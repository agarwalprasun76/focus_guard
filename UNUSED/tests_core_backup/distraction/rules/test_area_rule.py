"""
Tests for the area increase distraction rule.

This module contains tests for the AreaIncreaseRule class.
"""

import unittest

from core_v2.distraction.models import DistractionAlert, DistractionState, AlertLevel
from core_v2.distraction.rules.area_rule import AreaIncreaseRule


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
