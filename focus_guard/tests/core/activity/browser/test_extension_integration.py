"""
Unit tests for the BrowserExtensionIntegration class.

This module contains unit tests for the BrowserExtensionIntegration class defined in
core.activity.browser.extension_integration.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import time

from focus_guard.core.activity.browser.extension_integration import BrowserExtensionIntegration


class TestBrowserExtensionIntegration(unittest.TestCase):
    """Tests for the BrowserExtensionIntegration class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the BrowserIntegration
        self.mock_browser_integration = MagicMock()
        
        # Create BrowserExtensionIntegration with mock browser integration
        with patch("core.activity.browser.extension_integration.BrowserIntegration", 
                  return_value=self.mock_browser_integration):
            self.extension_integration = BrowserExtensionIntegration()
    
    def test_browser_integration_property(self):
        """Test browser_integration property."""
        # Reset the extension integration to test property initialization
        extension_integration = BrowserExtensionIntegration()
        extension_integration._browser_integration = None
        
        with patch("core.activity.browser.extension_integration.BrowserIntegration") as mock_browser_class:
            mock_browser = MagicMock()
            mock_browser_class.return_value = mock_browser
            
            # Access the property
            result = extension_integration.browser_integration
            
            # Verify the browser integration was created
            mock_browser_class.assert_called_once()
            self.assertEqual(result, mock_browser)
            
            # Verify the browser integration is cached
            extension_integration.browser_integration
            mock_browser_class.assert_called_once()
    
    def test_get_active_tab_from_cache(self):
        """Test get_active_tab when tab data is in cache."""
        # Set up cache
        tab_data = {
            "url": "https://example.com/test",
            "title": "Test Page",
            "browser": "chrome",
            "tab_id": "tab123",
            "window_id": "win123"
        }
        self.extension_integration._tab_cache = {"active_tab": tab_data}
        self.extension_integration._cache_timestamp = time.time()
        
        # Call the method
        result = self.extension_integration.get_active_tab()
        
        # Verify the result
        self.assertEqual(result, tab_data)
        
        # Verify browser integration was not called
        self.mock_browser_integration.get_active_tab.assert_not_called()
    
    def test_get_active_tab_cache_expired(self):
        """Test get_active_tab when cache is expired."""
        # Set up expired cache
        tab_data_old = {
            "url": "https://example.com/old",
            "title": "Old Page",
            "browser": "chrome",
            "tab_id": "tab123",
            "window_id": "win123"
        }
        tab_data_new = {
            "url": "https://example.com/new",
            "title": "New Page",
            "browser": "chrome",
            "tab_id": "tab456",
            "window_id": "win456"
        }
        self.extension_integration._tab_cache = {"active_tab": tab_data_old}
        self.extension_integration._cache_timestamp = time.time() - 60  # 60 seconds ago
        self.extension_integration._cache_ttl = 30  # 30 seconds TTL
        
        # Set up mock browser integration
        self.mock_browser_integration.get_active_tab.return_value = tab_data_new
        
        # Call the method
        result = self.extension_integration.get_active_tab()
        
        # Verify the result
        self.assertEqual(result, tab_data_new)
        
        # Verify browser integration was called
        self.mock_browser_integration.get_active_tab.assert_called_once()
        
        # Verify cache was updated
        self.assertEqual(self.extension_integration._tab_cache["active_tab"], tab_data_new)
    
    def test_get_active_tab_no_cache(self):
        """Test get_active_tab when no cache exists."""
        # Set up empty cache
        self.extension_integration._tab_cache = {}
        
        # Set up mock browser integration
        tab_data = {
            "url": "https://example.com/test",
            "title": "Test Page",
            "browser": "chrome",
            "tab_id": "tab123",
            "window_id": "win123"
        }
        self.mock_browser_integration.get_active_tab.return_value = tab_data
        
        # Call the method
        result = self.extension_integration.get_active_tab()
        
        # Verify the result
        self.assertEqual(result, tab_data)
        
        # Verify browser integration was called
        self.mock_browser_integration.get_active_tab.assert_called_once()
        
        # Verify cache was updated
        self.assertEqual(self.extension_integration._tab_cache["active_tab"], tab_data)
    
    def test_get_active_tab_browser_integration_error(self):
        """Test get_active_tab when browser integration raises an error."""
        # Set up empty cache
        self.extension_integration._tab_cache = {}
        
        # Set up mock browser integration to raise exception
        self.mock_browser_integration.get_active_tab.side_effect = Exception("Browser integration failed")
        
        # Set up mock fallback
        with patch.object(self.extension_integration, "_fallback_get_active_tab") as mock_fallback:
            fallback_data = {
                "url": "https://example.com/fallback",
                "title": "Fallback Page"
            }
            mock_fallback.return_value = fallback_data
            
            # Call the method
            result = self.extension_integration.get_active_tab()
            
            # Verify the result
            self.assertEqual(result, fallback_data)
            
            # Verify mock calls
            self.mock_browser_integration.get_active_tab.assert_called_once()
            mock_fallback.assert_called_once()
    
    def test_get_all_tabs_from_cache(self):
        """Test get_all_tabs when tab data is in cache."""
        # Set up cache
        tabs_data = [
            {
                "url": "https://example.com/test1",
                "title": "Test Page 1",
                "browser": "chrome",
                "tab_id": "tab123",
                "window_id": "win123"
            },
            {
                "url": "https://example.com/test2",
                "title": "Test Page 2",
                "browser": "chrome",
                "tab_id": "tab456",
                "window_id": "win123"
            }
        ]
        self.extension_integration._tab_cache = {"all_tabs": tabs_data}
        self.extension_integration._cache_timestamp = time.time()
        
        # Call the method
        result = self.extension_integration.get_all_tabs()
        
        # Verify the result
        self.assertEqual(result, tabs_data)
        
        # Verify browser integration was not called
        self.mock_browser_integration.get_all_tabs.assert_not_called()
    
    def test_get_all_tabs_no_cache(self):
        """Test get_all_tabs when no cache exists."""
        # Set up empty cache
        self.extension_integration._tab_cache = {}
        
        # Set up mock browser integration
        tabs_data = [
            {
                "url": "https://example.com/test1",
                "title": "Test Page 1",
                "browser": "chrome",
                "tab_id": "tab123",
                "window_id": "win123"
            },
            {
                "url": "https://example.com/test2",
                "title": "Test Page 2",
                "browser": "chrome",
                "tab_id": "tab456",
                "window_id": "win123"
            }
        ]
        self.mock_browser_integration.get_all_tabs.return_value = tabs_data
        
        # Call the method
        result = self.extension_integration.get_all_tabs()
        
        # Verify the result
        self.assertEqual(result, tabs_data)
        
        # Verify browser integration was called
        self.mock_browser_integration.get_all_tabs.assert_called_once()
        
        # Verify cache was updated
        self.assertEqual(self.extension_integration._tab_cache["all_tabs"], tabs_data)
    
    def test_get_all_tabs_browser_integration_error(self):
        """Test get_all_tabs when browser integration raises an error."""
        # Set up empty cache
        self.extension_integration._tab_cache = {}
        
        # Set up mock browser integration to raise exception
        self.mock_browser_integration.get_all_tabs.side_effect = Exception("Browser integration failed")
        
        # Set up mock fallback
        with patch.object(self.extension_integration, "_fallback_get_all_tabs") as mock_fallback:
            fallback_data = [{"url": "https://example.com/fallback"}]
            mock_fallback.return_value = fallback_data
            
            # Call the method
            result = self.extension_integration.get_all_tabs()
            
            # Verify the result
            self.assertEqual(result, fallback_data)
            
            # Verify mock calls
            self.mock_browser_integration.get_all_tabs.assert_called_once()
            mock_fallback.assert_called_once()
    
    def test_fallback_get_active_tab(self):
        """Test _fallback_get_active_tab."""
        # Mock the platform-specific active window detection
        with patch("core.activity.platform.get_platform_implementation") as mock_get_platform:
            mock_platform = MagicMock()
            mock_get_platform.return_value = mock_platform
            
            window_data = {
                "app_name": "chrome.exe",
                "window_title": "Test Page - Google Chrome",
                "pid": "12345"
            }
            mock_platform.get_active_window.return_value = window_data
            
            # Call the method
            result = self.extension_integration._fallback_get_active_tab()
            
            # Verify the result
            self.assertEqual(result["title"], "Test Page")
            self.assertEqual(result["browser"], "chrome")
            
            # Verify platform implementation was called
            mock_get_platform.assert_called_once()
            mock_platform.get_active_window.assert_called_once()
    
    def test_fallback_get_active_tab_no_browser(self):
        """Test _fallback_get_active_tab when active window is not a browser."""
        # Mock the platform-specific active window detection
        with patch("core.activity.platform.get_platform_implementation") as mock_get_platform:
            mock_platform = MagicMock()
            mock_get_platform.return_value = mock_platform
            
            window_data = {
                "app_name": "notepad.exe",
                "window_title": "Document - Notepad",
                "pid": "12345"
            }
            mock_platform.get_active_window.return_value = window_data
            
            # Call the method
            result = self.extension_integration._fallback_get_active_tab()
            
            # Verify the result is None
            self.assertIsNone(result)
            
            # Verify platform implementation was called
            mock_get_platform.assert_called_once()
            mock_platform.get_active_window.assert_called_once()
    
    def test_close_tab(self):
        """Test close_tab."""
        # Call the method
        self.extension_integration.close_tab("tab123", "win123", "https://example.com", "Test reason")
        
        # Verify browser integration was called with correct parameters
        self.mock_browser_integration.close_tab.assert_called_once_with(
            "tab123", "win123", "https://example.com", "Test reason"
        )
    
    def test_close_tab_error(self):
        """Test close_tab when browser integration raises an error."""
        # Set up mock browser integration to raise exception
        self.mock_browser_integration.close_tab.side_effect = Exception("Browser integration failed")
        
        # Call the method and verify it doesn't raise an exception
        try:
            self.extension_integration.close_tab("tab123", "win123", "https://example.com", "Test reason")
        except Exception:
            self.fail("close_tab raised an exception unexpectedly")
        
        # Verify browser integration was called
        self.mock_browser_integration.close_tab.assert_called_once()


if __name__ == "__main__":
    unittest.main()
