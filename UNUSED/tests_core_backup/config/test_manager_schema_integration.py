"""
Integration tests for ConfigurationManager and JsonConfigSchema.

This module tests the integration between the ConfigurationManager and JsonConfigSchema classes,
focusing on schema validation during get/set operations.
"""

import unittest
import os
import tempfile
import json
from typing import Dict, Any

from core_v2.config.interfaces import ConfigScope
from core_v2.config.manager import DefaultConfigurationManager
from core_v2.config.providers.memory_provider import MemoryConfigProvider
from core_v2.config.schema.schema import JsonConfigSchema


class TestManagerSchemaIntegration(unittest.TestCase):
    """Tests for the integration between ConfigurationManager and JsonConfigSchema."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a memory provider for testing
        self.provider = MemoryConfigProvider()
        
        # Create a configuration manager with the memory provider
        self.manager = DefaultConfigurationManager()
        self.manager.register_provider(self.provider, ConfigScope.USER)
        
        # Create test schemas
        self.user_schema = JsonConfigSchema(
            name="user",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer", "minimum": 18},
                    "email": {"type": "string"},
                    "preferences": {
                        "type": "object",
                        "properties": {
                            "theme": {"type": "string", "enum": ["light", "dark"]},
                            "notifications": {"type": "boolean", "default": True}
                        }
                    }
                },
                "required": ["name", "age"]
            }
        )
        
        self.app_settings_schema = JsonConfigSchema(
            name="app_settings",
            schema={
                "type": "object",
                "properties": {
                    "timeout": {"type": "integer", "minimum": 0, "default": 30},
                    "debug": {"type": "boolean", "default": False},
                    "log_level": {"type": "string", "enum": ["debug", "info", "warning", "error"], "default": "info"}
                }
            }
        )
        
        # Register schemas with the manager
        self.manager.register_schema(self.user_schema)
        self.manager.register_schema(self.app_settings_schema)

    def test_get_with_schema_validation(self):
        """Test getting values with schema validation."""
        # Set up some valid data
        self.provider.set("user.name", "John")
        self.provider.set("user.age", 25)
        self.provider.set("user.preferences.theme", "light")
        
        # Test getting valid values
        name = self.manager.get_value("user.name")
        self.assertEqual(name, "John")
        
        age = self.manager.get_value("user.age")
        self.assertEqual(age, 25)
        
        theme = self.manager.get_value("user.preferences.theme")
        self.assertEqual(theme, "light")
        
        # Test getting default values
        notifications = self.manager.get_value("user.preferences.notifications")
        self.assertEqual(notifications, True)  # Default value from schema
        
        # Test getting app settings with defaults
        timeout = self.manager.get_value("app_settings.timeout")
        self.assertEqual(timeout, 30)  # Default value from schema
        
        debug = self.manager.get_value("app_settings.debug")
        self.assertEqual(debug, False)  # Default value from schema

    def test_set_with_schema_validation(self):
        """Test setting values with schema validation."""
        # Set valid values
        self.manager.set_value("user.name", "Jane")
        self.assertEqual(self.provider.get("user.name"), "Jane")
        
        self.manager.set_value("user.age", 30)
        self.assertEqual(self.provider.get("user.age"), 30)
        
        self.manager.set_value("user.preferences.theme", "dark")
        self.assertEqual(self.provider.get("user.preferences.theme"), "dark")
        
        # Test setting with type coercion
        self.manager.set_value("user.age", "35")  # String should be coerced to int
        self.assertEqual(self.provider.get("user.age"), 35)
        self.assertIsInstance(self.provider.get("user.age"), int)
        
        self.manager.set_value("user.preferences.notifications", "true")  # String should be coerced to bool
        self.assertEqual(self.provider.get("user.preferences.notifications"), True)
        self.assertIsInstance(self.provider.get("user.preferences.notifications"), bool)
        
        # Test invalid values
        with self.assertRaises(ValueError):
            self.manager.set_value("user.age", 15)  # Below minimum
            
        with self.assertRaises(ValueError):
            self.manager.set_value("user.preferences.theme", "blue")  # Not in enum
            
        # Test required fields
        with self.assertRaises(ValueError):
            # Create a new user without required fields
            self.manager.set_value("new_user", {"email": "test@example.com"})

    def test_validate_configuration(self):
        """Test validating the entire configuration."""
        # Set up valid configuration
        self.provider.set("user.name", "John")
        self.provider.set("user.age", 25)
        self.provider.set("app_settings.timeout", 60)
        
        # Validate configuration
        is_valid, errors = self.manager.validate_configuration()
        self.assertTrue(is_valid)
        self.assertEqual(errors, {})
        
        # Introduce an invalid value
        self.provider.set("user.age", 15)  # Below minimum
        
        # Validate configuration again
        is_valid, errors = self.manager.validate_configuration()
        self.assertFalse(is_valid)
        self.assertIn("user.age", errors)

    def test_create_instance(self):
        """Test creating an instance from a schema."""
        # Set up valid data
        self.provider.set("user.name", "John")
        self.provider.set("user.age", 25)
        self.provider.set("user.email", "john@example.com")
        self.provider.set("user.preferences.theme", "dark")
        
        # Create instance
        user_data = self.manager.get_section("user")
        
        # Verify the data
        self.assertEqual(user_data["name"], "John")
        self.assertEqual(user_data["age"], 25)
        self.assertEqual(user_data["email"], "john@example.com")
        self.assertEqual(user_data["preferences"]["theme"], "dark")
        self.assertEqual(user_data["preferences"]["notifications"], True)  # Default value

    def test_json_file_provider_integration(self):
        """Test integration with a JSON file provider."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
            temp_file.write(b"{}")
        
        try:
            # Import here to avoid circular imports
            from core_v2.config.providers.json_provider import JsonConfigProvider
            
            # Create a JSON provider with the temp file
            json_provider = JsonConfigProvider(temp_file.name)
            
            # Create a new manager with the JSON provider
            manager = DefaultConfigurationManager()
            manager.register_provider(json_provider, ConfigScope.USER)
            
            # Register schemas
            manager.register_schema(self.user_schema)
            
            # Set and get values
            manager.set_value("user.name", "Alice")
            manager.set_value("user.age", 28)
            
            # Verify values
            self.assertEqual(manager.get_value("user.name"), "Alice")
            self.assertEqual(manager.get_value("user.age"), 28)
            
            # Check the file contents
            with open(temp_file.name, "r") as f:
                data = json.load(f)
                self.assertEqual(data.get("user", {}).get("name"), "Alice")
                self.assertEqual(data.get("user", {}).get("age"), 28)
        
        finally:
            # Clean up
            os.unlink(temp_file.name)


if __name__ == "__main__":
    unittest.main()
