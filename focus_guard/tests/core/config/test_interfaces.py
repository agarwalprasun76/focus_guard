"""
Unit tests for configuration interfaces.

This module contains unit tests for the configuration interfaces.
"""

import unittest
from unittest.mock import MagicMock, patch
from typing import Any, Dict, Optional, Set

from focus_guard.core.config.interfaces import ConfigPath, ConfigProvider, ConfigScope, ConfigSchema, ConfigValidator


class TestConfigInterfaces(unittest.TestCase):
    """Test cases for configuration interfaces."""
    
    def test_config_scope(self):
        """Test the ConfigScope enum."""
        # ConfigScope uses auto() values, so we test the enum members exist
        self.assertIsNotNone(ConfigScope.SYSTEM)
        self.assertIsNotNone(ConfigScope.USER)
        self.assertIsNotNone(ConfigScope.SESSION)
        self.assertIsNotNone(ConfigScope.MEMORY)
        # Test that they have different values
        self.assertNotEqual(ConfigScope.SYSTEM.value, ConfigScope.USER.value)
    
    def test_config_provider_interface(self):
        """Test the ConfigProvider interface."""
        # Create a mock provider
        provider = MagicMock(spec=ConfigProvider)
        
        # Set up return values
        provider.get_name.return_value = "mock"
        provider.get_value.return_value = "value"
        provider.set_value.return_value = True
        provider.delete_value.return_value = True
        provider.has_value.return_value = True
        provider.get_all_paths.return_value = {"path1", "path2"}
        provider.get_scope.return_value = ConfigScope.USER
        provider.load.return_value = True
        provider.save.return_value = True
        provider.clear.return_value = True
        
        # Test the provider methods
        self.assertEqual(provider.get_name(), "mock")
        self.assertEqual(provider.get_value("path"), "value")
        self.assertTrue(provider.set_value("path", "value"))
        self.assertTrue(provider.delete_value("path"))
        self.assertTrue(provider.has_value("path"))
        self.assertEqual(provider.get_all_paths(), {"path1", "path2"})
        self.assertEqual(provider.get_scope(), ConfigScope.USER)
        self.assertTrue(provider.load())
        self.assertTrue(provider.save())
        self.assertTrue(provider.clear())
    
    def test_config_validator_interface(self):
        """Test the ConfigValidator interface."""
        # Create a mock validator
        validator = MagicMock(spec=ConfigValidator)
        
        # Set up return values
        validator.validate.return_value = (True, None)
        
        # Test the validator methods
        self.assertEqual(validator.validate("value"), (True, None))
    
    def test_config_schema_interface(self):
        """Test the ConfigSchema interface."""
        # Create a mock schema
        schema = MagicMock(spec=ConfigSchema)
        
        # Set up return values
        schema.get_name.return_value = "mock"
        schema.get_description.return_value = "Mock schema"
        schema.validate.return_value = (True, {})
        schema.get_defaults.return_value = {"key": "default"}
        schema.create_instance.return_value = {"key": "value"}
        
        # Test the schema methods
        self.assertEqual(schema.get_name(), "mock")
        self.assertEqual(schema.get_description(), "Mock schema")
        self.assertEqual(schema.validate({}), (True, {}))
        self.assertEqual(schema.get_defaults(), {"key": "default"})
        self.assertEqual(schema.create_instance({}), {"key": "value"})


if __name__ == "__main__":
    unittest.main()
