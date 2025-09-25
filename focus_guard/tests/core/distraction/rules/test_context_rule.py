"""
Tests for the context switch distraction rule.

This module contains tests for the ContextSwitchRule class.
"""

import unittest
from unittest.mock import MagicMock

from focus_guard.core.distraction.models import DistractionAlert, DistractionState, AlertLevel
from focus_guard.core.distraction.rules.context_rule import ContextSwitchRule


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


if __name__ == "__main__":
    unittest.main()
