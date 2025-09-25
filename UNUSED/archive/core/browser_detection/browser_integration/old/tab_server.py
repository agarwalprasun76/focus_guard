"""
Browser Tab Server

This module provides a server that receives tab information from browser extensions
and makes it available to the rest of the FocusGuard application.
"""

import json
import threading
import time
from typing import Dict, List, Optional, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from core.logger.logger import get_logger

# Global state
tab_data = {
    "last_update": 0,
    "browser": None,
    "tabs": []
}

# Lock for thread-safe access to tab_data
tab_data_lock = threading.Lock()

class TabServerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the tab server."""
    
    def __init__(self, *args, **kwargs):
        self.logger = get_logger("tab_server")
        super().__init__(*args, **kwargs)
    
    def _set_headers(self, status_code=200, content_type="application/json"):
        """Set response headers."""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Requested-With")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Vary", "Origin")
        self.end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self._set_headers(200)
        self.wfile.write(b'')
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        self.logger.info(f"GET request received: {path}")
        
        if path == "/api/status":
            # Status endpoint
            self.logger.info("Handling status check")
            self._set_headers()
            response = {
                "status": "ok", 
                "server": "FocusGuard Tab Server",
                "timestamp": time.time(),
                "tab_count": len(tab_data.get("tabs", [])),
                "last_update": tab_data.get("last_update", 0)
            }
            self.wfile.write(json.dumps(response).encode())
        
        elif path == "/api/tabs":
            # Get current tab data
            self.logger.info(f"Returning current tab data: {len(tab_data.get('tabs', []))} tabs")
            with tab_data_lock:
                response = tab_data.copy()
            
            self._set_headers()
            self.wfile.write(json.dumps(response).encode())
        
        else:
            # Unknown endpoint
            self.logger.warning(f"Unknown endpoint accessed: {path}")
            self._set_headers(404)
            response = {"error": "Not found", "requested_path": path}
            self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        self.logger.info(f"POST request received: {path}")
        
        if path == "/api/tabs":
            # Update tab data
            content_length = int(self.headers.get("Content-Length", 0))
            self.logger.info(f"Content-Length: {content_length}")
            
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                self.logger.info(f"Raw POST data: {post_data[:500]}...")  # Log first 500 chars
                
                try:
                    data = json.loads(post_data.decode())
                    self.logger.info(f"Parsed JSON data. Browser: {data.get('browser', {}).get('name', 'unknown')}")
                    
                    # Update global tab data
                    with tab_data_lock:
                        tab_data["last_update"] = time.time()
                        tab_data["browser"] = data.get("browser", {})
                        tab_data["tabs"] = data.get("tabs", [])
                    
                    tab_count = len(data.get("tabs", []))
                    self.logger.info(f"Received {tab_count} tabs from {data.get('browser', {}).get('name', 'unknown browser')}")
                    
                    # Send success response
                    self._set_headers(200)
                    response = {
                        "status": "ok", 
                        "tabs_received": tab_count,
                        "timestamp": time.time()
                    }
                    self.wfile.write(json.dumps(response).encode())
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode error: {str(e)}")
                    self._set_headers(400)
                    response = {
                        "error": "Invalid JSON",
                        "details": str(e)
                    }
                    self.wfile.write(json.dumps(response).encode())
                except Exception as e:
                    self.logger.error(f"Error processing request: {str(e)}")
                    self._set_headers(500)
                    response = {
                        "error": "Internal server error",
                        "details": str(e)
                    }
                    self.wfile.write(json.dumps(response).encode())
            else:
                self.logger.warning("Empty POST request received")
                self._set_headers(400)
                response = {
                    "error": "Empty request",
                    "details": "No data received in POST body"
                }
                self.wfile.write(json.dumps(response).encode())
        else:
            # Unknown endpoint
            self.logger.warning(f"Unknown POST endpoint: {path}")
            self._set_headers(404)
            response = {
                "error": "Not found",
                "requested_path": path,
                "supported_endpoints": ["/api/status", "/api/tabs"]
            }
            self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Override log_message to use our logger."""
        self.logger.debug(f"{self.address_string()} - {format % args}")


class TabServer:
    """Server that receives tab information from browser extensions."""
    
    def __init__(self, host="localhost", port=5000):
        """Initialize the tab server."""
        self.logger = get_logger("tab_server")
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
    
    def start(self):
        """Start the tab server."""
        if self.running:
            self.logger.warning("Tab server already running")
            return
        
        try:
            # Check if the port is already in use
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind((self.host, self.port))
                s.close()
            except socket.error as e:
                if 'Address already in use' in str(e):
                    self.logger.error(f"Port {self.port} is already in use. Cannot start tab server.")
                    return
                else:
                    self.logger.error(f"Socket error checking port {self.port}: {e}")
                    return
            
            # Try to start the server
            self.server = HTTPServer((self.host, self.port), TabServerHandler)
            self.server_thread = threading.Thread(target=self._serve_with_error_handling)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # Verify server is listening by attempting to connect
            time.sleep(0.5)  # Give server time to start
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.0)
                s.connect((self.host, self.port))
                s.close()
                self.running = True
                self.logger.info(f"Tab server started successfully on http://{self.host}:{self.port}")
            except Exception as e:
                self.logger.error(f"Failed to verify tab server is running: {e}")
                if self.server:
                    self.server.shutdown()
                    self.server.server_close()
                return
        except Exception as e:
            self.logger.error(f"Failed to start tab server: {e}")
    
    def _serve_with_error_handling(self):
        """Serve forever with error handling."""
        try:
            self.server.serve_forever()
        except Exception as e:
            self.logger.error(f"Error in tab server thread: {e}")
            self.running = False
    
    def stop(self):
        """Stop the tab server."""
        if not self.running:
            return
        
        try:
            self.server.shutdown()
            self.server.server_close()
            self.running = False
            self.logger.info("Tab server stopped")
        except Exception as e:
            self.logger.error(f"Error stopping tab server: {e}")
    
    @staticmethod
    def get_tabs() -> List[Dict[str, Any]]:
        """Get the current tab data."""
        with tab_data_lock:
            return tab_data["tabs"].copy()
    
    @staticmethod
    def get_active_tab() -> Optional[Dict[str, Any]]:
        """Get the currently active tab."""
        with tab_data_lock:
            active_tabs = [tab for tab in tab_data["tabs"] if tab.get("active")]
            return active_tabs[0] if active_tabs else None
    
    @staticmethod
    def get_last_update_time() -> float:
        """Get the timestamp of the last update."""
        with tab_data_lock:
            return tab_data["last_update"]
    
    @staticmethod
    def is_extension_connected() -> bool:
        """Check if the browser extension is connected."""
        with tab_data_lock:
            # Consider the extension disconnected if no updates in the last 30 seconds
            return (time.time() - tab_data["last_update"]) < 30 if tab_data["last_update"] > 0 else False


# Singleton instance
_tab_server_instance = None

def get_tab_server() -> TabServer:
    """Get the singleton tab server instance."""
    global _tab_server_instance
    if _tab_server_instance is None:
        _tab_server_instance = TabServer()
    return _tab_server_instance
