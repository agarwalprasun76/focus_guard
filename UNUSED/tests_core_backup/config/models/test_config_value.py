"""
Unit tests for configuration value models.

This module contains unit tests for the configuration value models.
"""

import unittest
from unittest.mock import MagicMock, patch
from typing import Any, Dict, List, Optional

from core_v2.config.models.config_value import (
    ConfigurationValue, StringConfigValue, IntConfigValue,
    BoolConfigValue, ListConfigValue, DictConfigValue
)


class TestConfigurationValue(unittest.TestCase):
    """Test cases for ConfigurationValue base class."""
    
    def test_init(self):
        """Test initialization."""
        # Create a mock value
        value = ConfigurationValue("test", "value")
        
        # Check properties
        self.assertEqual(value.path, "test")
        self.assertEqual(value.get_value(), "value")
        self.assertFalse(value.is_modified())
    
    def test_set_value(self):
        """Test setting value."""
        # Create a mock value
        value = ConfigurationValue("test", "value")
        
        # Set value
        value.set_value("new_value")
        
        # Check properties
        self.assertEqual(value.get_value(), "new_value")
        self.assertTrue(value.is_modified())
    
    def test_reset(self):
        """Test resetting value."""
        # Create a mock value
        value = ConfigurationValue("test", "value")
        
        # Set value and reset
        value.set_value("new_value")
        value.reset()
        
        # Check properties
        self.assertEqual(value.get_value(), "value")
        self.assertFalse(value.is_modified())
    
    def test_commit(self):
        """Test committing value."""
        # Create a mock value
        value = ConfigurationValue("test", "value")
        
        # Set value and commit
        value.set_value("new_value")
        value.commit()
        
        # Check properties
        self.assertEqual(value.get_value(), "new_value")
        self.assertFalse(value.is_modified())
    
    def test_on_change(self):
        """Test on_change callback."""
        # Create a mock callback
        callback = MagicMock()
        
        # Create a mock value with callback
        value = ConfigurationValue("test", "value")
        value.on_change(callback)
        
        # Set value
        value.set_value("new_value")
        
        # Check callback
        callback.assert_called_once_with("test", "new_value")
        
        # Remove callback
        value.remove_on_change(callback)
        
        # Set value again
        callback.reset_mock()
        value.set_value("another_value")
        
        # Check callback
        callback.assert_not_called()


class TestStringConfigValue(unittest.TestCase):
    """Test cases for StringConfigValue."""
    
    def test_init(self):
        """Test initialization."""
        # Create a string value
        value = StringConfigValue("test", "value")
        
        # Check properties
        self.assertEqual(value.path, "test")
        self.assertEqual(value.get_value(), "value")
        self.assertFalse(value.is_modified())
    
    def test_validation(self):
        """Test validation."""
        # Create a string value with min and max length
        value = StringConfigValue("test", "value", min_length=3, max_length=10)
        
        # Valid values
        self.assertTrue(value.validate("abc"))
        self.assertTrue(value.validate("abcdefghij"))
        
        # Invalid values
        self.assertFalse(value.validate("ab"))
        self.assertFalse(value.validate("abcdefghijk"))
        self.assertFalse(value.validate(123))
        
        # Create a string value with pattern
        value = StringConfigValue("test", "value", pattern=r"^[a-z]+$")
        
        # Valid values
        self.assertTrue(value.validate("abc"))
        
        # Invalid values
        self.assertFalse(value.validate("123"))
        self.assertFalse(value.validate("abc123"))


class TestIntConfigValue(unittest.TestCase):
    """Test cases for IntConfigValue."""
    
    def test_init(self):
        """Test initialization."""
        # Create an int value
        value = IntConfigValue("test", 42)
        
        # Check properties
        self.assertEqual(value.path, "test")
        self.assertEqual(value.get_value(), 42)
        self.assertFalse(value.is_modified())
    
    def test_validation(self):
        """Test validation."""
        # Create an int value with min and max
        value = IntConfigValue("test", 42, min_value=0, max_value=100)
        
        # Valid values
        self.assertTrue(value.validate(0))
        self.assertTrue(value.validate(100))
        self.assertTrue(value.validate(42))
        
        # Invalid values
        self.assertFalse(value.validate(-1))
        self.assertFalse(value.validate(101))
        self.assertFalse(value.validate("42"))
        
        # Create an int value with allowed values
        value = IntConfigValue("test", 42, allowed_values=[0, 42, 100])
        
        # Valid values
        self.assertTrue(value.validate(0))
        self.assertTrue(value.validate(42))
        self.assertTrue(value.validate(100))
        
        # Invalid values
        self.assertFalse(value.validate(1))
        self.assertFalse(value.validate(99))


class TestBoolConfigValue(unittest.TestCase):
    """Test cases for BoolConfigValue."""
    
    def test_init(self):
        """Test initialization."""
        # Create a bool value
        value = BoolConfigValue("test", True)
        
        # Check properties
        self.assertEqual(value.path, "test")
        self.assertEqual(value.get_value(), True)
        self.assertFalse(value.is_modified())
    
    def test_validation(self):
        """Test validation."""
        # Create a bool value
        value = BoolConfigValue("test", True)
        
        # Valid values
        self.assertTrue(value.validate(True))
        self.assertTrue(value.validate(False))
        
        # Invalid values
        self.assertFalse(value.validate(0))
        self.assertFalse(value.validate(1))
        self.assertFalse(value.validate("True"))


class TestListConfigValue(unittest.TestCase):
    """Test cases for ListConfigValue."""
    
    def test_init(self):
        """Test initialization."""
        # Create a list value
        value = ListConfigValue("test", [1, 2, 3])
        
        # Check properties
        self.assertEqual(value.path, "test")
        self.assertEqual(value.get_value(), [1, 2, 3])
        self.assertFalse(value.is_modified())
    
    def test_validation(self):
        """Test validation."""
        # Create a list value with min and max length
        value = ListConfigValue("test", [1, 2, 3], min_length=1, max_length=5)
        
        # Valid values
        self.assertTrue(value.validate([1]))
        self.assertTrue(value.validate([1, 2, 3, 4, 5]))
        
        # Invalid values
        self.assertFalse(value.validate([]))
        self.assertFalse(value.validate([1, 2, 3, 4, 5, 6]))
        self.assertFalse(value.validate("not a list"))
        
        # Create a list value with item validator
        def validate_item(item):
            return isinstance(item, int) and 0 <= item <= 10
        
        value = ListConfigValue("test", [1, 2, 3], item_validator=validate_item)
        
        # Valid values
        self.assertTrue(value.validate([1, 2, 3]))
        self.assertTrue(value.validate([0, 5, 10]))
        
        # Invalid values
        self.assertFalse(value.validate([1, 2, 11]))
        self.assertFalse(value.validate([1, "2", 3]))


class TestDictConfigValue(unittest.TestCase):
    """Test cases for DictConfigValue."""
    
    def test_init(self):
        """Test initialization."""
        # Create a dict value
        value = DictConfigValue("test", {"a": 1, "b": 2})
        
        # Check properties
        self.assertEqual(value.path, "test")
        self.assertEqual(value.get_value(), {"a": 1, "b": 2})
        self.assertFalse(value.is_modified())
    
    def test_validation(self):
        """Test validation."""
        # Create a dict value with required keys
        value = DictConfigValue("test", {"a": 1, "b": 2}, required_keys=["a"])
        
        # Valid values
        self.assertTrue(value.validate({"a": 1}))
        self.assertTrue(value.validate({"a": 1, "b": 2}))
        self.assertTrue(value.validate({"a": 1, "c": 3}))
        
        # Invalid values
        self.assertFalse(value.validate({}))
        self.assertFalse(value.validate({"b": 2}))
        self.assertFalse(value.validate("not a dict"))
        
        # Create a dict value with key validator
        def validate_key(key):
            return isinstance(key, str) and key.isalpha()
        
        value = DictConfigValue("test", {"a": 1, "b": 2}, key_validator=validate_key)
        
        # Valid values
        self.assertTrue(value.validate({"a": 1, "b": 2}))
        self.assertTrue(value.validate({"abc": 1}))
        
        # Invalid values
        self.assertFalse(value.validate({"123": 1}))
        self.assertFalse(value.validate({"a-b": 1}))
        
        # Create a dict value with value validator
        def validate_value(value):
            return isinstance(value, int) and 0 <= value <= 10
        
        value = DictConfigValue("test", {"a": 1, "b": 2}, value_validator=validate_value)
        
        # Valid values
        self.assertTrue(value.validate({"a": 1, "b": 2}))
        self.assertTrue(value.validate({"a": 0, "b": 10}))
        
        # Invalid values
        self.assertFalse(value.validate({"a": -1}))
        self.assertFalse(value.validate({"a": 11}))
        self.assertFalse(value.validate({"a": "1"}))


if __name__ == "__main__":
    unittest.main()
