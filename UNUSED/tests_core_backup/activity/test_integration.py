"""
Integration tests for the activity monitor components.

This module contains integration tests for the ActivityMonitor class and its
interactions with platform-specific implementations and browser integration.
"""

import unittest
from unittest.mock import patch, MagicMock

from core_v2.activity.monitor import ActivityMonitor
from core_v2.activity.models import WindowInfo, ActivityEvent


class TestActivityMonitorIntegration(unittest.TestCase):
    """Integration tests for the ActivityMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create real ActivityMonitor
        self.monitor = ActivityMonitor()
    
    @patch("core_v2.activity.platform.get_platform_implementation")
    @patch("core_v2.activity.browser.tab_monitor.BrowserTabMonitor")
    def test_activity_monitor_with_platform_and_browser(self, mock_browser_monitor_class, mock_get_platform):
        """Test ActivityMonitor integration with platform and browser components."""
        # Set up mock platform implementation
        mock_platform = MagicMock()
        window_data = {
            "app_name": "chrome.exe",
            "window_title": "Test Page - Google Chrome",
            "pid": "12345",
            "hwnd": 67890,
            "rect": (0, 0, 100, 100),
            "area": 10000
        }
        mock_platform.get_active_window.return_value = window_data
        mock_get_platform.return_value = mock_platform
        
        # Set up mock browser monitor
        mock_browser_monitor = MagicMock()
        browser_data = {
            "url": "https://example.com/test",
            "title": "Test Page",
            "browser": "chrome",
            "tab_id": "tab123",
            "window_id": "win123"
        }
        mock_browser_monitor.get_active_tab.return_value = browser_data
        mock_browser_monitor_class.return_value = mock_browser_monitor
        
        # Create monitor with mocked dependencies
        monitor = ActivityMonitor()
        
        # Call the method to get active window
        result = monitor.get_active_window()
        
        # Verify the result
        self.assertIsInstance(result, WindowInfo)
        self.assertEqual(result.app_name, "chrome.exe")
        self.assertEqual(result.window_title, "Test Page - Google Chrome")
        self.assertEqual(result.pid, "12345")
        self.assertEqual(result.hwnd, 67890)
        self.assertEqual(result.rect, (0, 0, 100, 100))
        self.assertEqual(result.area, 10000)
        
        # Verify URL was set from browser data
        self.assertIsNotNone(result.url)
        self.assertIsNotNone(result.domain)
        
        # Verify mock calls
        mock_get_platform.assert_called_once()
        mock_platform.get_active_window.assert_called_once()
        mock_browser_monitor_class.assert_called_once()
        mock_browser_monitor.get_active_tab.assert_called_once()
    
    @patch("core_v2.activity.platform.get_platform_implementation")
    @patch("core_v2.activity.browser.tab_monitor.BrowserTabMonitor")
    def test_create_activity_event_integration(self, mock_browser_monitor_class, mock_get_platform):
        """Test ActivityMonitor.create_activity_event integration."""
        # Set up mock platform implementation
        mock_platform = MagicMock()
        window_data = {
            "app_name": "notepad.exe",
            "window_title": "Document - Notepad",
            "pid": "12345"
        }
        mock_platform.get_active_window.return_value = window_data
        mock_get_platform.return_value = mock_platform
        
        # Set up mock browser monitor (not used for non-browser app)
        mock_browser_monitor = MagicMock()
        mock_browser_monitor_class.return_value = mock_browser_monitor
        
        # Create monitor with mocked dependencies
        monitor = ActivityMonitor()
        
        # Call the method to create activity event
        result = monitor.create_activity_event("window_activated", {"duration": 60})
        
        # Verify the result
        self.assertIsInstance(result, ActivityEvent)
        self.assertEqual(result.event_type, "window_activated")
        self.assertEqual(result.metadata, {"duration": 60})
        
        # Verify window info
        self.assertIsInstance(result.window_info, WindowInfo)
        self.assertEqual(result.window_info.app_name, "notepad.exe")
        self.assertEqual(result.window_info.window_title, "Document - Notepad")
        self.assertEqual(result.window_info.pid, "12345")
        
        # Verify mock calls
        mock_get_platform.assert_called_once()
        mock_platform.get_active_window.assert_called_once()
        mock_browser_monitor.get_active_tab.assert_not_called()
    
    @patch("core_v2.activity.platform.get_platform_implementation")
    @patch("core_v2.activity.browser.tab_monitor.BrowserTabMonitor")
    def test_get_top_windows_integration(self, mock_browser_monitor_class, mock_get_platform):
        """Test ActivityMonitor.get_top_windows integration."""
        # Set up mock platform implementation
        mock_platform = MagicMock()
        windows_data = [
            {
                "app_name": "chrome.exe",
                "window_title": "Test Page - Google Chrome",
                "pid": "12345",
                "area": 10000,
                "percent": 0.5
            },
            {
                "app_name": "notepad.exe",
                "window_title": "Document - Notepad",
                "pid": "67890",
                "area": 5000,
                "percent": 0.25
            }
        ]
        mock_platform.get_top_windows.return_value = windows_data
        mock_get_platform.return_value = mock_platform
        
        # Set up mock browser monitor (not used for get_top_windows)
        mock_browser_monitor = MagicMock()
        mock_browser_monitor_class.return_value = mock_browser_monitor
        
        # Create monitor with mocked dependencies
        monitor = ActivityMonitor()
        
        # Call the method to get top windows
        result = monitor.get_top_windows(top_region=300)
        
        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], WindowInfo)
        self.assertIsInstance(result[1], WindowInfo)
        self.assertEqual(result[0].app_name, "chrome.exe")
        self.assertEqual(result[0].window_title, "Test Page - Google Chrome")
        self.assertEqual(result[0].area, 10000)
        self.assertEqual(result[0].percent, 0.5)
        self.assertEqual(result[1].app_name, "notepad.exe")
        self.assertEqual(result[1].window_title, "Document - Notepad")
        
        # Verify mock calls
        mock_get_platform.assert_called_once()
        mock_platform.get_top_windows.assert_called_once_with(300)


class TestBrowserIntegrationWithActivityMonitor(unittest.TestCase):
    """Integration tests for browser integration with ActivityMonitor."""
    
    @patch("core_v2.activity.platform.get_platform_implementation")
    @patch("core_v2.activity.browser.extension_integration.BrowserIntegration")
    def test_browser_integration_fallback(self, mock_browser_integration_class, mock_get_platform):
        """Test fallback to window title parsing when browser integration fails."""
        # Set up mock platform implementation
        mock_platform = MagicMock()
        window_data = {
            "app_name": "chrome.exe",
            "window_title": "https://example.com/test - Google Chrome",
            "pid": "12345"
        }
        mock_platform.get_active_window.return_value = window_data
        mock_get_platform.return_value = mock_platform
        
        # Set up mock browser integration to fail
        mock_browser_integration = MagicMock()
        mock_browser_integration.get_active_tab.side_effect = Exception("Browser integration failed")
        mock_browser_integration_class.return_value = mock_browser_integration
        
        # Create monitor
        monitor = ActivityMonitor()
        
        # Call the method to get active window
        result = monitor.get_active_window()
        
        # Verify the result
        self.assertIsInstance(result, WindowInfo)
        self.assertEqual(result.app_name, "chrome.exe")
        self.assertEqual(result.window_title, "https://example.com/test - Google Chrome")
        
        # Verify URL was extracted from window title
        self.assertIsNotNone(result.url)
        self.assertIsNotNone(result.domain)
        
        # Convert URL to string for easier assertion
        url_str = str(result.url)
        self.assertEqual(url_str, "https://example.com/test")


if __name__ == "__main__":
    unittest.main()
