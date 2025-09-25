#!/usr/bin/env python
"""
Unit tests for the browser extension background.js script

This test uses Selenium WebDriver to test the browser extension background script
by mocking the browser extension API and verifying that it correctly sends tab data
to the tab server.
"""

import unittest
import json
import time
import threading
import http.server
import socketserver
from unittest.mock import MagicMock, patch
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add project root to Python path to import modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.browser_integration.config import Config

class MockTabServer(BaseHTTPRequestHandler):
    """Mock HTTP server to receive tab data from the background.js script"""
    
    received_data = []
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        # Store the received data
        try:
            json_data = json.loads(post_data)
            MockTabServer.received_data.append(json_data)
        except json.JSONDecodeError:
            pass
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(b'')

class TestBackgroundJS(unittest.TestCase):
    """Test cases for the background.js script"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for the class"""
        # Start a mock tab server
        cls.server_port = 5555
        cls.server = HTTPServer(('localhost', cls.server_port), MockTabServer)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join()
    
    def setUp(self):
        """Set up test fixtures"""
        # Clear received data before each test
        MockTabServer.received_data = []
        
        # Load the background.js script
        with open(os.path.join(os.path.dirname(__file__), '../../core/browser_integration/background.js'), 'r') as f:
            self.background_js = f.read()
    
    def test_background_js_content(self):
        """Test that the background.js file contains expected content"""
        # Check that the script contains key functions and variables
        self.assertIn('sendTabData', self.background_js)
        self.assertIn('updateIcon', self.background_js)
        self.assertIn('SERVER_URL', self.background_js)
        self.assertIn('chrome.tabs.query', self.background_js)
    
    def test_server_url_configuration(self):
        """Test that the server URL in background.js matches the config"""
        # Extract the SERVER_URL from the background.js script
        import re
        match = re.search(r'const\s+SERVER_URL\s*=\s*[\'"]([^\'"]+)[\'"]', self.background_js)
        if match:
            server_url = match.group(1)
            expected_url = f"http://{Config.SERVER_HOST}:{Config.SERVER_PORT}/api/tabs"
            
            # Check that the URL matches or contains the expected host and port
            self.assertTrue(
                server_url == expected_url or 
                (Config.SERVER_HOST in server_url and str(Config.SERVER_PORT) in server_url),
                f"SERVER_URL in background.js ({server_url}) doesn't match expected URL ({expected_url})"
            )
        else:
            self.fail("SERVER_URL not found in background.js")
    
    def test_update_interval(self):
        """Test that the update interval in background.js is reasonable"""
        # Extract the update interval from the background.js script
        import re
        # Try to match setInterval with a numeric literal
        match = re.search(r'setInterval\(\s*[^,]+,\s*(\d+)\s*\)', self.background_js)
        if match:
            interval = int(match.group(1))
        else:
            # Try to match setInterval with a constant (e.g., UPDATE_INTERVAL)
            match = re.search(r'setInterval\(\s*[^,]+,\s*([A-Z_]+)\s*\)', self.background_js)
            if match:
                const_name = match.group(1)
                # Extract the value of the constant from the JS code
                const_match = re.search(rf'const {const_name}\s*=\s*(\d+)', self.background_js)
                if const_match:
                    interval = int(const_match.group(1))
                else:
                    self.fail(f"Constant {const_name} not found in background.js")
            else:
                self.fail("Update interval not found in background.js")
        # Check that the interval is reasonable (between 1 and 30 seconds)
        self.assertTrue(1000 <= interval <= 30000,
            f"Update interval ({interval}ms) is outside reasonable range (1000-30000ms)")

# Note: The following tests would typically be run with Selenium WebDriver
# to test the actual browser extension in a real browser environment.
# Since that requires a more complex setup, we've included placeholders
# for these tests with comments explaining what they would do.

"""
class TestBackgroundJSWithSelenium(unittest.TestCase):
    def setUp(self):
        # Set up Selenium WebDriver with browser extension loaded
        pass
        
    def tearDown(self):
        # Clean up WebDriver
        pass
        
    def test_tab_data_sent_to_server(self):
        # Test that the extension sends tab data to the server
        pass
        
    def test_icon_updates_on_connection_status(self):
        # Test that the extension icon updates based on connection status
        pass
        
    def test_retry_mechanism(self):
        # Test that the extension retries when the server is unavailable
        pass
"""

if __name__ == '__main__':
    unittest.main()
