"""
Tests for the browser activity tracker.

This module contains tests for the StandardBrowserTracker class.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from core_v2.distraction.models import DistractionState
from core_v2.distraction.trackers.browser_tracker import StandardBrowserTracker
from core_v2.domain.models import Domain, Category, Classification


class TestStandardBrowserTracker(unittest.TestCase):
    """Tests for the StandardBrowserTracker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.browser_integration = MagicMock()
        self.domain_classifier = MagicMock()
        self.tracker = StandardBrowserTracker(
            browser_integration=self.browser_integration,
            domain_classifier=self.domain_classifier
        )
    
    def test_name(self):
        """Test name property."""
        self.assertEqual(self.tracker.name, "Standard Browser Tracker")
    
    def test_register_state_update_callback(self):
        """Test register_state_update_callback method."""
        callback = MagicMock()
        self.tracker.register_state_update_callback(callback)
        
        # Verify callback was registered
        self.assertIn(callback, self.tracker._state_update_callbacks)
    
    def test_update_state_no_tabs(self):
        """Test update_state with no tabs."""
        # Mock browser integration
        self.browser_integration.get_active_tabs.return_value = {}
        
        # Create state
        state = DistractionState()
        
        # Update state
        self.tracker.update_state(state)
        
        # Verify state was updated
        browser_tabs = state.browser_tabs
        self.assertIsNone(browser_tabs.get("active_tab"))
        self.assertEqual(browser_tabs.get("all_tabs"), [])
        self.assertIn("last_update", browser_tabs)
    
    @patch('core_v2.domain.utils.extract_domain_from_url')
    def test_update_state_with_tabs(self, mock_extract_domain):
        """Test update_state with tabs."""
        # Mock extract_domain_from_url
        mock_extract_domain.return_value = "example.com"
        
        # Mock browser integration
        self.browser_integration.get_active_tabs.return_value = {
            "active_tab": {"url": "https://example.com", "title": "Example"},
            "all_tabs": [
                {"url": "https://example.com", "title": "Example"},
                {"url": "https://example.org", "title": "Another Example"}
            ]
        }
        
        # Mock domain classifier
        domain = Domain("example.com")
        category = Category.SOCIAL_MEDIA
        classification = Classification(domain=domain, category=category, confidence=0.9)
        self.domain_classifier.classify.return_value = classification
        
        # Create state
        state = DistractionState()
        
        # Update state
        self.tracker.update_state(state)
        
        # Verify state was updated
        self.assertIsNotNone(state.browser_tabs.get("active_tab"))
        self.assertEqual(len(state.browser_tabs.get("all_tabs", [])), 2)
        
        # Verify active tab was classified
        active_tab = state.browser_tabs.get("active_tab")
        self.assertEqual(active_tab.get("domain"), "example.com")
        self.assertEqual(active_tab.get("category"), Category.SOCIAL_MEDIA.name)
    
    def test_on_tab_event(self):
        """Test _on_tab_event method."""
        # Create callback
        callback = MagicMock()
        self.tracker.register_state_update_callback(callback)
        
        # Create tab event
        event = {
            "type": "tab_created",
            "tab": {"url": "https://example.com", "title": "Example"}
        }
        
        # Call _on_tab_event
        self.tracker._on_tab_event(event)
        
        # Verify callback was called
        callback.assert_called_once_with(event)


if __name__ == "__main__":
    unittest.main()
