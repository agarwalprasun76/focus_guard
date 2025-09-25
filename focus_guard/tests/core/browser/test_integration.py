"""
Integration tests for browser detection and tab tracking.

This module contains tests that verify the integration of browser detection,
tab tracking, and tab blocking components.
"""

import unittest
import time
from unittest.mock import MagicMock, patch

from focus_guard.core.browser.adapter import BrowserDetector, TabTracker, TabBlocker
from focus_guard.core.browser.models.browser import Browser, BrowserType
from focus_guard.core.browser.models.tab import Tab
from focus_guard.core.browser.integration.tab_tracker import BrowserTabTracker
from focus_guard.core.browser.integration.tab_blocker import BrowserTabBlocker
from focus_guard.core.browser.extension.manager import BrowserExtensionManager
from focus_guard.core.browser.usage.tracker import BrowserUsageTracker


class TestBrowserIntegration(unittest.TestCase):
    """Test case for browser integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.browser_detector = BrowserDetector()
        self.tab_tracker = TabTracker()
        self.tab_blocker = TabBlocker()
        
        # Create test browser
        self.test_browser = Browser(
            id="test-browser-1",
            type=BrowserType.CHROME,
            name="Chrome",
            process_id=12345,
            window_id=1,
            window_title="Test Browser",
            metadata={"is_active": True}
        )
        
        # Create test tabs
        self.test_tabs = [
            Tab(
                id=1,
                window_id=1,
                url="https://example.com",
                title="Example Domain",
                browser_id="test-browser-1",
                domain="example.com",
                is_active=True
            ),
            Tab(
                id=2,
                window_id=1,
                url="https://test.com",
                title="Test Domain",
                browser_id="test-browser-1",
                domain="test.com",
                is_active=False
            )
        ]
    
    def test_browser_detector(self):
        """Test browser detector."""
        # Mock the _update_browser_data method to return test data
        with patch.object(BrowserDetector, '_update_browser_data') as mock_update:
            # Set up the mock to update the _browsers dictionary
            def side_effect():
                self.browser_detector._browsers = {"test-browser-1": self.test_browser}
                self.browser_detector._last_update_time = time.time()
            mock_update.side_effect = side_effect
            
            # Test get_active_browsers
            browsers = self.browser_detector.get_active_browsers()
            self.assertEqual(len(browsers), 1)
            self.assertEqual(browsers[0].id, "test-browser-1")
            self.assertEqual(browsers[0].type, BrowserType.CHROME)
            
            # Test get_active_browser_window
            active_browser = self.browser_detector.get_active_browser_window()
            self.assertIsNotNone(active_browser)
            self.assertEqual(active_browser.id, "test-browser-1")
    
    def test_tab_tracker(self):
        """Test tab tracker."""
        # Mock the _update_tab_data method to return test data
        with patch.object(TabTracker, '_update_tab_data') as mock_update:
            # Set up the mock to update the _tabs dictionary
            def side_effect():
                self.tab_tracker._tabs = {tab.id: tab for tab in self.test_tabs}
                self.tab_tracker._last_update_time = time.time()
            mock_update.side_effect = side_effect
            
            # Test get_all_tabs
            tabs = self.tab_tracker.get_all_tabs()
            self.assertEqual(len(tabs), 2)
            
            # Test get_active_tab
            active_tab = self.tab_tracker.get_active_tab()
            self.assertIsNotNone(active_tab)
            self.assertEqual(active_tab.url, "https://example.com")
            
            # Test get_tabs_by_domain
            domain_tabs = self.tab_tracker.get_tabs_by_domain("example.com")
            self.assertEqual(len(domain_tabs), 1)
            self.assertEqual(domain_tabs[0].url, "https://example.com")
    
    def test_tab_blocker(self):
        """Test tab blocker."""
        # Test block_domain
        self.assertTrue(self.tab_blocker.block_domain("example.com"))
        self.assertTrue(self.tab_blocker.is_domain_blocked("example.com"))
        self.assertFalse(self.tab_blocker.is_domain_blocked("test.com"))
        
        # Test close_tab
        self.assertTrue(self.tab_blocker.close_tab(self.test_tabs[0]))
        
        # Test block_domain with duration
        self.assertTrue(self.tab_blocker.block_domain("temporary.com", 1))
        self.assertTrue(self.tab_blocker.is_domain_blocked("temporary.com"))
        
        # Wait for block to expire
        time.sleep(1.1)
        self.assertFalse(self.tab_blocker.is_domain_blocked("temporary.com"))
    
    def test_integration_classes(self):
        """Test integration classes."""
        # Test BrowserTabTracker initialization
        browser_tab_tracker = BrowserTabTracker()
        self.assertIsNotNone(browser_tab_tracker)
        
        # Test BrowserTabBlocker initialization
        browser_tab_blocker = BrowserTabBlocker()
        self.assertIsNotNone(browser_tab_blocker)
        
        # Test BrowserExtensionManager initialization
        extension_manager = BrowserExtensionManager()
        self.assertIsNotNone(extension_manager)
        
        # Test BrowserUsageTracker interface exists
        # Note: We don't instantiate it directly since it's an abstract class
        self.assertTrue(hasattr(BrowserUsageTracker, 'record_tab_event'))
        self.assertTrue(hasattr(BrowserUsageTracker, 'record_domain_visit'))
        self.assertTrue(hasattr(BrowserUsageTracker, 'record_browser_session'))
        self.assertTrue(hasattr(BrowserUsageTracker, 'end_browser_session'))


if __name__ == "__main__":
    unittest.main()
