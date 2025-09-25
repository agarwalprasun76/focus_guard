"""
Tests for distraction detection rules.

This module contains tests for the distraction detection rules.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from core_v2.distraction.models import DistractionAlert, DistractionState, AlertLevel
from core_v2.distraction.rules.base import BaseDistractionRule
from core_v2.distraction.rules.url_rule import URLRule
from core_v2.distraction.rules.context_rule import ContextSwitchRule
from core_v2.distraction.rules.area_rule import AreaIncreaseRule
from core_v2.domain.models import Domain, Category, Classification


class TestBaseDistractionRule(unittest.TestCase):
    """Tests for the BaseDistractionRule class."""
    
    def test_create_alert(self):
        """Test creating an alert."""
        # Create a concrete subclass for testing
        class TestRule(BaseDistractionRule):
            @property
            def name(self):
                return "Test Rule"
                
            @property
            def description(self):
                return "Test rule description"
                
            def should_apply(self, state):
                return True
                
            def check(self, state):
                return []
        
        # Create an instance
        rule = TestRule()
        
        # Test creating an alert
        alert = rule.create_alert(
            message="Test message",
            level=AlertLevel.WARNING,
            metadata={"key": "value"}
        )
        
        self.assertEqual(alert.rule_name, "Test Rule")
        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertEqual(alert.message, "Test message")
        self.assertEqual(alert.metadata, {"key": "value"})
        self.assertIsNotNone(alert.timestamp)
    
    def test_is_enabled(self):
        """Test is_enabled method."""
        # Create a concrete subclass for testing
        class TestRule(BaseDistractionRule):
            @property
            def name(self):
                return "Test Rule"
                
            @property
            def description(self):
                return "Test rule description"
                
            def should_apply(self, state):
                return True
                
            def check(self, state):
                return []
        
        # Test with default config (enabled)
        rule = TestRule()
        self.assertTrue(rule.is_enabled())
        
        # Test with explicit enabled config
        rule = TestRule({"enabled": True})
        self.assertTrue(rule.is_enabled())
        
        # Test with disabled config
        rule = TestRule({"enabled": False})
        self.assertFalse(rule.is_enabled())


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
    
    @patch('core_v2.domain.utils.extract_domain_from_url')
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
    
    @patch('core_v2.domain.utils.extract_domain_from_url')
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


class TestContextSwitchRule(unittest.TestCase):
    """Tests for the ContextSwitchRule class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rule = ContextSwitchRule(switch_threshold=3, time_window_seconds=60)
    
    def test_should_apply(self):
        """Test should_apply method."""
        # Create a state with a window
        state = DistractionState()
        state.update(
            {"app_name": "notepad", "title": "Test Window"},
            []
        )
        
        # Test should_apply
        self.assertTrue(self.rule.should_apply(state))
        
        # Create a state with no window
        state = DistractionState()
        
        # Test should_apply
        self.assertFalse(self.rule.should_apply(state))
    
    def test_check_no_switching(self):
        """Test check with no switching."""
        # Create a state with a window
        state = DistractionState()
        state.update(
            {"app_name": "notepad", "title": "Test Window"},
            []
        )
        
        # Test check
        alerts = self.rule.check(state)
        self.assertEqual(len(alerts), 0)
    
    def test_check_with_switching(self):
        """Test check with switching."""
        # Create a rule with lower threshold
        rule = ContextSwitchRule(switch_threshold=2, time_window_seconds=60)
        
        # Create a state with a window
        state = DistractionState()
        
        # First app
        state.update(
            {"app_name": "notepad", "title": "Test Window"},
            []
        )
        rule.check(state)
        
        # Switch to second app
        state.update(
            {"app_name": "chrome", "title": "Browser"},
            []
        )
        rule.check(state)
        
        # Switch back to first app
        state.update(
            {"app_name": "notepad", "title": "Test Window"},
            []
        )
        alerts = rule.check(state)
        
        # Should have an alert
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].rule_name, "Context Switch Rule")
        self.assertEqual(alerts[0].level, AlertLevel.WARNING)
        self.assertIn("switching", alerts[0].message.lower())
    
    def test_check_old_switches_ignored(self):
        """Test check with old switches ignored."""
        # Create a rule with mocked time
        rule = ContextSwitchRule(switch_threshold=2, time_window_seconds=60)
        
        # Create a state with a window
        state = DistractionState()
        
        # Mock _recent_switches to return empty list (as if all switches are old)
        rule._recent_switches = MagicMock(return_value=[])
        
        # First app
        state.update(
            {"app_name": "notepad", "title": "Test Window"},
            []
        )
        rule.check(state)
        
        # Switch to second app
        state.update(
            {"app_name": "chrome", "title": "Browser"},
            []
        )
        rule.check(state)
        
        # Switch back to first app
        state.update(
            {"app_name": "notepad", "title": "Test Window"},
            []
        )
        alerts = rule.check(state)
        
        # Should have no alerts since all switches are considered old
        self.assertEqual(len(alerts), 0)


class TestAreaIncreaseRule(unittest.TestCase):
    """Tests for the AreaIncreaseRule class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rule = AreaIncreaseRule(area_threshold=50.0, min_area=100)
    
    def test_should_apply(self):
        """Test should_apply method."""
        # Create a state with a window
        state = DistractionState()
        state.update(
            {"app_name": "notepad", "title": "Test Window"},
            []
        )
        
        # Test should_apply
        self.assertTrue(self.rule.should_apply(state))
        
        # Create a state with no window
        state = DistractionState()
        
        # Test should_apply
        self.assertFalse(self.rule.should_apply(state))
    
    def test_check_no_area_increase(self):
        """Test check with no area increase."""
        # Create a state with a window
        state = DistractionState()
        state.update(
            {"app_name": "notepad", "title": "Test Window", "width": 100, "height": 100},
            []
        )
        
        # First check to establish baseline
        alerts = self.rule.check(state)
        self.assertEqual(len(alerts), 0)
        
        # Check again with same area
        alerts = self.rule.check(state)
        self.assertEqual(len(alerts), 0)
    
    def test_check_with_area_increase(self):
        """Test check with area increase."""
        # Create a state with a window
        state = DistractionState()
        state.update(
            {"app_name": "notepad", "title": "Test Window", "width": 100, "height": 100},
            []
        )
        
        # First check to establish baseline
        alerts = self.rule.check(state)
        self.assertEqual(len(alerts), 0)
        
        # Update with increased area
        state.update(
            {"app_name": "notepad", "title": "Test Window", "width": 200, "height": 200},
            []
        )
        
        # Check again with increased area
        alerts = self.rule.check(state)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].rule_name, "Area Increase Rule")
        self.assertEqual(alerts[0].level, AlertLevel.INFO)
        self.assertIn("increased", alerts[0].message.lower())
    
    def test_check_below_min_area(self):
        """Test check with area below minimum."""
        # Create a rule with higher min_area
        rule = AreaIncreaseRule(area_threshold=50.0, min_area=100000)
        
        # Create a state with a window
        state = DistractionState()
        state.update(
            {"app_name": "notepad", "title": "Test Window", "width": 100, "height": 100},
            []
        )
        
        # First check to establish baseline
        alerts = rule.check(state)
        self.assertEqual(len(alerts), 0)
        
        # Update with increased area but still below min_area
        state.update(
            {"app_name": "notepad", "title": "Test Window", "width": 200, "height": 200},
            []
        )
        
        # Check again
        alerts = rule.check(state)
        self.assertEqual(len(alerts), 0)


if __name__ == "__main__":
    unittest.main()
