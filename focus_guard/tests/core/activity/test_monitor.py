"""
Unit tests for the ActivityMonitor class.

This module contains unit tests for the ActivityMonitor class defined in
core.activity.monitor.
"""

import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from focus_guard.core.activity.monitor import ActivityMonitor
from focus_guard.core.activity.models import WindowInfo, ActivityEvent


class TestActivityMonitor(unittest.TestCase):
    """Tests for the ActivityMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = ActivityMonitor()
        
        # Mock platform implementation
        self.mock_platform_impl = MagicMock()
        self.monitor._platform_impl = self.mock_platform_impl
        
        # Mock browser monitor
        self.mock_browser_monitor = MagicMock()
        self.monitor._browser_monitor = self.mock_browser_monitor
    
    def test_platform_impl_property(self):
        """Test platform_impl property."""
        # Reset the monitor to test property initialization
        monitor = ActivityMonitor()
        monitor._platform_impl = None
        
        with patch("focus_guard.core.activity.platform.get_platform_implementation") as mock_get_platform:
            mock_impl = MagicMock()
            mock_get_platform.return_value = mock_impl
            
            # Access the property
            result = monitor.platform_impl
            
            # Verify the implementation was retrieved
            mock_get_platform.assert_called_once()
            self.assertEqual(result, mock_impl)
            
            # Verify the implementation is cached
            monitor.platform_impl
            mock_get_platform.assert_called_once()
    
    def test_browser_monitor_property(self):
        """Test browser_monitor property."""
        # Reset the monitor to test property initialization
        monitor = ActivityMonitor()
        monitor._browser_monitor = None
        
        with patch("focus_guard.core.activity.browser.tab_monitor.BrowserTabMonitor") as mock_browser_monitor_class:
            mock_browser_monitor = MagicMock()
            mock_browser_monitor_class.return_value = mock_browser_monitor
            
            # Access the property
            result = monitor.browser_monitor
            
            # Verify the browser monitor was created
            mock_browser_monitor_class.assert_called_once()
            self.assertEqual(result, mock_browser_monitor)
            
            # Verify the browser monitor is cached
            monitor.browser_monitor
            mock_browser_monitor_class.assert_called_once()
    
    def test_get_active_window_basic(self):
        """Test get_active_window with basic window info."""
        # Set up mock platform implementation
        window_data = {
            "app_name": "test_app",
            "window_title": "Test Window",
            "pid": "12345",
            "timestamp": "2025-07-26T11:30:00"
        }
        self.mock_platform_impl.get_active_window.return_value = window_data
        
        # Call the method
        result = self.monitor.get_active_window()
        
        # Verify the result
        self.assertIsInstance(result, WindowInfo)
        self.assertEqual(result.app_name, "test_app")
        self.assertEqual(result.window_title, "Test Window")
        self.assertEqual(result.pid, "12345")
        
        # Verify platform implementation was called
        self.mock_platform_impl.get_active_window.assert_called_once()
    
    def test_get_active_window_none(self):
        """Test get_active_window when no window is active."""
        # Set up mock platform implementation
        self.mock_platform_impl.get_active_window.return_value = None
        
        # Call the method
        result = self.monitor.get_active_window()
        
        # Verify the result
        self.assertIsNone(result)
        
        # Verify platform implementation was called
        self.mock_platform_impl.get_active_window.assert_called_once()
    
    def test_get_active_window_browser(self):
        """Test get_active_window with browser window."""
        # Set up mock platform implementation
        window_data = {
            "app_name": "chrome.exe",
            "window_title": "Test Page - Google Chrome",
            "pid": "12345",
            "timestamp": "2025-07-26T11:30:00"
        }
        self.mock_platform_impl.get_active_window.return_value = window_data
        
        # Set up mock browser monitor
        browser_data = {
            "url": "https://example.com/test",
            "title": "Test Page",
            "browser": "chrome",
            "tab_id": "tab123",
            "window_id": "win123"
        }
        self.mock_browser_monitor.get_active_tab.return_value = browser_data
        
        # Mock normalize_url and extract_domain_from_url (the actual functions used)
        with patch("focus_guard.core.activity.monitor.normalize_url") as mock_normalize, \
             patch("focus_guard.core.activity.monitor.extract_domain_from_url") as mock_extract_domain:
            mock_normalize.return_value = "https://example.com/test"
            mock_extract_domain.return_value = "example.com"
            
            # Call the method
            result = self.monitor.get_active_window()
            
            # Verify the result
            self.assertIsInstance(result, WindowInfo)
            self.assertEqual(result.app_name, "chrome.exe")
            self.assertEqual(result.window_title, "Test Page - Google Chrome")
            self.assertEqual(result.url, "https://example.com/test")
            self.assertEqual(result.domain, "example.com")
            
            # Verify mock calls
            self.mock_platform_impl.get_active_window.assert_called_once()
            self.mock_browser_monitor.get_active_tab.assert_called_once()
            mock_normalize.assert_called_once_with("https://example.com/test")
    
    def test_get_active_window_browser_fallback(self):
        """Test get_active_window with browser window when browser integration fails."""
        # Set up mock platform implementation
        window_data = {
            "app_name": "chrome.exe",
            "window_title": "https://example.com/test - Google Chrome",
            "pid": "12345",
            "timestamp": "2025-07-26T11:30:00"
        }
        self.mock_platform_impl.get_active_window.return_value = window_data
        
        # Set up mock browser monitor to raise exception
        self.mock_browser_monitor.get_active_tab.side_effect = Exception("Browser integration failed")
        
        # Mock URL extraction and the actual functions used in fallback path
        with patch.object(self.monitor, "_extract_url_from_title") as mock_extract_url, \
             patch("focus_guard.core.activity.monitor.normalize_url") as mock_normalize, \
             patch("focus_guard.core.activity.monitor.extract_domain_from_url") as mock_extract_domain:
            mock_extract_url.return_value = "https://example.com/test"
            mock_normalize.return_value = "https://example.com/test"
            mock_extract_domain.return_value = "example.com"
            
            # Call the method
            result = self.monitor.get_active_window()
            
            # Verify the result
            self.assertIsInstance(result, WindowInfo)
            self.assertEqual(result.app_name, "chrome.exe")
            self.assertEqual(result.window_title, "https://example.com/test - Google Chrome")
            self.assertEqual(result.url, "https://example.com/test")
            self.assertEqual(result.domain, "example.com")
            
            # Verify mock calls
            self.mock_platform_impl.get_active_window.assert_called_once()
            self.mock_browser_monitor.get_active_tab.assert_called_once()
            mock_extract_url.assert_called_once_with("https://example.com/test - Google Chrome")
            mock_normalize.assert_called_once_with("https://example.com/test")
    
    def test_get_top_windows(self):
        """Test get_top_windows."""
        # Set up mock platform implementation
        window_data_1 = {
            "app_name": "test_app_1",
            "window_title": "Test Window 1",
            "pid": "12345",
            "timestamp": "2025-07-26T11:30:00"
        }
        window_data_2 = {
            "app_name": "test_app_2",
            "window_title": "Test Window 2",
            "pid": "67890",
            "timestamp": "2025-07-26T11:30:00"
        }
        self.mock_platform_impl.get_top_windows.return_value = [window_data_1, window_data_2]
        
        # Call the method
        result = self.monitor.get_top_windows(top_region=300)
        
        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], WindowInfo)
        self.assertIsInstance(result[1], WindowInfo)
        self.assertEqual(result[0].app_name, "test_app_1")
        self.assertEqual(result[1].app_name, "test_app_2")
        
        # Verify platform implementation was called with correct parameters
        self.mock_platform_impl.get_top_windows.assert_called_once_with(300)
    
    def test_create_activity_event(self):
        """Test create_activity_event."""
        # Set up mock get_active_window
        mock_window_info = MagicMock(spec=WindowInfo)
        with patch.object(self.monitor, "get_active_window", return_value=mock_window_info):
            # Call the method
            result = self.monitor.create_activity_event("window_activated", {"duration": 60})
            
            # Verify the result
            self.assertIsInstance(result, ActivityEvent)
            self.assertEqual(result.event_type, "window_activated")
            self.assertEqual(result.window_info, mock_window_info)
            self.assertEqual(result.metadata, {"duration": 60})
    
    def test_is_browser(self):
        """Test _is_browser method."""
        # Test with browser names
        self.assertTrue(self.monitor._is_browser("chrome.exe"))
        self.assertTrue(self.monitor._is_browser("firefox.exe"))
        self.assertTrue(self.monitor._is_browser("msedge.exe"))
        self.assertTrue(self.monitor._is_browser("brave.exe"))
        
        # Test with non-browser names
        self.assertFalse(self.monitor._is_browser("notepad.exe"))
        self.assertFalse(self.monitor._is_browser("explorer.exe"))
    
    def test_extract_url_from_title(self):
        """Test _extract_url_from_title method."""
        # Test with URL in title
        url = self.monitor._extract_url_from_title("https://example.com/test - Google Chrome")
        self.assertEqual(url, "https://example.com/test")
        
        # Test with URL in middle of title
        url = self.monitor._extract_url_from_title("Test Page - https://example.com/test - Google Chrome")
        self.assertEqual(url, "https://example.com/test")
        
        # Test with no URL in title
        url = self.monitor._extract_url_from_title("Test Page - Google Chrome")
        self.assertIsNone(url)


if __name__ == "__main__":
    unittest.main()
