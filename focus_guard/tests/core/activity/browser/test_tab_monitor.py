"""
DEPRECATED: These tests target the old BrowserTabMonitor wrapper which delegates to
BrowserExtensionIntegration. The underlying BrowserExtensionIntegration was rewritten
to use the browser_v2 tab server HTTP API. The thin wrapper tests here mock constructor
patterns and functions (create_url_from_string) that no longer exist.

See browser_v2 tests for current coverage:
  - focus_guard/tests/browser_v2/integration/test_tab_server.py
  - focus_guard/tests/browser_v2/unit/test_api_models.py
"""

import pytest
pytestmark = pytest.mark.skip(reason="DEPRECATED: tests target old browser API replaced by browser_v2 tab server")

import unittest
from unittest.mock import patch, MagicMock

from focus_guard.core.activity.browser.tab_monitor import BrowserTabMonitor


class TestBrowserTabMonitor(unittest.TestCase):
    """Tests for the BrowserTabMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the BrowserExtensionIntegration
        self.mock_extension_integration = MagicMock()
        
        # Create BrowserTabMonitor with mock extension integration
        with patch("focus_guard.core.activity.browser.tab_monitor.BrowserExtensionIntegration", 
                  return_value=self.mock_extension_integration):
            self.tab_monitor = BrowserTabMonitor()
    
    def test_extension_integration_property(self):
        """Test extension_integration property."""
        # Reset the tab monitor to test property initialization
        tab_monitor = BrowserTabMonitor()
        tab_monitor._extension_integration = None
        
        with patch("focus_guard.core.activity.browser.tab_monitor.BrowserExtensionIntegration") as mock_extension_class:
            mock_extension = MagicMock()
            mock_extension_class.return_value = mock_extension
            
            # Access the property
            result = tab_monitor.extension_integration
            
            # Verify the extension integration was created
            mock_extension_class.assert_called_once()
            self.assertEqual(result, mock_extension)
            
            # Verify the extension integration is cached
            tab_monitor.extension_integration
            mock_extension_class.assert_called_once()
    
    def test_get_active_tab(self):
        """Test get_active_tab."""
        # Set up mock extension integration
        tab_data = {
            "url": "https://example.com/test",
            "title": "Test Page",
            "browser": "chrome",
            "tab_id": "tab123",
            "window_id": "win123"
        }
        self.mock_extension_integration.get_active_tab.return_value = tab_data
        
        # Call the method
        result = self.tab_monitor.get_active_tab()
        
        # Verify the result
        self.assertEqual(result, tab_data)
        
        # Verify extension integration was called
        self.mock_extension_integration.get_active_tab.assert_called_once()
    
    def test_get_active_tab_none(self):
        """Test get_active_tab when no tab is active."""
        # Set up mock extension integration
        self.mock_extension_integration.get_active_tab.return_value = None
        
        # Call the method
        result = self.tab_monitor.get_active_tab()
        
        # Verify the result
        self.assertIsNone(result)
        
        # Verify extension integration was called
        self.mock_extension_integration.get_active_tab.assert_called_once()
    
    def test_get_all_tabs(self):
        """Test get_all_tabs."""
        # Set up mock extension integration
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
        self.mock_extension_integration.get_all_tabs.return_value = tabs_data
        
        # Call the method
        result = self.tab_monitor.get_all_tabs()
        
        # Verify the result
        self.assertEqual(result, tabs_data)
        
        # Verify extension integration was called
        self.mock_extension_integration.get_all_tabs.assert_called_once()
    
    def test_get_tabs_by_browser(self):
        """Test get_tabs_by_browser."""
        # Set up mock extension integration
        tabs_data = [
            {
                "url": "https://example.com/test1",
                "title": "Test Page 1",
                "browser": "chrome",
                "tab_id": "tab123",
                "window_id": "win123"
            }
        ]
        self.mock_extension_integration.get_all_tabs.return_value = tabs_data
        
        # Call the method
        result = self.tab_monitor.get_tabs_by_browser("chrome")
        
        # Verify the result
        self.assertEqual(result, tabs_data)
        
        # Verify extension integration was called
        self.mock_extension_integration.get_all_tabs.assert_called_once()
    
    def test_get_tabs_by_browser_no_match(self):
        """Test get_tabs_by_browser with no matching browser."""
        # Set up mock extension integration
        tabs_data = [
            {
                "url": "https://example.com/test1",
                "title": "Test Page 1",
                "browser": "chrome",
                "tab_id": "tab123",
                "window_id": "win123"
            }
        ]
        self.mock_extension_integration.get_all_tabs.return_value = tabs_data
        
        # Call the method
        result = self.tab_monitor.get_tabs_by_browser("firefox")
        
        # Verify the result
        self.assertEqual(result, [])
        
        # Verify extension integration was called
        self.mock_extension_integration.get_all_tabs.assert_called_once()
    
    def test_get_tabs_by_domain(self):
        """Test get_tabs_by_domain."""
        # Set up mock extension integration
        tabs_data = [
            {
                "url": "https://example.com/test1",
                "title": "Test Page 1",
                "browser": "chrome",
                "tab_id": "tab123",
                "window_id": "win123",
                "domain": "example.com"
            },
            {
                "url": "https://other.com/test2",
                "title": "Test Page 2",
                "browser": "chrome",
                "tab_id": "tab456",
                "window_id": "win123",
                "domain": "other.com"
            }
        ]
        self.mock_extension_integration.get_all_tabs.return_value = tabs_data
        
        # Call the method
        result = self.tab_monitor.get_tabs_by_domain("example.com")
        
        # Verify the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["url"], "https://example.com/test1")
        
        # Verify extension integration was called
        self.mock_extension_integration.get_all_tabs.assert_called_once()
    
    def test_get_tabs_by_domain_no_domain_field(self):
        """Test get_tabs_by_domain when tabs don't have domain field."""
        # Set up mock extension integration
        tabs_data = [
            {
                "url": "https://example.com/test1",
                "title": "Test Page 1",
                "browser": "chrome",
                "tab_id": "tab123",
                "window_id": "win123"
            },
            {
                "url": "https://other.com/test2",
                "title": "Test Page 2",
                "browser": "chrome",
                "tab_id": "tab456",
                "window_id": "win123"
            }
        ]
        self.mock_extension_integration.get_all_tabs.return_value = tabs_data
        
        # Mock URL creation
        with patch("focus_guard.core.activity.browser.tab_monitor.create_url_from_string") as mock_create_url:
            mock_url_1 = MagicMock()
            mock_domain_1 = MagicMock()
            mock_domain_1.__str__.return_value = "example.com"
            mock_url_1.domain = mock_domain_1
            
            mock_url_2 = MagicMock()
            mock_domain_2 = MagicMock()
            mock_domain_2.__str__.return_value = "other.com"
            mock_url_2.domain = mock_domain_2
            
            mock_create_url.side_effect = [mock_url_1, mock_url_2]
            
            # Call the method
            result = self.tab_monitor.get_tabs_by_domain("example.com")
            
            # Verify the result
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["url"], "https://example.com/test1")
            
            # Verify mock calls
            self.mock_extension_integration.get_all_tabs.assert_called_once()
            mock_create_url.assert_any_call("https://example.com/test1")
            mock_create_url.assert_any_call("https://other.com/test2")


if __name__ == "__main__":
    unittest.main()
