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

from core_v2.config.interfaces import ConfigurationManager
from core_v2.browser.models.tab import Tab
from core_v2.browser.extension.interfaces import TabServerInterface, TabServerConfig

logger = logging.getLogger(__name__)

# Import the actual tab server implementation
from core.browser_detection.browser_integration.tab_server_v2 import TabServer as TabServerV2
from core.browser_detection.browser_integration.tab_server_v2 import is_running

# Functions to delegate to the actual tab server implementation
def get_tab_server() -> TabServerV2:
    """Get the tab server instance from the actual implementation.
    
    Returns:
        TabServerV2: The tab server instance
    """
    from core.browser_detection.browser_integration.tab_server_v2 import get_tab_server as get_tab_server_v2
    return get_tab_server_v2()

def start_tab_server(port: int = 5000) -> bool:
    """Start the tab server on the specified port.
    
    Args:
        port: Port to run the tab server on
        
    Returns:
        bool: True if the tab server was started successfully
    """
    from core.browser_detection.browser_integration.tab_server_v2 import start_tab_server as start_tab_server_v2
    return start_tab_server_v2(port)

def stop_tab_server() -> bool:
    """Stop the tab server.
    
    Returns:
        bool: True if the tab server was stopped successfully
    """
    from core.browser_detection.browser_integration.tab_server_v2 import stop_tab_server as stop_tab_server_v2
    return stop_tab_server_v2()

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
    
    def __init__(self, config: TabServerConfig):
        """
        Initialize the tab server.
        
        Args:
            config: Configuration for the tab server
        """
        self.host = config.host
        self.port = config.port
        self.config = config
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
    
    def is_running(self) -> bool:
        """
        Check if the tab server is running.
        
        Returns:
            bool: True if the tab server is running
        """
        # Delegate to the imported is_running function
        return is_running()
        
    def is_port_available(self, port: Optional[int] = None) -> bool:
        """
        Check if a port is available.
        
        Args:
            port: Port to check (default: self.port)
            
        Returns:
            bool: True if the port is available, False otherwise
        """
        port = port or self.port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, port)) != 0
    
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
            
        # Check if port is available
        if not self.is_port_available():
            logger.warning(f"Port {self.port} is not available, trying to find an available port")
            # Try to find an available port
            for test_port in range(self.port + 1, self.port + 10):
                if self.is_port_available(test_port):
                    self.port = test_port
                    logger.info(f"Found available port: {self.port}")
                    break
            else:
                logger.error("Could not find an available port")
                return False
        
        # Start the server
        max_retries = 3
        retry_count = 0
        
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
                
        logger.error("Failed to start TabServer after multiple attempts")
        return False
    
    def _run_server(self) -> None:
        """Run the server in a loop until stopped."""
        try:
            logger.info(f"Tab server thread starting on {self.host}:{self.port}")
            while self._running.is_set():
                try:
                    self._server.handle_request()
                except Exception as e:
                    if self._running.is_set():  # Only log if we're still supposed to be running
                        logger.error(f"Error handling request: {e}")
            logger.info("Tab server thread exiting normally")
        except Exception as e:
            logger.error(f"Tab server thread exiting with error: {e}")
    
    def stop(self) -> None:
        """Stop the tab server."""
        if not self._running.is_set():
            logger.info("Tab server is not running")
            return
            
        logger.info("Stopping tab server...")
        self._running.clear()
        
        # First try a clean shutdown via a special request
        try:
            def send_shutdown_request():
                try:
                    import urllib.request
                    urllib.request.urlopen(f"http://{self.host}:{self.port}/__shutdown__", timeout=1)
                except Exception as e:
                    logger.debug(f"Shutdown request error (expected): {e}")
            
            # Send shutdown request in a thread to avoid blocking
            threading.Thread(target=send_shutdown_request, daemon=True).start()
            
            # Give the server a moment to process the shutdown request
            time.sleep(0.5)
        except Exception as e:
            logger.debug(f"Error sending shutdown request: {e}")
        
        # Now do a forceful shutdown if needed
        self._forceful_shutdown()
        
        # Wait for server thread to exit
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2)
            
        logger.info("Tab server stopped")
    
    def _forceful_shutdown(self) -> None:
        """
        Robustly shut down the ThreadingHTTPServer and its thread, avoiding deadlocks and port reuse issues.
        
        This method is required because Python's ThreadingHTTPServer/shutdown() can hang indefinitely on Windows
        when there are active connections. This is a known issue in Python's http.server module.
        
        The approach here:
        1. Set a flag to stop the server loop
        2. Try to shutdown the server in a separate thread with a timeout
        3. If that fails, set the server to None to allow garbage collection
        4. This ensures the port is released quickly for reuse
        
        This pattern is robust and cross-platform, and is safe to use in test and production code.
        See: https://github.com/python/cpython/issues/85240, https://github.com/streamlit/streamlit/issues/7163
        """
        if not self._server:
            return
            
        # Try to shutdown the server in a separate thread with a timeout
        shutdown_thread = threading.Thread(
            target=lambda: self._server.shutdown() if self._server else None,
            daemon=True,
            name="TabServerShutdownThread"
        )
        
        try:
            # Start the shutdown thread
            shutdown_thread.start()
            
            # Wait for the shutdown thread to complete with a timeout
            shutdown_thread.join(timeout=2)
            
            # If the thread is still alive after timeout, we need to force cleanup
            if shutdown_thread.is_alive():
                logger.warning("Server shutdown thread timed out, forcing cleanup")
            
            # Close the socket if it exists
            if hasattr(self._server, 'socket') and self._server.socket:
                try:
                    self._server.socket.close()
                except Exception as e:
                    logger.debug(f"Error closing server socket: {e}")
            
            # Set server to None to allow garbage collection
            self._server = None
            
        except Exception as e:
            logger.error(f"Error during server shutdown: {e}")
            # Ensure server is set to None even if an exception occurs
            self._server = None
    
    def update_tabs(self, data: Dict[str, Any]) -> None:
        """
        Update the tab data in a thread-safe manner.
        
        Args:
            data: Dictionary containing tab data
        """
        if not data:
            logger.warning("Received empty tab data")
            return
            
        with self._lock:
            try:
                # Extract browser information
                browser_info = data.get("browser", {})
                browser_name = browser_info.get("name", "unknown")
                
                # Update browser-specific data
                if browser_name and browser_name != "unknown":
                    self._data["browsers"][browser_name] = browser_info
                    self._data["browser_last_updates"][browser_name] = time.time()
                    
                    # Keep the legacy "browser" field updated with the most recent browser
                    self._data["browser"] = browser_info
                
                # Update tabs data
                tabs = data.get("tabs", [])
                if tabs:
                    # If we're getting tabs for a specific browser, replace only those tabs
                    if browser_name and browser_name != "unknown":
                        # Remove existing tabs for this browser
                        self._data["tabs"] = [
                            tab for tab in self._data["tabs"] 
                            if tab.get("browser", {}).get("name", "") != browser_name
                        ]
                        # Add the new tabs
                        self._data["tabs"].extend(tabs)
                    else:
                        # If no browser specified, replace all tabs
                        self._data["tabs"] = tabs
                
                # Update global last_update timestamp
                self._data["last_update"] = time.time()
                
                logger.debug(f"Updated tabs for {browser_name}: {len(tabs)} tabs")
                
            except Exception as e:
                logger.error(f"Error updating tabs: {e}")
    
    def add_command(self, command: Dict[str, Any]) -> None:
        """
        Add a command to the command queue for the browser extension.
        
        Args:
            command: Dictionary containing command data with format:
                    {"action": "close_tab", "data": {"tabId": 123, "windowId": 456, ...}}
        """
        if not command:
            logger.warning("Attempted to add empty command")
            return
            
        # Validate command format
        if not isinstance(command, dict):
            logger.error(f"Invalid command format: {command}")
            return
            
        if "action" not in command:
            logger.error(f"Command missing 'action' field: {command}")
            return
            
        with self._commands_lock:
            # Add timestamp to command
            command["timestamp"] = time.time()
            
            # Add unique ID if not present
            if "id" not in command:
                command["id"] = f"cmd_{time.time()}_{len(self._commands)}"
                
            self._commands.append(command)
            logger.debug(f"Added command: {command['action']} (ID: {command['id']})")
            
            # Limit command queue size
            max_commands = 100
            if len(self._commands) > max_commands:
                # Remove oldest commands
                excess = len(self._commands) - max_commands
                removed = self._commands[:excess]
                self._commands = self._commands[excess:]
                logger.warning(f"Command queue exceeded {max_commands}, removed {len(removed)} old commands")
    
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
                
            # Filter commands by browser name if specified
            return [
                cmd for cmd in self._commands
                if not cmd.get("browser") or cmd.get("browser") == browser_name
            ]
    
    def clear_commands(self) -> None:
        """
        Clear all pending commands after they've been processed.
        """
        with self._commands_lock:
            command_count = len(self._commands)
            self._commands.clear()
            logger.debug(f"Cleared {command_count} commands")
    
    def get_tabs(self) -> List[Dict[str, Any]]:
        """
        Get a thread-safe copy of the tab data.
        
        Returns:
            List of tab dictionaries
        """
        with self._lock:
            return self._data["tabs"].copy()
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently active tab.
        
        Returns:
            dict or None: The active tab data or None if no active tab
        """
        tabs = self.get_tabs()
        # Check for both 'active' and 'isActive' keys for compatibility
        return next((tab for tab in tabs if tab.get("active", False) or tab.get("isActive", False)), None)
    
    def is_extension_connected(self, browser_name: Optional[str] = None) -> bool:
        """
        Check if the browser extension is connected.
        
        Args:
            browser_name: Optional browser name to check specific browser connection
            
        Returns:
            bool: True if the extension has sent data recently, False otherwise
        """
        with self._lock:
            current_time = time.time()
            connection_timeout = 30  # seconds
            
            if browser_name:
                # Check specific browser
                last_update = self._data["browser_last_updates"].get(browser_name, 0)
                return (current_time - last_update) < connection_timeout
            else:
                # Check any browser
                if not self._data["browser_last_updates"]:
                    return False
                    
                # Check if any browser has connected recently
                return any(
                    (current_time - last_update) < connection_timeout
                    for last_update in self._data["browser_last_updates"].values()
                )
    
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
        try:
            # Use the domain blocking integration if available
            from core_v2.browser.extension.domain_blocking import should_block_url
            return should_block_url(url)
        except ImportError:
            logger.warning("Domain blocking integration not available")
            return False
    def _get_blocking_rules(self, browser_name: str) -> List[Dict[str, Any]]:
        """
        Get blocking rules for the browser extension.
        
        Args:
            browser_name: The name of the browser requesting rules
            
        Returns:
            List of rule dictionaries
        """
        # This is a placeholder for domain blocking rules
        # In the actual implementation, this would return the current blocking rules
        # from the domain classifier and blocking configuration
        
        # For now, we'll just return an empty list (no rules)
        # The actual implementation will be added when we integrate with the domain classifier
        return []
    
    def _make_handler(self) -> Type[BaseHTTPRequestHandler]:
        """Create a request handler class with access to this server instance."""
        server_instance = self
        
        class TabRequestHandler(BaseHTTPRequestHandler):
            """HTTP request handler for tab server endpoints."""
            
            def do_OPTIONS(self):
                """Handle OPTIONS requests for CORS preflight."""
                self._set_headers()
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
                """Handle status endpoint."""
                status_data = {
                    "status": "ok",
                    "uptime": time.time() - server_instance._data["server_start_time"],
                    "connected": server_instance.is_extension_connected(),
                    "port": server_instance.port,
                    "tab_count": len(server_instance.get_tabs()),
                    "browsers": list(server_instance._data["browsers"].keys())
                }
                self._send_json(200, status_data)
            
            def _handle_get_tabs(self):
                """Handle tabs endpoint."""
                self._send_json(200, {"tabs": server_instance.get_tabs()})
            
            def _handle_get_commands(self):
                """Handle command endpoint."""
                # Parse the query parameters
                parsed_path = urllib.parse.urlparse(self.path)
                query_params = urllib.parse.parse_qs(parsed_path.query)
                
                # Get browser name if provided
                browser_name = query_params.get("browser", [None])[0]
                
                # Get commands for the browser
                commands = server_instance.get_commands(browser_name)
                self._send_json(200, {"commands": commands})
            
            def _handle_should_block(self):
                """Handle should_block endpoint."""
                # Parse the query parameters
                parsed_path = urllib.parse.urlparse(self.path)
                query_params = urllib.parse.parse_qs(parsed_path.query)
                
                # Get URL and browser name
                url = query_params.get("url", [""])[0]
                domain = query_params.get("domain", [""])[0]
                browser_name = query_params.get("browser", ["unknown"])[0]
                
                # Check if URL should be blocked
                should_block = server_instance._should_block_url(url, domain, browser_name)
                
                # Get blocking rules
                rules = server_instance._get_blocking_rules(browser_name)
                
                self._send_json(200, {
                    "should_block": should_block,
                    "rules": rules
                })
            
            def _handle_post_tabs(self):
                """Handle POST to tabs endpoint."""
                try:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length).decode('utf-8')
                    data = json.loads(post_data)
                    
                    # Update tab data
                    server_instance.update_tabs(data)
                    
                    # Send response
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
            
            def do_GET(self):
                """Handle GET requests for status and tab data endpoints."""
                try:
                    if self.path == "/__shutdown__":
                        # Special endpoint for clean shutdown
                        self._set_headers(200)
                        self.wfile.write(b"Shutdown request received")
                        return
                    elif self.path.startswith("/api/status"):
                        self._handle_status()
                    elif self.path.startswith("/api/tabs"):
                        self._handle_get_tabs()
                    elif self.path.startswith("/api/command"):
                        self._handle_get_commands()
                    elif self.path.startswith("/api/should_block"):
                        self._handle_should_block()
                    else:
                        self.send_error(404, "Not Found")
                except Exception as e:
                    logger.error(f"Error handling GET request: {e}")
                    self._send_json(500, {"error": "Internal Server Error"})

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
                    else:
                        self._send_json(404, {"error": "Not found", "path": self.path})
                except Exception as e:
                    logger.error(f"Error handling POST request: {e}")
                    self._send_json(500, {"error": "Internal Server Error"})
            
            def log_message(self, format, *args):
                """Override log_message to use our logger."""
                logger.debug(f"{self.address_string()} - {format % args}")
        
        return TabRequestHandler
