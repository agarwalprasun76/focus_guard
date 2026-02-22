"""
Tab Server for browser extension communication.

This module provides a lightweight HTTP server for communicating with browser extensions.
It handles tab data updates, commands, and status checks.
"""

import json
import time
import socket
import logging
import threading
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, Type, Callable, List, Union

from focus_guard.core.config.interfaces import ConfigurationManager
from focus_guard.core.browser.models.tab import Tab
from focus_guard.core.browser.extension.interfaces import TabServerInterface, TabServerConfig

logger = logging.getLogger(__name__)

# Singleton instance
_tab_server_instance = None

class TabServer(TabServerInterface):
    """
    Manages an HTTP server for receiving browser tab data and sending commands to browser extensions.
    
    This server provides endpoints for:
    - Receiving tab data from browser extensions
    - Sending commands to browser extensions
    - Checking extension connection status
    - Getting tab data and active tab information
    
    The server uses a ThreadingHTTPServer to handle multiple concurrent requests.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config: Optional[TabServerConfig] = None):
        """Singleton pattern implementation with config-aware instances."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            elif config and hasattr(cls._instance, 'port') and config.port != cls._instance.port:
                # If requesting different port and server is not running, allow reconfiguration
                if not cls._instance.is_running():
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[TabServerConfig] = None):
        """
        Initialize the tab server.
        
        Args:
            config: Configuration for the tab server
        """
        if hasattr(self, '_initialized') and self._initialized:
            # Allow reconfiguration if server is not running and config differs
            if config and not self.is_running():
                if (config.port != self.port) or (config.host != self.host):
                    logger.info(f"Reconfiguring tab server: {self.host}:{self.port} -> {config.host}:{config.port}")
                    self.port = config.port
                    self.host = config.host
            return
            
        self.config = config or TabServerConfig()
        self.host = self.config.host
        self.port = self.config.port
        self._server: Optional[ThreadingHTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {
            "tabs": [],
            "browsers": {},  # Track multiple browsers
            "browser": {},   # Keep for backward compatibility
            "last_update": 0,  # Global last update (for backward compatibility)
            "browser_last_updates": {},  # Per-browser last update timestamps
            "server_start_time": time.time()
        }
        
        # Command queue for browser extension
        self._commands: List[Dict[str, Any]] = []
        self._commands_lock = threading.Lock()
        
        # Track browser statuses
        self._browser_statuses = {}  # Track browser connection status
        self._last_activity = {}  # Track last activity per browser
        self._health_metrics = {
            "requests_processed": 0,
            "errors_encountered": 0,
            "average_response_time": 0.0,
            "last_request_time": None
        }
        
        # Real-time event processing
        self._event_history = []  # Store recent events
        self._max_event_history = 1000  # Limit event history size
        self._blocking_cache = {}  # Cache blocking decisions
        self._classification_callback = None  # Callback for classification system
        
        # Error handling and resilience
        self._error_counts = {
            'http_errors': 0,
            'classification_errors': 0,
            'event_processing_errors': 0,
            'cache_errors': 0
        }
        self._last_error_reset = time.time()
        self._max_consecutive_errors = 5
        self._degraded_mode = False
        
        # Tab data
        self._tabs = []
        self._extension_connected = False
        self._start_time = time.time()
        
        # Shutdown handling
        self._shutdown_requested = threading.Event()
        
        self._initialized = True
        
        # Register cleanup on exit
        import atexit
        atexit.register(self.cleanup)
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self.cleanup_cache, daemon=True)
        cleanup_thread.start()
    
    def cleanup(self):
        """Clean up resources on exit."""
        self.stop()
    
    def cleanup_cache(self):
        """Clear old cache entries periodically."""
        while self._running:
            try:
                current_time = time.time()
                # Clean up old blocking cache entries
                expired_keys = [
                    key for key, value in self._blocking_cache.items()
                    if current_time - value['timestamp'] > 300  # 5 minutes
                ]
                for key in expired_keys:
                    del self._blocking_cache[key]
                
                # Clean up old event history
                cutoff_time = (current_time - 3600) * 1000  # 1 hour ago in milliseconds
                self._event_history = [
                    event for event in self._event_history
                    if event.get('timestamp', 0) > cutoff_time
                ]
                
                logger.debug(f"Cache cleanup: {len(expired_keys)} blocking entries, event history size: {len(self._event_history)}")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
            
            time.sleep(60)  # Clean every minute
    
    def is_running(self) -> bool:
        """
        Check if the tab server is running.
        
        Returns:
            bool: True if the tab server is running
        """
        return self._running.is_set()
        
    def is_port_available(self, port: Optional[int] = None) -> bool:
        """Check if a port is available.
        
        Args:
            port: Port to check (default: self.port)
            
        Returns:
            bool: True if the port is available, False otherwise
        """
        port = port or self.port
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                result = s.connect_ex((self.host, port))
                return result != 0
        except Exception as e:
            logger.debug(f"Error checking port availability: {e}")
            return False
    
    def start(self, port: Optional[int] = None) -> bool:
        """
        Start the tab server.
        
        Args:
            port: Optional port override
            
        Returns:
            bool: True if server started successfully, False otherwise
        """
        if port is not None:
            self.port = port
            
        if self._server_thread and self._server_thread.is_alive():
            logger.info("Tab server is already running")
            return True
            
        # Ensure we have a valid port
        if self.port is None:
            self.port = self.config.port or 5000
            
        # Find an available port if needed
        original_port = self.port
        if self.port == 0:
            self.port = self._find_available_port(5000, 5020)
            if self.port is None:
                logger.error("Could not find an available port in range 5000-5020")
                return False
            logger.info(f"Auto-selected available port: {self.port}")
        
        # Check if the specified port is available
        if not self.is_port_available():
            logger.warning(f"Port {self.port} is not available, searching for alternative")
            # Try to find an available port near the requested one
            alternative_port = self._find_available_port(self.port + 1, self.port + 20)
            if alternative_port is None:
                logger.error(f"Could not find an available port near {original_port}")
                return False
            self.port = alternative_port
            logger.info(f"Using alternative port: {self.port}")
        
        # Start the server
        max_retries = 3
        retry_count = 0
        
        try:
            while retry_count < max_retries:
                try:
                    self._server = ThreadingHTTPServer((self.host, self.port), self._make_handler())
                    self._server.timeout = 1
                    self._running.set()
                    self._server_thread = threading.Thread(
                        target=self._run_server,
                        daemon=True,
                        name="TabServerThread"
                    )
                    self._server_thread.start()
                    logger.info(f"Tab server started on {self.host}:{self.port}")
                    return True
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Failed to start TabServer (attempt {retry_count}/{max_retries}): {e}")
                    self._server = None
                    self._server_thread = None
                    
                    if retry_count < max_retries:
                        time.sleep(1)  # Wait before retrying
            return False
        except Exception as e:
            logger.error(f"Failed to start tab server: {e}")
            return False
    
    def _run_server(self):
        """Run the server in a loop until stopped."""
        try:
            logger.info("Tab server thread started")
            self._server.serve_forever()
        except OSError as e:
            if e.errno == 10048:  # Address already in use on Windows
                logger.error(f"Port {self.port} is already in use")
            else:
                logger.error(f"OS error in tab server: {e}")
        except Exception as e:
            if self._running.is_set():  # Only log if we're still supposed to be running
                logger.error(f"Error in tab server: {e}")
        finally:
            logger.info("Tab server thread stopped")
    
    def stop(self):
        """Stop the tab server gracefully."""
        if not self._running.is_set():
            logger.info("Tab server is not running")
            return True
            
        logger.info("Stopping tab server gracefully...")
        self._shutdown_requested.set()
        self._running.clear()
        
        # Clear any pending commands
        with self._commands_lock:
            self._commands.clear()
        
        # Shutdown the server properly
        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception as e:
                logger.error(f"Error shutting down server: {e}")
        
        # Wait for the server thread to finish
        if self._server_thread and self._server_thread.is_alive():
            try:
                self._server_thread.join(timeout=5)
                if self._server_thread.is_alive():
                    logger.warning("Server thread did not stop within timeout")
            except Exception as e:
                logger.error(f"Error joining server thread: {e}")
        
        # Reset server references
        self._server = None
        self._server_thread = None
        
        logger.info("Tab server stopped gracefully")
        return True
    
    def _forceful_shutdown(self):
        """
        Robustly shut down the ThreadingHTTPServer and its thread, avoiding deadlocks and port reuse issues.
        
        This method is required because Python's ThreadingHTTPServer/shutdown() can hang indefinitely on Windows
        when there are active connections, and the socket may remain in TIME_WAIT state preventing port reuse.
        
        Instead, we:
        1. Clear the running flag to signal the thread to stop
        2. Create a new socket connection to unblock server.handle_request()
        3. Close the server socket directly
        4. Join the thread with a timeout
        5. Set all references to None
        
        This pattern is robust and cross-platform, and is safe to use in test and production code.
        See: https://github.com/python/cpython/issues/85240, https://github.com/streamlit/streamlit/issues/7163
        """
        if not self._server:
            return
            
        # Signal the thread to stop
        self._running.clear()
        
        # Define a function to shutdown the server
        def shutdown_server():
            try:
                # Connect to the server to unblock handle_request()
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.host, self.port))
                    s.close()
            except:
                pass  # Ignore errors, we're shutting down anyway
        
        # Start a thread to shutdown the server
        threading.Thread(target=shutdown_server, daemon=True).start()
        
        # Close the server socket directly
        if hasattr(self._server, 'socket'):
            try:
                self._server.socket.close()
            except:
                pass
                
        # Wait for the thread to stop
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5)
            
        # Clean up references
        self._server = None
        self._server_thread = None
    
    def update_tabs(self, data: Dict[str, Any]):
        """
        Update the tab data in a thread-safe manner.
        
        Args:
            data: Dictionary containing tab data
        """
        if not isinstance(data, dict):
            logger.error(f"Invalid tab data format: {type(data)}")
            return
            
        with self._lock:
            try:
                # Extract browser name from data - ensure it's a string
                browser_data = data.get("browser", "unknown")
                if isinstance(browser_data, dict):
                    browser_name = browser_data.get("name", "unknown")
                else:
                    browser_name = str(browser_data) if browser_data else "unknown"
                
                # Update tabs
                if "tabs" in data and isinstance(data["tabs"], list):
                    self._tabs = data["tabs"]
                    self._extension_connected = True
                    
                    # Update browser-specific data
                    # Find active tab safely to avoid unhashable type errors
                    active_tab = None
                    try:
                        for tab in data["tabs"]:
                            if isinstance(tab, dict) and tab.get("active", False):
                                active_tab = tab
                                break
                    except Exception as e:
                        logger.debug(f"Error finding active tab: {e}")
                        active_tab = None
                    
                    self._browser_statuses[browser_name] = {
                        "last_update": time.time(),
                        "tab_count": len(data["tabs"]),
                        "active_tab": active_tab
                    }
                    
                    # Update legacy data structure for backward compatibility
                    self._data["tabs"] = data["tabs"]
                    self._data["browser"] = data.get("browser", {})
                    self._data["last_update"] = time.time()
                    self._data["browser_last_updates"][browser_name] = time.time()
                    
                    logger.debug(f"Updated {len(data['tabs'])} tabs from {browser_name}")
                else:
                    logger.warning(f"No tabs found in update from {browser_name}")
            except Exception as e:
                logger.error(f"Error updating tabs: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
    
    def add_command(self, command: Dict[str, Any]):
        """
        Add a command to the command queue for the browser extension.
        
        Args:
            command: Dictionary containing command data with format:
                    {"action": "close_tab", "data": {"tabId": 123, "windowId": 456, ...}}
        """
        if not isinstance(command, dict) or "action" not in command:
            logger.error(f"Invalid command format: {command}")
            return
            
        with self._commands_lock:
            # Add timestamp and ID if not present
            command["timestamp"] = time.time()
            if "id" not in command:
                command["id"] = f"cmd_{time.time()}_{len(self._commands)}"
                
            # Add the command to the queue
            self._commands.append(command)
            logger.debug(f"Added command: {command['action']}")
    
    def get_commands(self, browser_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all pending commands for the browser extension.
        
        Args:
            browser_name: Optional browser name to filter commands by
            
        Returns:
            List of command dictionaries
        """
        with self._commands_lock:
            if not browser_name:
                return self._commands.copy()
                
            # Filter commands by browser name
            return [cmd for cmd in self._commands if cmd.get("browser") == browser_name or "browser" not in cmd]
    
    def clear_commands(self):
        """
        Clear all pending commands after they've been processed.
        """
        with self._commands_lock:
            self._commands.clear()
    
    def get_tabs(self) -> List[Dict[str, Any]]:
        """
        Get a thread-safe copy of the tab data.
        
        Returns:
            List of tab dictionaries
        """
        with self._lock:
            return self._tabs.copy()
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently active tab.
        
        Returns:
            dict or None: The active tab data or None if no active tab
        """
        tabs = self.get_tabs()
        return next((tab for tab in tabs if tab.get("active", False)), None)
    
    def is_extension_connected(self, browser_name: Optional[str] = None) -> bool:
        """
        Check if the browser extension is connected.
        
        Args:
            browser_name: Optional browser name to check specific browser connection
            
        Returns:
            bool: True if the extension has sent data recently, False otherwise
        """
        current_time = time.time()
        connection_timeout = 30  # Consider extension disconnected after 30 seconds of no updates
        
        with self._lock:
            if browser_name:
                # Check specific browser connection
                status = self._browser_statuses.get(browser_name, {})
                last_update = status.get("last_update", 0)
                return (current_time - last_update) < connection_timeout
            else:
                # Check if any browser is connected
                return any(
                    (current_time - status.get("last_update", 0)) < connection_timeout
                    for status in self._browser_statuses.values()
                )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the tab server.
        
        Returns:
            Dict[str, Any]: Status information including extension connection status,
                           tab count, browser information, etc.
        """
        with self._lock:
            status_data = {
                "status": "ok",
                "server": "FocusGuard Tab Server",
                "version": "1.0.0",
                "uptime": time.time() - self._start_time,
                "extension_connected": self.is_extension_connected(),
                "tab_count": len(self.get_tabs()),
                "browsers": list(self._browser_statuses.keys()),
                "browser_statuses": self._browser_statuses
            }
            return status_data
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status of the tab server.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        current_time = time.time()
        
        # Update health metrics
        self._health_metrics["last_request_time"] = current_time
        
        # Check for issues
        issues = []
        
        # Check if extension is connected
        if not self.is_extension_connected():
            issues.append("No browser extension connected")
        
        # Check server responsiveness
        if self._server is None:
            issues.append("HTTP server not running")
        
        # Check if we have recent tab data
        if len(self._tabs) == 0:
            issues.append("No tab data received")
        
        # Update health status
        self._health_metrics["status"] = "healthy" if len(issues) == 0 else "degraded"
        self._health_metrics["issues"] = issues
        
        return self._health_metrics.copy()
    
    def _find_available_port(self, start_port: int, end_port: int) -> Optional[int]:
        """Find an available port in the given range.
        
        Args:
            start_port: Starting port number
            end_port: Ending port number
            
        Returns:
            Optional[int]: Available port number or None if no port is available
        """
        for port in range(start_port, end_port + 1):
            if self.is_port_available(port):
                return port
        return None
    
    def _trigger_shutdown(self):
        """Trigger graceful shutdown (called from HTTP endpoint)."""
        logger.info("Shutdown triggered via HTTP endpoint")
        self.stop()
    
    def set_classification_callback(self, callback):
        """Set callback function for classification decisions."""
        self._classification_callback = callback
        logger.info("Classification callback registered")
    
    def _get_blocking_decision(self, url, domain, browser, tab_id):
        """Get blocking decision from classification system."""
        try:
            # Check cache first
            cache_key = f"{domain}:{url}"
            if cache_key in self._blocking_cache:
                cached = self._blocking_cache[cache_key]
                age = time.time() - cached['timestamp']
                if age < 30:  # Cache for 30 seconds
                    return cached['should_block'], cached['reason']
            
            # Use classification callback if available
            if self._classification_callback:
                should_block, reason = self._classification_callback(url, domain, browser, tab_id)
            else:
                # Default behavior - block known distracting domains
                distracting_domains = {
                    'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com',
                    'reddit.com', 'tiktok.com', 'netflix.com', 'twitch.tv'
                }
                should_block = any(d in domain.lower() for d in distracting_domains)
                reason = 'default_domain_filter' if should_block else 'not_in_default_filter'
            
            # Cache the decision
            self._blocking_cache[cache_key] = {
                'should_block': should_block,
                'reason': reason,
                'timestamp': time.time()
            }
            
            # Limit cache size
            if len(self._blocking_cache) > 1000:
                oldest_key = min(self._blocking_cache.keys(), 
                               key=lambda k: self._blocking_cache[k]['timestamp'])
                del self._blocking_cache[oldest_key]
            
            return should_block, reason
            
        except Exception as e:
            logger.error(f"Error getting blocking decision: {e}")
            return False, f"error: {str(e)}"
    
    def process_tab_event(self, event_data):
        """Process incoming tab event from browser extension."""
        try:
            event_type = event_data.get('type', 'unknown')
            timestamp = event_data.get('timestamp', time.time() * 1000)
            browser = event_data.get('browser', 'unknown')
            
            # Add to event history
            event_record = {
                'type': event_type,
                'data': event_data.get('data', {}),
                'timestamp': timestamp,
                'browser': browser,
                'processed_at': time.time()
            }
            
            self._event_history.append(event_record)
            
            # Limit history size
            if len(self._event_history) > self._max_event_history:
                self._event_history = self._event_history[-self._max_event_history:]
            
            # Update browser activity
            self._last_activity[browser] = time.time()
            
            # Handle specific event types
            if event_type == 'tab_blocked':
                logger.info(f"Tab blocked: {event_data.get('data', {}).get('url', 'unknown')}")
            elif event_type == 'tab_created':
                tab_data = event_data.get('data', {})
                logger.debug(f"New tab created: {tab_data.get('url', 'unknown')}")
            elif event_type == 'tab_updated':
                tab_data = event_data.get('data', {})
                logger.debug(f"Tab updated: {tab_data.get('changeInfo', {}).get('url', 'no URL change')}")
            
        except Exception as e:
            logger.error(f"Error processing tab event: {e}")
    
    def get_recent_events(self, browser=None, since=None, limit=100):
        """Get recent events, optionally filtered by browser and time."""
        try:
            events = self._event_history
            
            # Filter by browser if specified
            if browser:
                events = [e for e in events if e.get('browser') == browser]
            
            # Filter by time if specified
            if since:
                try:
                    since_timestamp = float(since)
                    events = [e for e in events if e.get('timestamp', 0) > since_timestamp]
                except (ValueError, TypeError):
                    logger.warning(f"Invalid since parameter: {since}")
            
            # Limit results
            events = events[-limit:] if limit else events
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []
    
    def _should_block_url(self, url: str, domain: str, browser_name: str) -> bool:
        """
        Check if a URL should be blocked based on domain classifier.
        
        Args:
            url: The URL to check
            domain: The domain extracted from the URL
            browser_name: The name of the browser making the request
            
        Returns:
            bool: True if the URL should be blocked, False otherwise
        """
        # This is a placeholder for domain classification logic
        # In a real implementation, this would check against the domain classifier
        return False
    
    def _make_handler(self):
        """Create HTTP request handler."""
        server_instance = self
        
        class TabRequestHandler(BaseHTTPRequestHandler):
            """HTTP request handler for tab server endpoints."""
            
            def do_OPTIONS(self):
                """Handle CORS preflight requests."""
                self._set_headers(200)
                self.end_headers()
            
            def _set_headers(self, status_code=200, content_type="application/json"):
                """Set response headers with CORS support."""
                self.send_response(status_code)
                self.send_header('Content-Type', content_type)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
            
            def _send_json(self, code: int, data: Dict[str, Any]) -> None:
                """Send a JSON response."""
                self._set_headers(code)
                self.wfile.write(json.dumps(data).encode())
            
            def _handle_status(self):
                """Handle GET to status endpoint."""
                try:
                    status_data = {
                        "status": "ok",
                        "server": "FocusGuard Tab Server",
                        "version": "1.0.0",
                        "uptime": time.time() - server_instance._start_time,
                        "extension_connected": server_instance.is_extension_connected(),
                        "tab_count": len(server_instance.get_tabs()),
                        "browsers": list(server_instance._browser_statuses.keys()),
                        "port": server_instance.port,
                        "host": server_instance.host,
                        "health": server_instance.get_health_status()
                    }
                    self._send_json(200, status_data)
                except Exception as e:
                    logger.error(f"Error handling status request: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def _handle_get_tabs(self):
                """Handle GET to tabs endpoint."""
                try:
                    self._send_json(200, {"tabs": server_instance.get_tabs()})
                except Exception as e:
                    logger.error(f"Error handling get tabs request: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def _handle_health_check(self):
                """Handle GET to health endpoint."""
                try:
                    health_data = server_instance.get_health_status()
                    status_code = 200 if health_data["status"] == "healthy" else 503
                    self._send_json(status_code, health_data)
                except Exception as e:
                    logger.error(f"Error handling health check request: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def _handle_shutdown_request(self):
                """Handle POST to shutdown endpoint."""
                try:
                    self._send_json(200, {"status": "shutdown_initiated", "message": "Server shutdown initiated"})
                    # Trigger graceful shutdown in a separate thread
                    threading.Thread(target=server_instance._trigger_shutdown, daemon=True).start()
                except Exception as e:
                    logger.error(f"Error handling shutdown request: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def _handle_get_commands(self):
                """Handle GET to command endpoint."""
                try:
                    # Parse query parameters
                    parsed = urllib.parse.urlparse(self.path)
                    params = urllib.parse.parse_qs(parsed.query)
                    browser = params.get("browser", [None])[0]
                    
                    # Get commands for the specified browser
                    commands = server_instance.get_commands(browser)
                    self._send_json(200, {"commands": commands})
                except Exception as e:
                    logger.error(f"Error handling get commands request: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def _handle_should_block(self):
                """Handle GET to should_block endpoint."""
                try:
                    # Parse query parameters
                    parsed = urllib.parse.urlparse(self.path)
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    url = params.get("url", [""])[0]
                    domain = params.get("domain", [""])[0]
                    browser = params.get("browser", ["unknown"])[0]
                    
                    if not url or not domain:
                        self._send_json(400, {"error": "Missing required parameters", "should_block": False})
                        return
                        
                    # Check if the URL should be blocked
                    should_block = server_instance._should_block_url(url, domain, browser)
                    self._send_json(200, {"should_block": should_block, "url": url, "domain": domain})
                except Exception as e:
                    logger.error(f"Error handling should_block request: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def _handle_post_tabs(self):
                """Handle POST to tabs endpoint."""
                try:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length).decode('utf-8')
                    data = json.loads(post_data)
                    
                    # Update tab data
                    server_instance.update_tabs(data)
                    self._send_json(200, {"status": "ok"})
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    self._send_json(400, {"error": "Invalid JSON", "details": str(e)})
                except ValueError as e:
                    logger.error(f"Invalid data format: {e}")
                    self._send_json(400, {"error": "Invalid data format", "details": str(e)})
                except Exception as e:
                    logger.error(f"Error processing tab data: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def _handle_post_commands(self):
                """Handle POST to command endpoint."""
                try:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length).decode('utf-8')
                    data = json.loads(post_data)
                    
                    # If the browser acknowledges commands, clear them
                    if data.get("status") == "processed":
                        # Get browser name if provided
                        browser_name = data.get("browser")
                        if browser_name:
                            logger.info(f"Command acknowledgment from browser: {browser_name}")
                        
                        server_instance.clear_commands()
                        self._send_json(200, {"status": "ok"})
                    else:
                        self._send_json(400, {"error": "Invalid acknowledgment"})
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    self._send_json(400, {"error": "Invalid JSON", "details": str(e)})
                except ValueError as e:
                    logger.error(f"Invalid data format: {e}")
                    self._send_json(400, {"error": "Invalid data format", "details": str(e)})
                except Exception as e:
                    logger.error(f"Error processing command acknowledgment: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
                    # Increment error count for health monitoring
                    server_instance._health_metrics["errors_encountered"] += 1
            
            def do_GET(self):
                """Handle GET requests for status and tab data endpoints."""
                try:
                    if self.path == "/__shutdown__":
                        # Special endpoint for clean shutdown
                        self._set_headers(200)
                        self.wfile.write(b"Shutdown request received")
                        # Trigger graceful shutdown in a separate thread
                        threading.Thread(target=server_instance._trigger_shutdown, daemon=True).start()
                        return
                    elif self.path.startswith("/api/status"):
                        self._handle_status()
                    elif self.path.startswith("/api/tabs"):
                        self._handle_get_tabs()
                    elif self.path.startswith("/api/command"):
                        self._handle_get_commands()
                    elif self.path.startswith("/api/should_block"):
                        self._handle_should_block()
                    elif self.path.startswith("/api/health"):
                        self._handle_health_check()
                    elif self.path.startswith("/api/events"):
                        self._handle_events_request()
                    else:
                        self.send_error(404, "Not Found")
                except Exception as e:
                    logger.error(f"Error handling GET request: {e}")
                    self._send_json(500, {"error": "Internal Server Error"})
            
            def _handle_events_request(self):
                """Handle GET to events endpoint for event streaming."""
                try:
                    # Parse query parameters
                    parsed = urllib.parse.urlparse(self.path)
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    browser = params.get("browser", [None])[0]
                    since = params.get("since", [None])[0]
                    limit = int(params.get("limit", [100])[0])
                    
                    # Get recent events
                    events = server_instance.get_recent_events(browser, since, limit)
                    
                    self._send_json(200, {
                        "events": events,
                        "timestamp": time.time(),
                        "browser": browser
                    })
                except Exception as e:
                    logger.error(f"Error handling events request: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def _handle_post_events(self):
                """Handle POST to events endpoint for receiving real-time events."""
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    if content_length > 0:
                        post_data = self.rfile.read(content_length)
                        event_data = json.loads(post_data.decode('utf-8'))
                        
                        # Check if this is a batch of events or single event
                        is_batch = self.headers.get('X-Event-Batch') == 'true'
                        
                        if is_batch and 'events' in event_data:
                            # Handle batch of events
                            for event in event_data['events']:
                                server_instance.process_tab_event(event)
                            logger.debug(f"Processed batch of {len(event_data['events'])} events")
                            self._send_json(200, {
                                "status": "batch_processed",
                                "count": len(event_data['events'])
                            })
                        else:
                            # Handle single event
                            server_instance.process_tab_event(event_data)
                            event_type = event_data.get('type', 'unknown')
                            logger.debug(f"Processed {event_type} event")
                            self._send_json(200, {
                                "status": "event_processed",
                                "type": event_type
                            })
                    else:
                        self._send_json(400, {"error": "No event data provided"})
                        
                except Exception as e:
                    logger.error(f"Error handling post events request: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def _handle_should_block_request(self):
                """Handle GET to should_block endpoint with enhanced classification."""
                try:
                    # Parse query parameters
                    parsed = urllib.parse.urlparse(self.path)
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    url = params.get("url", [None])[0]
                    domain = params.get("domain", [None])[0]
                    browser = params.get("browser", [None])[0]
                    tab_id = params.get("tabId", [None])[0]
                    
                    if not url or not domain:
                        self._send_json(400, {"error": "Missing url or domain parameter"})
                        return
                    
                    # Get blocking decision from classification system
                    should_block, reason = server_instance._get_blocking_decision(url, domain, browser, tab_id)
                    
                    # Log the decision for debugging
                    logger.debug(f"Blocking decision for {domain}: {should_block} ({reason})")
                    
                    self._send_json(200, {
                        "should_block": should_block,
                        "reason": reason,
                        "url": url,
                        "domain": domain,
                        "browser": browser,
                        "tab_id": tab_id,
                        "timestamp": time.time()
                    })
                except Exception as e:
                    logger.error(f"Error handling should_block request: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def do_POST(self):
                """Handle POST requests for updating tab data."""
                try:
                    # Parse the path to handle query parameters
                    parsed_path = urllib.parse.urlparse(self.path)
                    base_path = parsed_path.path
                    
                    if base_path == "/api/tabs":
                        self._handle_post_tabs()
                    elif base_path == "/api/command":
                        self._handle_post_commands()
                    elif base_path == "/api/shutdown":
                        self._handle_shutdown_request()
                    elif base_path == "/api/events":
                        self._handle_post_events()
                    else:
                        self._send_json(404, {"error": "Not found", "path": self.path})
                except Exception as e:
                    logger.error(f"Error handling POST request: {e}")
                    self._send_json(500, {"error": "Internal Server Error"})
            
            def log_message(self, format, *args):
                """Override log_message to use our logger."""
                logger.debug(f"{self.address_string()} - {format % args}")
        
        return TabRequestHandler


def get_tab_server(config: Optional[TabServerConfig] = None) -> TabServer:
    """Get the singleton tab server instance.
    
    Args:
        config: Optional configuration for the tab server
    
    Returns:
        TabServer: The singleton tab server instance
    """
    global _tab_server_instance
    if _tab_server_instance is None:
        _tab_server_instance = TabServer(config)
    return _tab_server_instance


def is_running() -> bool:
    """Check if the tab server is running.
    
    Returns:
        bool: True if the tab server is running, False otherwise
    """
    server = get_tab_server()
    return server.is_running()


def start_tab_server(port: int = 5000) -> bool:
    """Start the tab server on the specified port.
    
    Args:
        port: Port to run the tab server on
        
    Returns:
        bool: True if the tab server was started successfully
    """
    server = get_tab_server()
    return server.start(port)


def stop_tab_server() -> bool:
    """Stop the tab server.
    
    Returns:
        bool: True if the tab server was stopped successfully
    """
    server = get_tab_server()
    return server.stop()


def main():
    """Main function for standalone testing."""
    logging.basicConfig(level=logging.DEBUG)
    server = get_tab_server()
    if server.start(5000):
        print("Tab server running on http://localhost:5000")
        print("Press Ctrl+C to stop...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
    else:
        print("Failed to start tab server")


if __name__ == "__main__":
    main()