"""
Unit tests for the ExtensionInstaller class.

This module contains tests for the ExtensionInstaller class in core_v2.browser.extension.installer.
"""

import unittest
import time
import threading
from unittest.mock import patch, MagicMock, call
import pytest
import socket

from core_v2.browser.extension.installer import ExtensionInstaller
from core_v2.browser.models.browser import Browser, BrowserType
from core.browser_detection.browser_integration.tab_server_v2 import TabServer


class TestExtensionInstaller:
    """Test cases for the ExtensionInstaller class."""

    @pytest.fixture
    def extension_installer(self):
        """Create an ExtensionInstaller instance for testing."""
        installer = ExtensionInstaller()
        yield installer
        # Ensure tab server is stopped after test
        if installer._tab_server_thread and installer._tab_server_thread.is_alive():
            installer.stop_tab_server()

    @pytest.fixture
    def mock_browser_detector(self):
        """Create a mock BrowserDetector for testing."""
        mock_detector = MagicMock()
        mock_detector.get_active_browsers.return_value = [
            Browser(
                id="chrome-12345",
                type=BrowserType.CHROME,
                name="chrome",
                process_id=12345,
                window_id=1,
                window_title="Chrome Window",
                metadata={"is_active": True}
            ),
            Browser(
                id="firefox-67890",
                type=BrowserType.FIREFOX,
                name="firefox",
                process_id=67890,
                window_id=2,
                window_title="Firefox Window",
                metadata={"is_active": False}
            )
        ]
        return mock_detector

    @pytest.fixture
    def mock_extension_manager(self):
        """Create a mock ExtensionManager for testing."""
        mock_manager = MagicMock()
        mock_manager.install_extension.return_value = True
        mock_manager.is_extension_installed.return_value = True
        return mock_manager

    @pytest.fixture
    def mock_tab_server(self):
        """Create a mock TabServer for testing."""
        mock_server = MagicMock()
        mock_server.is_extension_connected.return_value = True
        mock_server.start.return_value = True
        mock_server.stop.return_value = True
        return mock_server

    def test_init(self, extension_installer):
        """Test ExtensionInstaller initialization."""
        # Verify the installer was initialized correctly
        assert extension_installer._tab_server is None
        assert extension_installer._tab_server_thread is None
        assert hasattr(extension_installer, '_extension_manager')

    @patch('core.browser_detection.browser_integration.tab_server_v2.is_running')
    def test_ensure_tab_server_running_already_running(self, mock_is_running, extension_installer):
        """Test ensure_tab_server_running when server is already running."""
        # Set up a mock tab server thread that is alive
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        extension_installer._tab_server_thread = mock_thread
        extension_installer._tab_server = MagicMock()
        
        # Mock the is_running function
        mock_is_running.return_value = True
        
        # Call the method
        result = extension_installer.ensure_tab_server_running()
        
        # Verify the result
        assert result is True
        
        # Verify a new server was not started
        assert extension_installer._tab_server_thread is mock_thread

    @patch('core_v2.browser.extension.installer.TabServer')
    @patch('core.browser_detection.browser_integration.tab_server_v2.is_running')
    def test_ensure_tab_server_running_start_success(self, mock_is_running, mock_tab_server_class, extension_installer):
        """Test ensure_tab_server_running when server needs to be started."""
        # Set up the mock tab server
        mock_server = MagicMock()
        mock_server.start.return_value = True
        mock_tab_server_class.return_value = mock_server
        
        # Mock is_running to return False first, then True after server starts
        mock_is_running.side_effect = [False, True]
        
        # Call the method
        result = extension_installer.ensure_tab_server_running()
        
        # Verify the result
        assert result is True
        
        # Verify the server was created and started
        mock_tab_server_class.assert_called_once()
        assert extension_installer._tab_server is mock_server
        assert extension_installer._tab_server_thread is not None

    @patch('core_v2.browser.extension.installer.TabServer')
    @patch('core.browser_detection.browser_integration.tab_server_v2.is_running')
    def test_ensure_tab_server_running_start_failure(self, mock_is_running, mock_tab_server_class, extension_installer):
        """Test ensure_tab_server_running when server fails to start."""
        # Set up the mock tab server
        mock_server = MagicMock()
        mock_server.is_running.return_value = False  # Server never starts
        mock_tab_server_class.return_value = mock_server
        
        # Mock is_running to always return False (server never starts)
        mock_is_running.return_value = False
        
        # Call the method
        result = extension_installer.ensure_tab_server_running()
        
        # Verify the result
        assert result is False
        
        # Verify the server was created but not started successfully
        mock_tab_server_class.assert_called_once()

    @patch('core_v2.browser.extension.installer.TabServer')
    @patch('core.browser_detection.browser_integration.tab_server_v2.is_running')
    def test_ensure_tab_server_running_port_conflict(self, mock_is_running, mock_tab_server_class, extension_installer):
        """Test ensure_tab_server_running when there is a port conflict."""
        # Set up the mock tab server
        mock_server = MagicMock()
        mock_server.is_running.return_value = True
        mock_tab_server_class.return_value = mock_server
        
        # Mock is_running to return True after server starts
        mock_is_running.return_value = True
        
        # Call the method
        result = extension_installer.ensure_tab_server_running(port=8000)
        
        # Verify the result
        assert result is True
        
        # Verify the server was created with the right port
        # Note: The implementation doesn't handle port conflicts by incrementing
        # It just uses the provided port
        mock_tab_server_class.assert_called_once_with(port=8000)
        
        # Verify the server was started
        assert extension_installer._tab_server_thread is not None

    @patch('core.browser_detection.browser_integration.tab_server_v2.is_running')
    def test_stop_tab_server_running(self, mock_is_running, extension_installer):
        """Test stop_tab_server when server is running."""
        # Set up a mock tab server and thread
        mock_server = MagicMock()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        
        # Mock is_running to return True (server is running)
        mock_is_running.return_value = True
        
        extension_installer._tab_server = mock_server
        extension_installer._tab_server_thread = mock_thread
        
        # Call the method
        result = extension_installer.stop_tab_server()
        
        # Verify the result
        assert result is True
        
        # Verify the server was stopped
        mock_server.stop.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=5.0)
        
        # Verify the server and thread were cleared
        assert extension_installer._tab_server is None
        assert extension_installer._tab_server_thread is None

    def test_stop_tab_server_not_running(self, extension_installer):
        """Test stop_tab_server when server is not running."""
        # Set up the installer with no tab server
        extension_installer._tab_server = None
        extension_installer._tab_server_thread = None
        
        # Call the method
        result = extension_installer.stop_tab_server()
        
        # Verify the result
        assert result is True

    @patch('core_v2.browser.extension.installer.TabServer')
    def test_install_extension_success(self, mock_tab_server_class, extension_installer, mock_extension_manager):
        """Test install_extension with successful installation."""
        # Set up the installer with a mock extension manager
        extension_installer._extension_manager = mock_extension_manager
        mock_extension_manager.install_extension.return_value = True
        
        # Set up a mock tab server that is running
        mock_server = MagicMock()
        mock_server.is_running.return_value = True
        mock_tab_server_class.return_value = mock_server
        extension_installer._tab_server = mock_server
        
        # Call the method
        result = extension_installer.install_extension(BrowserType.CHROME)
        
        # Verify the result
        assert result is True
        
        # Verify the extension manager was called
        mock_extension_manager.install_extension.assert_called_once_with(BrowserType.CHROME)

    @patch('core_v2.browser.extension.installer.TabServer')
    def test_install_extension_failure(self, mock_tab_server_class, extension_installer, mock_extension_manager):
        """Test install_extension with failed installation."""
        # Set up the installer with a mock extension manager that fails
        mock_extension_manager.install_extension.return_value = False
        extension_installer._extension_manager = mock_extension_manager
        
        # Set up a mock tab server that is running
        mock_server = MagicMock()
        mock_server.is_running.return_value = True
        mock_tab_server_class.return_value = mock_server
        extension_installer._tab_server = mock_server
        
        # Call the method
        result = extension_installer.install_extension(BrowserType.CHROME)
        
        # Verify the result
        assert result is False
        
        # Verify the extension manager was called
        mock_extension_manager.install_extension.assert_called_once_with(BrowserType.CHROME)

    @patch('time.sleep')
    def test_verify_installation_connected(self, mock_sleep, extension_installer, mock_tab_server):
        """Test verify_installation when extension is connected."""
        # Set up the installer with a mock tab server
        extension_installer._tab_server = mock_tab_server
        
        # Mock extension manager to report extension as installed
        extension_installer._extension_manager = MagicMock()
        extension_installer._extension_manager.is_extension_installed.return_value = True
        
        # Mock the tab server's get_status method to return connected status
        mock_tab_server.get_status.return_value = {
            "extension_connected": True,
            "browser_statuses": {
                "chrome": {"connected": True}
            }
        }
        
        # Call the method
        result = extension_installer.verify_installation(BrowserType.CHROME)
        
        # Verify the result
        assert result is True
        
        # Verify the tab server's get_status was called
        assert mock_tab_server.get_status.called
        
        # Verify sleep was not called (connection was immediate)
        mock_sleep.assert_not_called()

    @patch('time.sleep')
    def test_verify_installation_delayed_connection(self, mock_sleep, extension_installer, mock_tab_server):
        """Test verify_installation when extension connects after a delay."""
        # Set up the installer with a mock tab server
        extension_installer._tab_server = mock_tab_server
        
        # Mock extension manager to report extension as installed
        extension_installer._extension_manager = MagicMock()
        extension_installer._extension_manager.is_extension_installed.return_value = True
        
        # Mock the tab server's get_status method to initially return not connected, then connected after delay
        mock_tab_server.get_status.side_effect = [
            # First two calls - not connected
            {"extension_connected": False, "browser_statuses": {}},
            {"extension_connected": False, "browser_statuses": {}},
            # Third call - connected
            {
                "extension_connected": True,
                "browser_statuses": {
                    "chrome": {"connected": True}
                }
            }
        ]
        
        # Call the method
        result = extension_installer.verify_installation(BrowserType.CHROME)
        
        # Verify the result
        assert result is True
        
        # Verify the tab server's get_status was called multiple times
        assert mock_tab_server.get_status.call_count == 3
        
        # Verify sleep was called for each retry
        assert mock_sleep.call_count == 2

    @patch('time.sleep')
    def test_verify_installation_never_connects(self, mock_sleep, extension_installer, mock_tab_server):
        """Test verify_installation when extension never connects."""
        # Set up the installer with a mock tab server
        extension_installer._tab_server = mock_tab_server
        
        # Mock extension manager to report extension as installed
        extension_installer._extension_manager = MagicMock()
        extension_installer._extension_manager.is_extension_installed.return_value = True
        
        # Mock the tab server's get_status method to always return not connected
        # Create a side effect that returns the same disconnected status multiple times
        disconnected_status = {"extension_connected": False, "browser_statuses": {}}
        mock_tab_server.get_status.return_value = disconnected_status
        
        # Call the method with a short timeout
        result = extension_installer.verify_installation(BrowserType.CHROME, timeout=1)
        
        # Verify the result
        assert result is False
        
        # Verify the tab server's get_status was called at least once
        assert mock_tab_server.get_status.call_count >= 1
        
        # Verify sleep was called at least once for retries
        assert mock_sleep.call_count >= 1

    def test_verify_installation_no_server(self, extension_installer):
        """Test verify_installation when tab server is not running."""
        # Set up the installer with no tab server
        extension_installer._tab_server = None
        
        # Call the method
        result = extension_installer.verify_installation(BrowserType.CHROME)
        
        # Verify the result
        assert result is False

    def test_install_for_detected_browsers(self, extension_installer, mock_browser_detector, mock_extension_manager):
        """Test install_for_detected_browsers with successful installations."""
        # Set up the installer with mock components
        extension_installer._browser_detector = mock_browser_detector
        extension_installer._extension_manager = mock_extension_manager
        
        # Set up browser paths in extension manager
        mock_extension_manager._browser_paths = {
            BrowserType.CHROME: "path/to/chrome",
            BrowserType.FIREFOX: "path/to/firefox"
        }
        
        # Make the extension manager's install_extension method return True
        mock_extension_manager.install_extension.return_value = True
        
        # Mock the ensure_tab_server_running and verify_installation methods
        with patch.object(ExtensionInstaller, 'ensure_tab_server_running', return_value=True), \
             patch.object(ExtensionInstaller, 'verify_installation', return_value=True):
            # Call the method
            results = extension_installer.install_for_detected_browsers()
            
            # Verify the results
            assert results == {BrowserType.CHROME: True, BrowserType.FIREFOX: True}
            
            # Verify the extension manager was called for each browser
            assert mock_extension_manager.install_extension.call_count == 2
            mock_extension_manager.install_extension.assert_any_call(BrowserType.CHROME)
            mock_extension_manager.install_extension.assert_any_call(BrowserType.FIREFOX)

    def test_install_for_detected_browsers_no_browsers(self, extension_installer, mock_browser_detector):
        """Test install_for_detected_browsers when no browsers are detected."""
        # Set up the installer with a mock browser detector that returns no browsers
        mock_browser_detector.get_active_browsers.return_value = []
        extension_installer._browser_detector = mock_browser_detector
        
        # Call the method
        results = extension_installer.install_for_detected_browsers()
        
        # Verify the results
        assert results == {}

    def test_install_for_detected_browsers_tab_server_failure(self, extension_installer, mock_browser_detector):
        """Test install_for_detected_browsers when tab server fails to start."""
        # Set up the installer with a mock browser detector
        extension_installer._browser_detector = mock_browser_detector
        
        # Mock the ensure_tab_server_running method to return False
        with patch.object(ExtensionInstaller, 'ensure_tab_server_running', return_value=False):
            # Call the method
            results = extension_installer.install_for_detected_browsers()
            
            # Verify the results - should be empty dict when tab server fails
            assert results == {}

    def test_install_for_detected_browsers_mixed_results(self, extension_installer, mock_browser_detector, mock_extension_manager):
        """Test install_for_detected_browsers with mixed installation results."""
        # Set up the installer with mock components
        extension_installer._browser_detector = mock_browser_detector
        extension_installer._extension_manager = mock_extension_manager
        
        # Set up browser paths in extension manager
        mock_extension_manager._browser_paths = {
            BrowserType.CHROME: "path/to/chrome",
            BrowserType.FIREFOX: "path/to/firefox"
        }
        
        # Mock the ensure_tab_server_running method
        with patch.object(ExtensionInstaller, 'ensure_tab_server_running', return_value=True), \
             patch.object(ExtensionInstaller, 'install_extension', side_effect=lambda browser_type: browser_type == BrowserType.CHROME):
            # Call the method
            results = extension_installer.install_for_detected_browsers()
            
            # Verify the results
            assert results == {BrowserType.CHROME: True, BrowserType.FIREFOX: False}


if __name__ == "__main__":
    pytest.main(["-v", "test_extension_installer.py"])
