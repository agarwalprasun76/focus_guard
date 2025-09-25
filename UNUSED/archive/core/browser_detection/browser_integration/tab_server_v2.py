# core/browser_integration/tab_server_v2.py
import json
import time
import socket
import logging
import threading
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, Type, Callable, List

from core.browser_detection.browser_integration.config import Config

logger = logging.getLogger(__name__)

class TabServer:
    """Manages an HTTP server for receiving browser tab data."""
    
    def __init__(self, host: str = None, port: int = None):
        """Initialize the tab server.
        
        Args:
            host: Hostname to bind to (default: Config.SERVER_HOST)
            port: Port to listen on (default: Config.SERVER_PORT)
        """
        self.host = host or Config.SERVER_HOST
        self.port = port or Config.SERVER_PORT
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
        
        # We'll register cleanup in the main application
    
    def is_port_available(self, port: int = None) -> bool:
        """Check if a port is available.
        
        Args:
            port: Port to check (default: self.port)
            
        Returns:
            bool: True if the port is available, False otherwise
        """
        port = port or self.port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, port)) != 0
    
    def start(self, port: int = None):
        """Start the tab server.
        
        Args:
            port: Optional port override
            
        Returns:
            bool: True if server started successfully, False otherwise
        """
        if port is not None:
            self.port = port
            
        if self._server_thread and self._server_thread.is_alive():
            print("Tab server is already running")
            return True
            
        # Check if port is available
        if not self.is_port_available():
            print(f"Port {self.port} is not available, trying to find an available port")
            # Try to find an available port
            for test_port in range(self.port + 1, self.port + 10):
                if self.is_port_available(test_port):
                    self.port = test_port
                    print(f"Found available port: {self.port}")
                    break
            else:
                print("Could not find an available port")
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
                print(f"Tab server started on {self.host}:{self.port}")
                return True
            except Exception as e:
                retry_count += 1
                print(f"Failed to start TabServer (attempt {retry_count}/{max_retries}): {e}")
                self._server = None
                self._server_thread = None
                
                if retry_count < max_retries:
                    print(f"Retrying in 1 second...")
                    time.sleep(1)
                else:
                    print("Max retries reached, giving up")
                    return False    
    
    def _run_server(self) -> None:
        """Run the server in a loop until stopped."""
        consecutive_errors = 0
        max_consecutive_errors = 5
        retry_delay = 1.0  # seconds
        
        try:
            while self._running.is_set() and self._server:
                try:
                    self._server.handle_request()
                    consecutive_errors = 0  # Reset error counter on successful request
                except Exception as e:
                    consecutive_errors += 1
                    print(f"Error handling request in server thread: {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"Too many consecutive errors ({consecutive_errors}), pausing server for {retry_delay} seconds")
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30 seconds
                        consecutive_errors = 0  # Reset after backoff
        except Exception as e:
            print(f"Critical error in server thread: {e}")
        finally:
            self._running.clear()
            print("Tab server thread stopped")
    
    def stop(self) -> None:
        # WARNING: DO NOT DELETE OR REPLACE THESE PRINT STATEMENTS WITH LOGGER CALLS!
        # Using print() here to avoid deadlocks with Python's logging module when shutting down from multiple threads.
        # See issue: logger deadlocks during shutdown if server thread is blocked or logging at the same time.
        print("DEBUG_MARKER_ENTER_STOP")
        print("DEBUG: type(self._running) =", type(self._running))
        print("DEBUG: self._running repr =", repr(self._running))
        if not self._running.is_set():
            return
        print("Stopping tab server... (print)")
        print("About to check self._server... (print)")
        if self._server:
            print("self._server is truthy, entering shutdown block. (print)")
            # Shutdown the server
            try:
                print("Entered try block in stop(). (print)")
                # Send a dummy HTTP request to unblock handle_request() BEFORE shutdown, in a separate thread
                def send_shutdown_request():
                    try:
                        import http.client
                        print("[thread] Sending dummy HTTP request to unblock server thread... (print)")
                        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
                        conn.request("GET", "/__shutdown__")
                        conn.getresponse()
                        conn.close()
                        print("[thread] Dummy HTTP request sent. (print)")
                    except Exception as e:
                        print(f"[thread] Failed to send dummy HTTP request: {e} (print)")
                import threading as _threading
                print("Spawning thread to send dummy shutdown request...")
                t = _threading.Thread(target=send_shutdown_request)
                t.start()
                t.join(timeout=3)
                print("Dummy shutdown request thread finished (or timed out). (print)")

                # Use helper to perform a robust, cross-platform shutdown of the threaded HTTP server.
                self._forceful_shutdown()
            except Exception as e:
                print(f"Error stopping server: {e} (print)")

    def _forceful_shutdown(self):
        """
        Robustly shut down the ThreadingHTTPServer and its thread, avoiding deadlocks and port reuse issues.

        This method is required because Python's ThreadingHTTPServer/shutdown() can hang indefinitely on Windows
        if the server thread is blocked in handle_request() and no requests are pending. This can cause:
          - Deadlocks during shutdown
          - Port not being released for reuse in tests

        To avoid this, we:
        1. Forcibly close the server socket to break handle_request() out of its blocking state.
        2. Check if the server thread is still alive. If not, skip shutdown().
        3. If the thread is alive, call shutdown() in a separate thread with a timeout.
        4. Always call server_close() to fully release the socket.

        This pattern is robust and cross-platform, and is safe to use in test and production code.
        See: https://github.com/python/cpython/issues/85240, https://github.com/streamlit/streamlit/issues/7163
        """
        import threading as _threading
        try:
            print(f"[FORCE CLOSE] Server thread alive before shutdown? {self._server_thread.is_alive() if self._server_thread else None}")
            if self._server and self._server.socket:
                print("[FORCE CLOSE] Closing server socket to unblock handle_request()...")
                self._server.socket.close()
                print("[FORCE CLOSE] Server socket closed.")
        except Exception as e:
            print(f"[FORCE CLOSE] Exception while closing server socket: {e}")

        alive_after_close = self._server_thread.is_alive() if self._server_thread else None
        print(f"[FORCE CLOSE] Server thread alive after socket close? {alive_after_close}")
        if not alive_after_close:
            print("Server thread dead after socket close; skipping shutdown(). (print)")
        else:
            print("Calling self._server.shutdown() in a separate thread with timeout... (print)")
            def shutdown_server():
                try:
                    self._server.shutdown()
                    print("self._server.shutdown() returned. (print)")
                except Exception as e:
                    print(f"Exception during self._server.shutdown(): {e} (print)")
            shutdown_thread = _threading.Thread(target=shutdown_server, name="shutdown_server", daemon=True)
            shutdown_thread.start()
            shutdown_thread.join(timeout=3)
            if shutdown_thread.is_alive():
                print("self._server.shutdown() did NOT return in 3 seconds; skipping. (print)")
            else:
                print("self._server.shutdown() completed in thread. (print)")

        print(f"[FORCE CLOSE] Server thread alive after shutdown logic? {self._server_thread.is_alive() if self._server_thread else None}")
        print("Calling self._server.server_close()... (print)")
        self._server.server_close()
        print("self._server.server_close() returned. (print)")

        self._running.clear()
        print("Cleared self._running event. (print)")

        print("Tab server stopped (print)")
        
        # Wait for the server thread to finish
        if self._server_thread and self._server_thread.is_alive():
            print("Joining server thread... (print)")
            self._server_thread.join(timeout=5.0)
            if self._server_thread.is_alive():
                print("Server thread did not shut down cleanly (print)")
            else:
                print("Server thread joined successfully. (print)")
    
    def update_tabs(self, data: Dict[str, Any]):
        """Update the tab data in a thread-safe manner.
        
        Args:
            data: Dictionary containing tab data
        """
        try:
            with self._lock:
                browser_info = data.get("browser", {})
                browser_name = browser_info.get("name", "Unknown")
                current_time = time.time()
                
                # Store the browser-specific data
                self._data["browsers"][browser_name] = browser_info
                
                # Keep the last browser for backward compatibility
                self._data["browser"] = browser_info
                
                # Update tabs
                if "tabs" in data:
                    tab_count = len(data["tabs"])
                    logger.debug(f"Updated tabs for browser: {browser_name} with {tab_count} tabs")
                    
                    # Validate tab data
                    valid_tabs = []
                    for tab in data["tabs"]:
                        # Ensure each tab has required fields
                        if not isinstance(tab, dict):
                            logger.warning(f"Skipping invalid tab data (not a dict): {tab}")
                            continue
                            
                        # Ensure tab has required fields
                        if "id" not in tab:
                            tab["id"] = f"unknown_{len(valid_tabs)}"
                            logger.warning("Tab missing ID, assigned temporary ID")
                            
                        if "url" not in tab:
                            tab["url"] = ""
                            logger.warning("Tab missing URL, assigned empty string")
                            
                        valid_tabs.append(tab)
                    
                    # Replace tabs for this browser
                    self._data["tabs"] = valid_tabs
                    
                    # Log total tabs across all browsers
                    logger.debug(f"Total tabs across all browsers: {len(self._data['tabs'])}")
                    
                    # Log active browsers
                    logger.debug(f"Active browsers: {list(self._data['browsers'].keys())}")
                    
                # Update timestamps
                self._data["last_update"] = current_time  # Global last update (for backward compatibility)
                
                # Initialize browser_last_updates if it doesn't exist
                if "browser_last_updates" not in self._data:
                    self._data["browser_last_updates"] = {}
                    
                # Update per-browser timestamp
                self._data["browser_last_updates"][browser_name] = current_time
        except Exception as e:
            logger.error(f"Error updating tabs: {e}")
            # Don't re-raise the exception to prevent crashing the server
            # Just log it and continue
    
    def add_command(self, command: Dict[str, Any]) -> None:
        """
        Add a command to the command queue for the browser extension.
        
        Args:
            command: Dictionary containing command data with format:
                    {"action": "close_tab", "data": {"tabId": 123, "windowId": 456, ...}}
        """
        with self._commands_lock:
            cmd_id = f"cmd_{int(time.time()*1000)}"
            
            # For close_tab commands, create a command for each browser if browser_name is not specified
            if command.get('action') == 'close_tab' and not command.get('browser_name'):
                # Get the tab URL to identify which browsers need the command
                tab_url = command.get('data', {}).get('url', '')
                tab_domain = command.get('data', {}).get('domain', '')
                
                # If we have a URL or domain, send command to all browsers that have matching tabs
                if tab_url or tab_domain:
                    with self._lock:  # Lock to safely access self._data
                        browsers_with_matching_tabs = []
                        
                        # Check each browser for matching tabs
                        for browser_name, browser_data in self._data['browsers'].items():
                            browser_tabs = browser_data.get('tabs', [])
                            
                            # Look for matching tabs in this browser
                            for tab in browser_tabs:
                                tab_matches = False
                                if tab_url and tab.get('url') == tab_url:
                                    tab_matches = True
                                elif tab_domain and tab_domain in tab.get('url', ''):
                                    tab_matches = True
                                
                                if tab_matches:
                                    browsers_with_matching_tabs.append(browser_name)
                                    break
                        
                        # If no specific browsers found, send to all browsers
                        if not browsers_with_matching_tabs:
                            browsers_with_matching_tabs = list(self._data['browsers'].keys())
                        
                        # Create a command for each browser
                        for browser_name in browsers_with_matching_tabs:
                            browser_cmd = {
                                **command,
                                "browser_name": browser_name,
                                "timestamp": time.time(),
                                "id": f"{cmd_id}_{browser_name}"
                            }
                            self._commands.append(browser_cmd)
                            
                            tab_id = command.get('data', {}).get('tabId')
                            tab_id_type = type(tab_id).__name__
                            logger.info(f"Added close_tab command for browser {browser_name}: ID={cmd_id}_{browser_name}, tabId={tab_id} (type={tab_id_type})")
                            logger.debug(f"Full command details: {json.dumps(browser_cmd)}")
                else:
                    # No URL/domain info, just add the command as is
                    cmd_with_meta = {
                        **command,
                        "timestamp": time.time(),
                        "id": cmd_id
                    }
                    self._commands.append(cmd_with_meta)
                    
                    tab_id = command.get('data', {}).get('tabId')
                    tab_id_type = type(tab_id).__name__
                    logger.info(f"Added generic close_tab command to queue: ID={cmd_id}, tabId={tab_id} (type={tab_id_type})")
                    logger.debug(f"Full command details: {json.dumps(cmd_with_meta)}")
            else:
                # For non-close_tab commands or commands with browser_name already specified
                cmd_with_meta = {
                    **command,
                    "timestamp": time.time(),
                    "id": cmd_id
                }
                self._commands.append(cmd_with_meta)
                
                if command.get('action') == 'close_tab':
                    tab_id = command.get('data', {}).get('tabId')
                    tab_id_type = type(tab_id).__name__
                    browser_name = command.get('browser_name', 'all')
                    logger.info(f"Added close_tab command for browser {browser_name}: ID={cmd_id}, tabId={tab_id} (type={tab_id_type})")
                    logger.debug(f"Full command details: {json.dumps(cmd_with_meta)}")
                else:
                    logger.info(f"Added command to queue: {command['action']}")
            
            # Log queue status
            logger.debug(f"Command queue now has {len(self._commands)} pending commands")
    
    def get_commands(self, browser_name: str = None) -> List[Dict[str, Any]]:
        """
        Get all pending commands for the browser extension.
        
        Args:
            browser_name: Optional browser name to filter commands by
            
        Returns:
            List of command dictionaries
        """
        with self._commands_lock:
            # If browser_name is provided, filter commands for that browser
            if browser_name:
                # Get commands with no browser_name (global) or matching browser_name
                commands = [cmd for cmd in self._commands if 
                           not cmd.get('browser_name') or cmd.get('browser_name') == browser_name]
                
                if commands:
                    logger.info(f"Returning {len(commands)} pending commands to browser: {browser_name}")
                    for cmd in commands:
                        if cmd.get('action') == 'close_tab':
                            tab_id = cmd.get('data', {}).get('tabId')
                            cmd_id = cmd.get('id', 'unknown')
                            logger.info(f"Sending close_tab command to {browser_name}: ID={cmd_id}, tabId={tab_id}")
                else:
                    logger.debug(f"No pending commands for browser: {browser_name}")
            else:
                # Return all commands if no browser_name specified
                commands = self._commands.copy()
                if commands:
                    logger.info(f"Returning all {len(commands)} pending commands")
                    for cmd in commands:
                        if cmd.get('action') == 'close_tab':
                            tab_id = cmd.get('data', {}).get('tabId')
                            cmd_id = cmd.get('id', 'unknown')
                            target_browser = cmd.get('browser_name', 'all')
                            logger.info(f"Sending close_tab command to {target_browser}: ID={cmd_id}, tabId={tab_id}")
                else:
                    logger.debug("No pending commands to return")
            
            return commands
    
    def clear_commands(self) -> None:
        """
        Clear all pending commands after they've been processed.
        """
        with self._commands_lock:
            count = len(self._commands)
            if count > 0:
                logger.info(f"Clearing {count} processed commands from queue")
            self._commands.clear()
    
    def get_tabs(self) -> Dict[str, Any]:
        """Get a thread-safe copy of the tab data.
        
        Returns:
            dict: A copy of the current tab data
        """
        with self._lock:
            return self._data.copy()
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """Get the currently active tab.
        
        Returns:
            dict or None: The active tab data or None if no active tab
        """
        with self._lock:
            active_tabs = [tab for tab in self._data.get("tabs", []) if tab.get("active")]
            return active_tabs[0] if active_tabs else None
    
    def is_extension_connected(self, browser_name: str = None) -> bool:
        """Check if the browser extension is connected.
        
        Args:
            browser_name: Optional browser name to check specific browser connection
        
        Returns:
            bool: True if the extension has sent data recently, False otherwise
        """
        with self._lock:
            current_time = time.time()
            
            # If browser_name is specified, check that specific browser
            if browser_name:
                last_update = self._data.get("browser_last_updates", {}).get(browser_name, 0)
                return (current_time - last_update) < 30 if last_update > 0 else False
            
            # Otherwise check if any browser is connected (for backward compatibility)
            if self._data.get("browser_last_updates"):
                # Check if any browser has updated recently
                for browser, last_update in self._data["browser_last_updates"].items():
                    if (current_time - last_update) < 30:
                        return True
            
            # Fall back to global last_update (for backward compatibility)
            return (current_time - self._data["last_update"]) < 30 if self._data["last_update"] > 0 else False
            
    def _should_block_url(self, url: str, domain: str, browser_name: str) -> bool:
        """Check if a URL should be blocked based on domain classifier.
        
        Args:
            url: The URL to check
            domain: The domain extracted from the URL
            browser_name: The name of the browser making the request
            
        Returns:
            bool: True if the URL should be blocked, False otherwise
        """
        # Log the request
        logger.info(f"Checking if URL should be blocked: {url} (domain: {domain}) from {browser_name}")
        
        # Use the classifier_blocker_api to determine if a URL should be blocked
        try:
            # Import the classifier_blocker_api module
            from core.integrations.classifier_blocker_api import should_block_tab
            
            # Create a tab info dictionary
            tab_info = {
                'url': url,
                'domain': domain,
                'metadata': {
                    'browser': browser_name
                }
            }
            
            # Get blocking decision from the classifier_blocker_api
            should_block, reason = should_block_tab(tab_info)
            
            if should_block:
                logger.info(f"Domain {domain} should be blocked. Reason: {reason}")
            else:
                logger.info(f"Domain {domain} allowed. Reason: {reason}")
                
            return should_block
        except Exception as e:
            # If classifier_blocker_api fails, fall back to simple check
            logger.error(f"Error using classifier_blocker_api: {e}")
            
            # Simple fallback check for common distracting sites
            distracting_domains = [
                "facebook.com", "twitter.com", "instagram.com", "tiktok.com",
                "reddit.com", "youtube.com", "netflix.com", "twitch.tv"
            ]
            
            for distracting_domain in distracting_domains:
                if distracting_domain in (domain or url):
                    logger.info(f"Domain {domain} matched distraction list, blocking")
                    return True
            
            logger.info(f"Domain {domain} not in distraction list, allowing")
            return False
    
    def _get_blocking_rules(self, browser_name: str) -> List[Dict[str, Any]]:
        """Get blocking rules for the browser extension.
        
        Args:
            browser_name: The name of the browser requesting rules
            
        Returns:
            List of rule dictionaries
        """
        logger.info(f"Getting blocking rules for browser: {browser_name}")
        
        # Use the classifier_blocker_api to get blocking rules
        try:
            # Import the classifier_blocker_api module
            from core.integrations.classifier_blocker_api import get_blocking_rules
            
            # Get rules from the classifier_blocker_api
            rules = get_blocking_rules()
            
            logger.info(f"Returning {len(rules)} blocking rules from classifier_blocker_api")
            return rules
        except Exception as e:
            # If classifier_blocker_api fails, fall back to simple rules
            logger.error(f"Error getting rules from classifier_blocker_api: {e}")
            
            # Simple fallback rules
            rules = [
                {"domain": "facebook.com", "category": "social", "reason": "Social media"},
                {"domain": "twitter.com", "category": "social", "reason": "Social media"},
                {"domain": "instagram.com", "category": "social", "reason": "Social media"},
                {"domain": "tiktok.com", "category": "social", "reason": "Social media"},
                {"domain": "reddit.com", "category": "social", "reason": "Social media"},
                {"domain": "youtube.com", "category": "entertainment", "reason": "Video streaming"},
                {"domain": "netflix.com", "category": "entertainment", "reason": "Video streaming"},
                {"domain": "twitch.tv", "category": "entertainment", "reason": "Video streaming"}
            ]
            
            logger.info(f"Returning {len(rules)} fallback blocking rules")
            return rules
    
    def _make_handler(self) -> Type[BaseHTTPRequestHandler]:
        """Create a request handler class with access to this server instance."""
        
        server_instance = self
        
        class TabRequestHandler(BaseHTTPRequestHandler):
            """HTTP request handler for tab server endpoints."""
            
            def do_OPTIONS(self):
                if self.path.startswith("/api/"):
                    self._set_headers(200)
                else:
                    self.send_error(404, "Not Found")
            
            def _set_headers(self, status_code=200, content_type="application/json"):
                """Set response headers with CORS support."""
                self.send_response(status_code)
                self.send_header("Content-Type", content_type)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Requested-With")
                self.send_header("Access-Control-Allow-Credentials", "true")
                self.send_header("Vary", "Origin")
                self.end_headers()
            
            def _handle_status(self) -> None:
                """Handle status requests."""
                current_time = time.time()
                
                # Get browser connection statuses
                browser_statuses = {}
                if "browser_last_updates" in server_instance._data:
                    for browser, last_update in server_instance._data["browser_last_updates"].items():
                        browser_statuses[browser] = {
                            "connected": (current_time - last_update) < 30,
                            "last_update": last_update
                        }
                
                # Check if any extension is connected
                any_connected = any(status.get("connected", False) for status in browser_statuses.values())
                
                status = {
                    "status": "ok",
                    "server": "FocusGuard Tab Server",
                    "timestamp": current_time,
                    "uptime": current_time - server_instance._data["server_start_time"],
                    "tab_count": len(server_instance._data.get("tabs", [])),
                    "last_update": server_instance._data["last_update"],
                    "extension_connected": any_connected,
                    "browser_statuses": browser_statuses
                }
                self._send_json(200, status)
            
            def _handle_get_tabs(self) -> None:
                """Handle requests for tab data."""
                self._send_json(200, server_instance.get_tabs())
            
            def _handle_get_commands(self) -> None:
                """Handle requests for pending commands."""
                # Parse query parameters to get browser name if provided
                query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                browser_name = None
                if 'browser' in query_components:
                    browser_name = query_components['browser'][0]
                    logger.info(f"Command request from browser: {browser_name}")
                
                # Get commands filtered by browser name
                commands = server_instance.get_commands(browser_name)
                self._send_json(200, {"commands": commands})
                
            def _handle_should_block(self) -> None:
                """Handle requests to check if a URL should be blocked."""
                # Parse query parameters
                query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                url = query_components.get('url', [''])[0]
                domain = query_components.get('domain', [''])[0]
                browser_name = query_components.get('browser', ['Unknown'])[0]
                
                if not url and not domain:
                    self._send_json(400, {"error": "URL or domain parameter required"})
                    return
                
                # If path includes /rules, return all blocking rules
                if self.path.endswith('/rules'):
                    # This would typically come from the domain classifier
                    # For now, return a simple example
                    rules = server_instance._get_blocking_rules(browser_name)
                    self._send_json(200, {"rules": rules})
                    return
                
                # Check if URL should be blocked
                should_block = server_instance._should_block_url(url, domain, browser_name)
                self._send_json(200, {
                    "should_block": should_block,
                    "url": url,
                    "domain": domain,
                    "browser": browser_name,
                    "timestamp": time.time()
                })
            
            def _handle_post_tabs(self) -> None:
                """Handle incoming tab data updates."""
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length == 0:
                    self._send_json(400, {"error": "No data received"})
                    return
                
                try:
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode())
                    
                    # Validate required fields
                    if "tabs" not in data:
                        self._send_json(400, {"error": "Missing required field: tabs"})
                        return
                    
                    if "browser" not in data:
                        logger.warning("Received tab data without browser information")
                        # Add default browser info to prevent errors
                        data["browser"] = {"name": "Unknown", "version": "Unknown"}
                    
                    # Process the data
                    server_instance.update_tabs(data)
                    
                    # Send success response with detailed info
                    self._send_json(200, {
                        "status": "ok",
                        "tabs_received": len(data.get("tabs", [])),
                        "timestamp": time.time(),
                        "browser": data.get("browser", {}).get("name", "Unknown")
                    })
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    self._send_json(400, {"error": "Invalid JSON", "details": str(e)})
                except ValueError as e:
                    logger.error(f"Invalid data format: {e}")
                    self._send_json(400, {"error": "Invalid data format", "details": str(e)})
                except Exception as e:
                    logger.error(f"Error processing tab data: {e}")
                    self._send_json(500, {"error": "Internal Server Error", "details": str(e)})
            
            def _handle_post_commands(self) -> None:
                """Handle command acknowledgments from the browser extension."""
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length == 0:
                    self._send_json(400, {"error": "No data received"})
                    return
                
                try:
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode())
                    
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

            def _send_json(self, code: int, data: Dict[str, Any]) -> None:
                """Send a JSON response.
                
                Args:
                    code: HTTP status code
                    data: Data to send as JSON
                """
                self._set_headers(code)
                self.wfile.write(json.dumps(data).encode())
            
            def log_message(self, format, *args):
                logger.debug(f"{self.address_string()} - {format % args}")
        
        return TabRequestHandler

# Singleton instance
tab_server = TabServer()

def get_tab_server() -> TabServer:
    return tab_server

def start_tab_server(port: int = None) -> bool:
    return tab_server.start(port)

def stop_tab_server():
    tab_server.stop()

def is_running() -> bool:
    return tab_server._running if tab_server else False