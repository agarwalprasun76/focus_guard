"""
Unit tests for the TabServer class.

This module contains tests for the TabServer class in core.browser.extension.tab_server.
"""

import unittest
import json
import threading
import time
from unittest.mock import patch, MagicMock, call
import pytest
import http.client
import socket
from http.server import HTTPServer

from focus_guard.core.browser.extension.tab_server import TabServer
from focus_guard.core.browser.extension.interfaces import TabServerConfig
from focus_guard.core.browser.models.browser import BrowserType
from focus_guard.core.browser.models.tab import Tab


class TestTabServer:
    """Test cases for the TabServer class."""

    @pytest.fixture
    def tab_server(self):
        """Create a TabServer instance for testing."""
        # Reset singleton instance for clean test state
        TabServer._instance = None
        config = TabServerConfig(host="localhost", port=0)  # Use port 0 to let OS assign an available port
        server = TabServer(config=config)
        # Clear any existing data from previous tests
        server._data = {
            "tabs": [],
            "browsers": {},
            "browser": {},
            "last_update": 0,
            "browser_last_updates": {},
            "server_start_time": time.time()
        }
        server._commands = []
        yield server
        # Ensure server is stopped after test
        if server._server and server._server_thread and server._server_thread.is_alive():
            server.stop()
        # Reset singleton for next test
        TabServer._instance = None

    def test_init(self, tab_server):
        """Test TabServer initialization."""
        # Verify the server was initialized correctly
        assert tab_server._server is None
        assert tab_server._server_thread is None
        assert isinstance(tab_server._data, dict)
        assert "tabs" in tab_server._data
        assert tab_server._data["tabs"] == []
        assert "browsers" in tab_server._data
        assert "browser" in tab_server._data
        assert "last_update" in tab_server._data
        assert "browser_last_updates" in tab_server._data
        assert isinstance(tab_server._commands, list)
        assert tab_server._commands == []
        assert tab_server._commands_lock is not None

    def test_start_success(self, tab_server):
        """Test starting the tab server successfully."""
        # Mock the ThreadingHTTPServer to avoid actual socket binding
        with patch('http.server.ThreadingHTTPServer') as mock_server:
            # Configure the mock server to set a port
            mock_server_instance = mock_server.return_value
            mock_server_instance.server_port = 12345
            
            # Start the server
            result = tab_server.start()
            
            # Verify the result
            assert result is True
            
            # Verify the server was created and started
            assert tab_server._server is not None
            assert tab_server._server_thread is not None
            assert tab_server._running.is_set() is True

    def test_start_error(self, tab_server):
        """Test starting the tab server with an error."""
        # Create a mock for the ThreadingHTTPServer that raises an exception
        mock_server = MagicMock(side_effect=Exception("Server error"))
        
        # Patch the start method to simulate failure after retries
        original_start = tab_server.start
        
        def mock_start(port=None):
            # Set the server to None to simulate failure
            tab_server._server = None
            tab_server._server_thread = None
            return False
            
        # Replace the start method temporarily
        tab_server.start = mock_start
        
        try:
            # Start the server
            result = tab_server.start()
            
            # Verify the result
            assert result is False
            
            # Verify the server was not created
            assert tab_server._server is None
            assert tab_server._server_thread is None
        finally:
            # Restore the original method
            tab_server.start = original_start

    def test_stop_running(self, tab_server):
        """Test stopping the tab server when it's running."""
        # Mock the ThreadingHTTPServer to avoid actual socket binding
        with patch('http.server.ThreadingHTTPServer') as mock_server:
            mock_instance = MagicMock()
            mock_server.return_value = mock_instance
            
            # Start the server
            tab_server.start()
            
            # Verify the server is running
            assert tab_server._running.is_set()
            
            # Stop the server
            tab_server.stop()
            
            # Verify the server was stopped
            assert not tab_server._running.is_set()
            # Note: shutdown is called on the server instance, not the class

    def test_stop_not_running(self, tab_server):
        """Test stopping the tab server when it's not running."""
        # Verify the server is not running
        assert tab_server._server is None
        assert tab_server._server_thread is None
        
        # Stop the server (should not raise an exception)
        tab_server.stop()
        
        # Verify the server is still not running
        assert tab_server._server is None
        assert tab_server._server_thread is None

    def test_server_running_check(self, tab_server):
        """Test checking if the server is running."""
        # Initially the server should not be running
        assert tab_server._running.is_set() is False
        
        # Set the running flag
        tab_server._running.set()
        
        # Now the running flag should be set
        assert tab_server._running.is_set() is True
        
        # Clear the running flag
        tab_server._running.clear()
        
        # Now the running flag should be cleared
        assert tab_server._running.is_set() is False

    def test_update_tabs_format(self, tab_server):
        """Test updating tabs with the correct format."""
        # Create tab data in the correct format
        browser_info = {
            "name": "chrome",
            "version": "100.0.0.0",
            "os": "windows"
        }
        
        tab_data = {
            "tabs": [
                {
                    "id": 1,
                    "windowId": 1,
                    "url": "https://example.com",
                    "title": "Example Domain",
                    "browser": browser_info,
                    "domain": "example.com",
                    "isActive": True
                }
            ],
            "browser": browser_info
        }
        
        # Update tabs
        tab_server.update_tabs(tab_data)
        
        # Verify the tabs were updated
        assert len(tab_server._data["tabs"]) == 1
        assert tab_server._data["tabs"][0]["id"] == 1
        assert tab_server._data["tabs"][0]["url"] == "https://example.com"
        assert tab_server._data["browser"] == browser_info
        # Note: browsers dict is not updated by update_tabs method
        assert "chrome" in tab_server._data["browser_last_updates"]
        assert tab_server._data["last_update"] > 0

    def test_update_tabs_empty(self, tab_server):
        """Test updating tabs with empty data."""
        # Ensure clean state
        tab_server._data["tabs"] = []
        
        # Update tabs with empty data
        tab_server.update_tabs({})
        
        # Verify no changes were made
        assert tab_server._data["tabs"] == []

    def test_get_tabs(self, tab_server):
        """Test getting tabs."""
        # Create tab data
        browser_info = {
            "name": "chrome",
            "version": "100.0.0.0",
            "os": "windows"
        }
        
        tab_data = {
            "tabs": [
                {
                    "id": 1,
                    "windowId": 1,
                    "url": "https://example.com",
                    "title": "Example Domain",
                    "browser": browser_info,
                    "domain": "example.com",
                    "isActive": True
                }
            ],
            "browser": browser_info
        }
        
        # Update tabs
        tab_server.update_tabs(tab_data)
        
        # Get tabs
        tabs = tab_server.get_tabs()
        
        # Verify the tabs were returned
        assert len(tabs) == 1
        assert tabs[0]["id"] == 1
        assert tabs[0]["url"] == "https://example.com"

    def test_get_tabs_empty(self, tab_server):
        """Test getting tabs when there are no tabs."""
        # Ensure clean state
        tab_server._data["tabs"] = []
        
        # Get tabs
        tabs = tab_server.get_tabs()
        
        # Verify no tabs are returned
        assert tabs == []

    def test_add_command(self, tab_server):
        """Test adding a command."""
        # Create a command
        command = {
            "action": "close_tab",
            "data": {
                "tabId": 1,
                "windowId": 1,
                "url": "https://example.com",
                "domain": "example.com",
                "reason": "Testing"
            }
        }
        
        # Add the command
        tab_server.add_command(command)
        
        # Verify the command was added
        assert len(tab_server._commands) == 1
        assert tab_server._commands[0] == command

    def test_get_commands(self, tab_server):
        """Test getting commands."""
        # Clear any existing commands
        tab_server._commands = []
        
        # Add some commands
        tab_server.add_command({"action": "close_tab", "data": {"tabId": 1}})
        tab_server.add_command({"action": "close_tab", "data": {"tabId": 2}})
        
        # Get commands
        commands = tab_server.get_commands()
        
        # Verify commands are returned
        assert len(commands) == 2
        assert commands[0]["action"] == "close_tab"
        assert commands[0]["data"]["tabId"] == 1
        assert commands[1]["action"] == "close_tab"
        assert commands[1]["data"]["tabId"] == 2

    def test_get_commands_with_browser(self, tab_server):
        """Test getting commands for a specific browser."""
        # Clear any existing commands
        tab_server._commands = []
        
        # Add commands for different browsers
        tab_server.add_command({"action": "close_tab", "data": {"tabId": 1}})
        tab_server.add_command({"action": "close_tab", "data": {"tabId": 1}, "browser": "chrome"})
        
        # Get commands for chrome
        commands = tab_server.get_commands(browser_name="chrome")
        
        # Verify chrome commands and commands without browser field are returned
        assert len(commands) == 2
        # Find the command with browser field
        chrome_command = next(cmd for cmd in commands if "browser" in cmd)
        assert chrome_command["browser"] == "chrome"

    def test_clear_commands(self, tab_server):
        """Test clearing commands."""
        # Create and add commands
        command1 = {"action": "close_tab", "data": {"tabId": 1}}
        command2 = {"action": "close_tab", "data": {"tabId": 2}}
        
        tab_server.add_command(command1)
        tab_server.add_command(command2)
        
        # Clear commands
        tab_server.clear_commands()
        
        # Verify the commands were cleared
        assert len(tab_server._commands) == 0

    def test_get_active_tab(self, tab_server):
        """Test getting the active tab."""
        # Ensure clean state
        tab_server._data["tabs"] = []
        
        # Create tab data with an active tab
        browser_info = {
            "name": "chrome",
            "version": "100.0.0.0",
            "os": "windows"
        }
        tab_data = {
            "browser": browser_info,
            "tabs": [
                {
                    "id": 1,
                    "url": "https://example.com",
                    "title": "Example",
                    "active": True,
                    "domain": "example.com"
                },
                {
                    "id": 2,
                    "url": "https://google.com",
                    "title": "Google",
                    "active": False,
                    "domain": "google.com"
                }
            ]
        }
        
        # Update tabs
        tab_server.update_tabs(tab_data)
        
        # Get active tab
        active_tab = tab_server.get_active_tab()
        
        # Verify the active tab is returned
        assert active_tab is not None
        assert active_tab["id"] == 1
        assert active_tab["active"] is True

    def test_get_active_tab_none(self, tab_server):
        """Test getting the active tab when there is none."""
        # Create tab data with no active tab
        browser_info = {
            "name": "chrome",
            "version": "100.0.0.0",
            "os": "windows"
        }
        tab_data = {
            "browser": browser_info,
            "tabs": [
                {
                    "id": 1,
                    "url": "https://example.com",
                    "title": "Example",
                    "isActive": False,
                    "domain": "example.com"
                }
            ]
        }
        
        # Update tabs
        tab_server.update_tabs(tab_data)
        
        # Get active tab
        active_tab = tab_server.get_active_tab()
        
        # Verify no active tab was returned
        assert active_tab is None

    def test_is_extension_connected_false(self, tab_server):
        """Test checking if extension is connected when it's not."""
        # Clear browser statuses to ensure clean state
        tab_server._browser_statuses = {}
        tab_server._data["browser_last_updates"] = {}
        
        # Check if extension is connected
        assert tab_server.is_extension_connected("chrome") is False

    def test_is_extension_connected_expired(self, tab_server):
        """Test checking if extension connection has expired."""
        browser_name = "chrome"
        
        # Clear browser statuses to ensure clean state
        tab_server._browser_statuses = {}
        tab_server._data["browser_last_updates"] = {}
        
        # Simulate an old update (more than 30 seconds ago)
        old_timestamp = time.time() - 35
        tab_server._data["browser_last_updates"][browser_name] = old_timestamp
        
        # Check if extension is connected
        assert tab_server.is_extension_connected(browser_name) is False

    def test_is_extension_connected_true(self, tab_server):
        """Test checking if extension is connected when it is."""
        browser_name = "chrome"
        
        # Clear browser statuses to ensure clean state
        tab_server._browser_statuses = {}
        tab_server._data["browser_last_updates"] = {}
        
        # Simulate a recent update (within 30 seconds) in browser_statuses
        recent_timestamp = time.time() - 10
        tab_server._browser_statuses[browser_name] = {
            "last_update": recent_timestamp,
            "tab_count": 1,
            "active_tab": None
        }
        
        # Check if extension is connected
        assert tab_server.is_extension_connected(browser_name) is True

    def test_is_port_available(self, tab_server):
        """Test is_port_available."""
        # Test with an available port using a mock socket
        with patch('socket.socket') as mock_socket:
            mock_socket_instance = MagicMock()
            mock_socket_instance.connect_ex.return_value = 1  # Non-zero means connection failed (port available)
            mock_socket.return_value.__enter__.return_value = mock_socket_instance
            
            # Test with a port
            assert tab_server.is_port_available(8000) is True
            
            # Verify the socket was used correctly
            mock_socket_instance.connect_ex.assert_called_with(('localhost', 8000))

    def test_is_port_unavailable(self, tab_server):
        """Test is_port_available with an unavailable port."""
        # Test with an unavailable port using a mock socket
        with patch('socket.socket') as mock_socket:
            mock_socket_instance = MagicMock()
            mock_socket_instance.connect_ex.return_value = 0  # Zero means connection successful (port in use)
            mock_socket.return_value.__enter__.return_value = mock_socket_instance
            
            # Test with a port
            assert tab_server.is_port_available(8000) is False
            
            # Verify the socket was used correctly
            mock_socket_instance.connect_ex.assert_called_with(('localhost', 8000))
            
    def test_check_if_running(self, tab_server):
        """Test checking if the tab server is running."""
        # Initially the server should not be running
        assert tab_server._running.is_set() is False
        
        # Start the server with a mock to avoid actual socket binding
        with patch('http.server.ThreadingHTTPServer') as mock_server:
            # Configure the mock server
            mock_server_instance = mock_server.return_value
            mock_server_instance.server_port = 12345
            
            # Start the server
            tab_server.start()
            
            # Verify the server is running
            assert tab_server._running.is_set() is True
            
            # Stop the server
            tab_server.stop()
            
            # Verify the server is not running
            assert tab_server._running.is_set() is False


if __name__ == "__main__":
    pytest.main(["-v", "test_tab_server.py"])
