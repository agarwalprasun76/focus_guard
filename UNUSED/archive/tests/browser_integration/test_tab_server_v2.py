#!/usr/bin/env python
"""
Unit tests for the TabServer V2 class
"""

import unittest
import json
import time
import threading
import http.client
from unittest.mock import patch, MagicMock, ANY
from core.logger.logger import get_logger

logger = get_logger("browser_integration.test_tab_server_v2")

# Add project root to Python path to import modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.browser_integration.tab_server_v2 import TabServer, get_tab_server

class TestTabServerV2(unittest.TestCase):
    """Test cases for the TabServer V2 class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a tab server with a non-default port to avoid conflicts
        self.test_port = 5555
        self.tab_server = TabServer(port=self.test_port)
        
        # Sample tab data for testing
        self.sample_tabs = {
            "tabs": [
                {
                    "id": 1,
                    "url": "https://example.com",
                    "title": "Example Domain",
                    "active": True
                },
                {
                    "id": 2,
                    "url": "https://test.com",
                    "title": "Test Website",
                    "active": False
                }
            ],
            "browser": {
                "name": "Microsoft Edge",
                "version": "100.0.0.0"
            }
        }
    
    def tearDown(self):
        """Clean up after tests"""
        import time
        print(f"[DEBUG] {time.time()} - Starting tearDown")
        # Stop the server if it's running
        self.tab_server.stop()
        print(f"[DEBUG] {time.time()} - Called self.tab_server.stop()")
        # Defensive: ensure server thread is dead
        if getattr(self.tab_server, '_server_thread', None) and self.tab_server._server_thread.is_alive():
            print(f"[DEBUG] {time.time()} - Server thread is alive before join, joining with timeout 1s")
            self.tab_server._server_thread.join(timeout=1.0)
            print(f"[DEBUG] {time.time()} - Finished join on server thread")
            if self.tab_server._server_thread.is_alive():
                print(f"[DEBUG][WARNING] {time.time()} - Server thread STILL ALIVE after join!")
        print(f"[DEBUG] {time.time()} - Finished tearDown")

    
    def test_singleton_pattern(self):
        """Test that get_tab_server returns a singleton instance"""
        server1 = get_tab_server()
        server2 = get_tab_server()
        
        # Check that both references point to the same instance
        self.assertIs(server1, server2)
    
    def test_is_port_available(self):
        """Test port availability check"""
        logger.info("Checking if port %s is initially available...", self.test_port)
        self.assertTrue(self.tab_server.is_port_available(self.test_port))
        logger.info("Port %s is initially available.", self.test_port)
        
        logger.info("Starting the tab server on port %s...", self.test_port)
        self.tab_server.start()
        logger.info("Tab server started on port %s.", self.test_port)
        
        logger.info("Checking if port %s is now unavailable...", self.test_port)
        self.assertFalse(self.tab_server.is_port_available(self.test_port))
        logger.info("Port %s is now unavailable as expected.", self.test_port)
        
        logger.info("Stopping the tab server on port %s...", self.test_port)
        self.tab_server.stop()
        logger.info("Tab server stopped on port %s.", self.test_port)
        
        logger.info("Checking if port %s is available again...", self.test_port)
        self.assertTrue(self.tab_server.is_port_available(self.test_port))
        logger.info("Port %s is available again after stopping the server.", self.test_port)
    
    def test_start_stop(self):
        """Test starting and stopping the server"""
        # Start the server
        result = self.tab_server.start()
        self.assertTrue(result)
        self.assertTrue(self.tab_server._running.is_set())
        
        # Try starting again (should return True but not restart)
        result = self.tab_server.start()
        self.assertTrue(result)
        
        # Stop the server
        self.tab_server.stop()
        self.assertFalse(self.tab_server._running.is_set())
        
        # Stop again (should be a no-op)
        self.tab_server.stop()
    
    def test_update_get_tabs(self):
        """Test updating and retrieving tab data"""
        # Update the tabs
        self.tab_server.update_tabs(self.sample_tabs)
        
        # Get the tabs
        tabs = self.tab_server.get_tabs()
        
        # Check that the tabs were updated
        self.assertEqual(tabs["tabs"], self.sample_tabs["tabs"])
        self.assertEqual(tabs["browser"], self.sample_tabs["browser"])
        self.assertGreater(tabs["last_update"], 0)
    
    def test_get_active_tab(self):
        """Test getting the active tab"""
        # Update the tabs
        self.tab_server.update_tabs(self.sample_tabs)
        
        # Get the active tab
        active_tab = self.tab_server.get_active_tab()
        
        # Check that the active tab was returned
        self.assertEqual(active_tab["id"], 1)
        self.assertEqual(active_tab["url"], "https://example.com")
        self.assertEqual(active_tab["title"], "Example Domain")
        self.assertTrue(active_tab["active"])
        
        # Test with no active tab
        no_active_tabs = {
            "tabs": [
                {
                    "id": 1,
                    "url": "https://example.com",
                    "title": "Example Domain",
                    "active": False
                }
            ]
        }
        self.tab_server.update_tabs(no_active_tabs)
        self.assertIsNone(self.tab_server.get_active_tab())
    
    def test_is_extension_connected(self):
        """Test checking if the extension is connected"""
        # Initially, the extension should not be connected
        self.assertFalse(self.tab_server.is_extension_connected())
        
        # Update the tabs to simulate extension connection
        self.tab_server.update_tabs(self.sample_tabs)
        
        # Now the extension should be connected
        self.assertTrue(self.tab_server.is_extension_connected())
        
        # Manually set last_update to simulate disconnection
        with self.tab_server._lock:
            self.tab_server._data["last_update"] = time.time() - 31
        
        # Now the extension should be disconnected
        self.assertFalse(self.tab_server.is_extension_connected())
    
    @patch('core.browser_integration.tab_server_v2.ThreadingHTTPServer')
    def test_server_error_handling(self, mock_server):
        """Test error handling when starting the server"""
        # Make the server raise an exception when started
        mock_server.side_effect = Exception("Test server error")
        
        # Try to start the server
        result = self.tab_server.start()
        
        # Check that the start method returned False
        self.assertFalse(result)
        self.assertFalse(self.tab_server._running.is_set())

from core.browser_integration.tab_server_v2 import TabServer

@patch('threading.Thread')
def test_server_thread_error(mock_thread, capsys):
    tab_server = TabServer()
    mock_thread_instance = MagicMock()
    mock_thread.return_value = mock_thread_instance

    with patch.object(tab_server, '_server', MagicMock()):
        tab_server.start()
        target_func = mock_thread.call_args[1]['target']
        with patch.object(tab_server._server, 'handle_request', side_effect=Exception("Test thread error")):
            target_func()
            captured = capsys.readouterr()
            assert "Error in server thread: Test thread error" in captured.out
        assert not tab_server._running.is_set()


class TestTabServerIntegration(unittest.TestCase):
    """Integration tests for the TabServer V2 class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for the class"""
        # Use a high port number to avoid conflicts
        cls.test_port = 5678
        cls.tab_server = TabServer(port=cls.test_port)
        
        # Start the server
        cls.tab_server.start()
        
        # Wait for the server to start
        time.sleep(0.5)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        # Stop the server
        cls.tab_server.stop()
    
    def test_server_status_endpoint(self):
        """Test the /api/status endpoint"""
        # Connect to the server
        conn = http.client.HTTPConnection("localhost", self.test_port)
        
        try:
            # Send a GET request to /api/status
            conn.request("GET", "/api/status")
            
            # Get the response
            response = conn.getresponse()
            
            # Check the status code
            self.assertEqual(response.status, 200)
            
            # Parse the response body
            body = json.loads(response.read().decode())
            
            # Check the response fields
            self.assertEqual(body["status"], "ok")
            self.assertEqual(body["server"], "FocusGuard Tab Server")
            self.assertIn("timestamp", body)
            self.assertIn("uptime", body)
            self.assertIn("tab_count", body)
            self.assertIn("last_update", body)
        finally:
            conn.close()
    
    def test_server_tabs_endpoint(self):
        """Test the /api/tabs endpoint"""
        # Connect to the server
        conn = http.client.HTTPConnection("localhost", self.test_port)
        
        try:
            # Send a GET request to /api/tabs
            conn.request("GET", "/api/tabs")
            
            # Get the response
            response = conn.getresponse()
            
            # Check the status code
            self.assertEqual(response.status, 200)
            
            # Parse the response body
            body = json.loads(response.read().decode())
            
            # Check the response fields
            self.assertIn("tabs", body)
            self.assertIn("browser", body)
            self.assertIn("last_update", body)
            self.assertIn("server_start_time", body)
        finally:
            conn.close()
    
    def test_server_post_tabs(self):
        """Test posting tab data to the server"""
        # Sample tab data
        sample_tabs = {
            "tabs": [
                {
                    "id": 1,
                    "url": "https://example.com",
                    "title": "Example Domain",
                    "active": True
                }
            ],
            "browser": {
                "name": "Microsoft Edge",
                "version": "100.0.0.0"
            }
        }
        
        # Connect to the server
        conn = http.client.HTTPConnection("localhost", self.test_port)
        
        try:
            # Send a POST request to /api/tabs
            headers = {"Content-Type": "application/json"}
            conn.request("POST", "/api/tabs", json.dumps(sample_tabs).encode(), headers)
            
            # Get the response
            response = conn.getresponse()
            
            # Check the status code
            self.assertEqual(response.status, 200)
            
            # Parse the response body
            body = json.loads(response.read().decode())
            
            # Check the response fields
            self.assertEqual(body["status"], "ok")
            self.assertEqual(body["tabs_received"], 1)
            self.assertIn("timestamp", body)
            
            # Check that the tabs were updated
            tabs = self.tab_server.get_tabs()
            self.assertEqual(len(tabs["tabs"]), 1)
            self.assertEqual(tabs["tabs"][0]["url"], "https://example.com")
            self.assertEqual(tabs["browser"]["name"], "Microsoft Edge")
        finally:
            conn.close()
    
    def test_server_cors_headers(self):
        """Test that CORS headers are set correctly"""
        # Connect to the server
        conn = http.client.HTTPConnection("localhost", self.test_port)
        
        try:
            # Send an OPTIONS request
            conn.request("OPTIONS", "/api/tabs")
            
            # Get the response
            response = conn.getresponse()
            
            # Check the status code
            self.assertEqual(response.status, 200)
            
            # Check the CORS headers
            headers = {k.lower(): v for k, v in response.getheaders()}
            self.assertEqual(headers["access-control-allow-origin"], "*")
            self.assertIn("get", headers["access-control-allow-methods"].lower())
            self.assertIn("post", headers["access-control-allow-methods"].lower())
            self.assertIn("options", headers["access-control-allow-methods"].lower())
            self.assertEqual(headers["access-control-allow-credentials"], "true")
            self.assertEqual(headers["vary"], "Origin")
        finally:
            conn.close()

if __name__ == '__main__':
    unittest.main()
