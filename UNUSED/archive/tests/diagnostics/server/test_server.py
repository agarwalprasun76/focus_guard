#!/usr/bin/env python
"""
Test server that mimics the tab server to check if connections are working properly.
"""

import sys
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading

# Add project root to Python path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from core.logger.logger import get_logger

# Setup logger
logger = get_logger("server.test")

class TestHandler(BaseHTTPRequestHandler):
    """Test HTTP request handler."""
    
    def __init__(self, *args, **kwargs):
        self.logger = get_logger("test_server")
        super().__init__(*args, **kwargs)
    
    def _set_headers(self, status_code=200, content_type="application/json"):
        """Set response headers."""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self._set_headers()
        self.wfile.write(b'')
    
    def do_GET(self):
        """Handle GET requests."""
        self.logger.info(f"Received GET request: {self.path}")
        
        if self.path == "/api/status":
            self._set_headers()
            response = {"status": "ok", "server": "Test Server"}
            self.wfile.write(json.dumps(response).encode())
        else:
            self._set_headers(404)
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        self.logger.info(f"Received POST request: {self.path}")
        
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode())
                self.logger.info(f"Received data: {data}")
            except:
                self.logger.error("Failed to parse JSON data")
        
        self._set_headers()
        response = {"status": "ok"}
        self.wfile.write(json.dumps(response).encode())
        
    def log_message(self, format, *args):
        """Override log_message to use our logger instead."""
        self.logger.debug(f"{self.client_address[0]} - {format%args}")


def run_server():
    """Run the test server."""
    host = "localhost"
    port = 5000
    
    try:
        server = HTTPServer((host, port), TestHandler)
        logger.info(f"Test server started on http://{host}:{port}")
        logger.info("Press Ctrl+C to stop the server")
        server.serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {port} is already in use. Is another server running?")
        else:
            logger.error(f"Error starting server: {e}")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if 'server' in locals():
            server.server_close()
            logger.info("Server stopped")


if __name__ == "__main__":
    run_server()
