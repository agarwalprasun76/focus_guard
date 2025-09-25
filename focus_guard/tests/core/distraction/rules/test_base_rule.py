"""
Tests for the base distraction rule.

This module contains tests for the BaseDistractionRule class.
"""

import unittest
from unittest.mock import MagicMock

from focus_guard.core.distraction.models import DistractionAlert, DistractionState, AlertLevel
from focus_guard.core.distraction.rules.base import BaseDistractionRule


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


if __name__ == "__main__":
    unittest.main()
