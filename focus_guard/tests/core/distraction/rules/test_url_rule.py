"""
Tests for the URL distraction rule.

This module contains tests for the URLRule class.
"""

import unittest
from unittest.mock import MagicMock, patch

from focus_guard.core.distraction.models import DistractionAlert, DistractionState, AlertLevel
from focus_guard.core.distraction.rules.url_rule import URLRule
from focus_guard.core.domain.models import Domain, Category, Classification


class TestURLRule(unittest.TestCase):
    """Tests for the URLRule class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.domain_classifier = MagicMock()
        self.rule = URLRule(domain_classifier=self.domain_classifier)
    
    def test_should_apply_browser(self):
        """Test should_apply with browser window."""
        # Create a state with a browser window
        state = DistractionState()
        state.update(
            {"app_name": "chrome", "title": "Test Window"},
            []
        )
        
        # Test should_apply
        self.assertTrue(self.rule.should_apply(state))
    
    def test_should_apply_non_browser(self):
        """Test should_apply with non-browser window."""
        # Create a state with a non-browser window
        state = DistractionState()
        state.update(
            {"app_name": "notepad", "title": "Test Window"},
            []
        )
        
        # Test should_apply
        self.assertFalse(self.rule.should_apply(state))
    
    def test_check_no_window(self):
        """Test check with no window."""
        # Create a state with no window
        state = DistractionState()
        
        # Test check
        alerts = self.rule.check(state)
        self.assertEqual(len(alerts), 0)
    
    def test_check_no_url(self):
        """Test check with no URL."""
        # Create a state with a browser window but no URL
        state = DistractionState()
        state.update(
            {"app_name": "chrome", "title": "Test Window"},
            []
        )
        
        # Test check
        alerts = self.rule.check(state)
        self.assertEqual(len(alerts), 0)
    
    @patch('focus_guard.core.domain.utils.extract_domain_from_url')
    def test_check_distracting_domain(self, mock_extract_domain):
        """Test check with distracting domain."""
        # Mock extract_domain_from_url
        mock_extract_domain.return_value = "example.com"
        
        # Create a state with a browser window and URL
        state = DistractionState()
        state.update(
            {"app_name": "chrome", "title": "Test Window"},
            []
        )
        state.update_browser_tabs({
            "active_tab": {"url": "https://example.com", "title": "Example"}
        })
        
        # Mock domain classifier
        domain = Domain("example.com")
        category = Category.SOCIAL_MEDIA
        classification = Classification(domain=domain, category=category, confidence=0.9)
        self.domain_classifier.classify.return_value = classification
        
        # Test check
        alerts = self.rule.check(state)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].rule_name, "URL Rule")
        self.assertEqual(alerts[0].level, AlertLevel.WARNING)
        self.assertIn("example.com", alerts[0].message)
        self.assertEqual(alerts[0].metadata["domain"], "example.com")
    
    @patch('focus_guard.core.domain.utils.extract_domain_from_url')
    def test_check_whitelisted_domain(self, mock_extract_domain):
        """Test check with whitelisted domain."""
        # Mock extract_domain_from_url
        mock_extract_domain.return_value = "example.com"
        
        # Create a rule with whitelist
        rule = URLRule(
            domain_classifier=self.domain_classifier,
            domain_whitelist={"example.com"}
        )
        
        # Create a state with a browser window and URL
        state = DistractionState()
        state.update(
            {"app_name": "chrome", "title": "Test Window"},
            []
        )
        state.update_browser_tabs({
            "active_tab": {"url": "https://example.com", "title": "Example"}
        })
        
        # Test check
        alerts = rule.check(state)
        self.assertEqual(len(alerts), 0)


if __name__ == "__main__":
    unittest.main()
