"""
Unit tests for the schema validation system.

This module tests the JsonConfigSchema class and its validation capabilities.
"""

import unittest
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

from focus_guard.core.config.schema.schema import JsonConfigSchema, create_schema_from_dataclass


class TestJsonConfigSchema(unittest.TestCase):
    """Tests for the JsonConfigSchema class."""

    def setUp(self):
        """Set up test fixtures."""
        self.simple_schema = JsonConfigSchema(
            name="test",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer", "minimum": 0},
                    "is_active": {"type": "boolean"}
                },
                "required": ["name", "age"]
            }
        )

        self.nested_schema = JsonConfigSchema(
            name="nested",
            schema={
                "type": "object",
                "properties": {
                    "user": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "preferences": {
                                "type": "object",
                                "properties": {
                                    "theme": {"type": "string", "enum": ["light", "dark"]},
                                    "notifications": {"type": "boolean"}
                                }
                            }
                        },
                        "required": ["name"]
                    },
                    "settings": {
                        "type": "object",
                        "properties": {
                            "timeout": {"type": "integer", "minimum": 1},
                            "debug": {"type": "boolean", "default": False}
                        }
                    }
                }
            }
        )

        self.array_schema = JsonConfigSchema(
            name="array_test",
            schema={
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1
                    },
                    "scores": {
                        "type": "array",
                        "items": {"type": "number", "minimum": 0, "maximum": 100}
                    }
                }
            }
        )

    def test_validate_simple_schema(self):
        """Test validation of a simple schema."""
        # Valid data
        valid_data = {"name": "John", "age": 30, "is_active": True}
        is_valid, errors = self.simple_schema.validate(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(errors, {})

        # Missing required field
        invalid_data = {"name": "John"}
        is_valid, errors = self.simple_schema.validate(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("age", str(errors))

        # Wrong type
        invalid_data = {"name": "John", "age": "thirty"}
        is_valid, errors = self.simple_schema.validate(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("age", str(errors))

        # Value out of range
        invalid_data = {"name": "John", "age": -5}
        is_valid, errors = self.simple_schema.validate(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("age", str(errors))

    def test_validate_nested_schema(self):
        """Test validation of a nested schema."""
        # Valid data
        valid_data = {
            "user": {
                "name": "John",
                "email": "john@example.com",
                "preferences": {
                    "theme": "dark",
                    "notifications": True
                }
            },
            "settings": {
                "timeout": 30,
                "debug": True
            }
        }
        is_valid, errors = self.nested_schema.validate(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(errors, {})

        # Invalid nested property
        invalid_data = {
            "user": {
                "name": "John",
                "preferences": {
                    "theme": "blue",  # Not in enum
                    "notifications": True
                }
            }
        }
        is_valid, errors = self.nested_schema.validate(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("theme", str(errors))

    def test_validate_array_schema(self):
        """Test validation of arrays in schema."""
        # Valid data
        valid_data = {
            "tags": ["important", "urgent"],
            "scores": [85, 90, 75]
        }
        is_valid, errors = self.array_schema.validate(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(errors, {})

        # Empty array (violates minItems)
        invalid_data = {
            "tags": [],
            "scores": [85, 90]
        }
        is_valid, errors = self.array_schema.validate(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("tags", str(errors))

        # Invalid array item
        invalid_data = {
            "tags": ["important"],
            "scores": [85, 110, 75]  # 110 exceeds maximum
        }
        is_valid, errors = self.array_schema.validate(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("scores", str(errors))

    def test_validate_value(self):
        """Test validating a single value at a specific path."""
        # Valid value
        is_valid, error = self.simple_schema.validate_value("test.age", 30)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

        # Invalid value
        is_valid, error = self.simple_schema.validate_value("test.age", -5)
        self.assertFalse(is_valid)
        self.assertIn("minimum", error)

        # Invalid path
        is_valid, error = self.simple_schema.validate_value("test.unknown", "value")
        self.assertFalse(is_valid)
        self.assertIn("not found", error)

        # Nested path
        is_valid, error = self.nested_schema.validate_value("nested.user.preferences.theme", "dark")
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

        is_valid, error = self.nested_schema.validate_value("nested.user.preferences.theme", "blue")
        self.assertFalse(is_valid)
        self.assertIn("enum", error)

    def test_coerce_value(self):
        """Test coercing values to the correct type."""
        # String to integer
        coerced = self.simple_schema.coerce_value("test.age", "25")
        self.assertEqual(coerced, 25)
        self.assertIsInstance(coerced, int)

        # String to boolean
        coerced = self.simple_schema.coerce_value("test.is_active", "true")
        self.assertEqual(coerced, True)
        self.assertIsInstance(coerced, bool)

        # Float to integer (when it's a whole number)
        coerced = self.simple_schema.coerce_value("test.age", 25.0)
        self.assertEqual(coerced, 25)
        self.assertIsInstance(coerced, int)

        # Non-coercible value
        coerced = self.simple_schema.coerce_value("test.age", "twenty-five")
        self.assertEqual(coerced, "twenty-five")  # Returns original value
        self.assertIsInstance(coerced, str)

    def test_get_path_mappings(self):
        """Test getting path mappings from a schema."""
        paths = self.simple_schema.get_path_mappings()
        expected_paths = {"test", "test.name", "test.age", "test.is_active"}
        self.assertEqual(paths, expected_paths)

        paths = self.nested_schema.get_path_mappings()
        self.assertIn("nested.user.preferences.theme", paths)
        self.assertIn("nested.settings.timeout", paths)

    def test_get_default_values(self):
        """Test extracting default values from a schema."""
        schema = JsonConfigSchema(
            name="defaults",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "default": "Anonymous"},
                    "age": {"type": "integer", "default": 18},
                    "settings": {
                        "type": "object",
                        "properties": {
                            "debug": {"type": "boolean", "default": False},
                            "theme": {"type": "string", "default": "light"}
                        }
                    }
                }
            }
        )

        defaults = schema.get_default_values()
        self.assertEqual(defaults.get("defaults.name"), "Anonymous")
        self.assertEqual(defaults.get("defaults.age"), 18)
        self.assertEqual(defaults.get("defaults.settings.debug"), False)
        self.assertEqual(defaults.get("defaults.settings.theme"), "light")


class TestDataclassSchemaConversion(unittest.TestCase):
    """Tests for dataclass to schema conversion."""

    def test_create_schema_from_dataclass(self):
        """Test creating a schema from a dataclass."""
        @dataclass
        class User:
            """User dataclass for testing."""
            name: str
            age: int
            email: Optional[str] = None
            is_active: bool = True
            tags: List[str] = None

        schema = create_schema_from_dataclass(User)

        # Check schema structure
        self.assertEqual(schema.get_name(), "User")
        self.assertEqual(schema._schema["type"], "object")
        self.assertIn("name", schema._schema["required"])
        self.assertIn("age", schema._schema["required"])
        self.assertNotIn("email", schema._schema["required"])
        self.assertNotIn("is_active", schema._schema["required"])

        # Check property types
        self.assertEqual(schema._schema["properties"]["name"]["type"], "string")
        self.assertEqual(schema._schema["properties"]["age"]["type"], "integer")
        self.assertEqual(schema._schema["properties"]["is_active"]["type"], "boolean")
        self.assertEqual(schema._schema["properties"]["is_active"]["default"], True)

        # Validate with the schema
        valid_data = {"name": "John", "age": 30, "email": "john@example.com"}
        is_valid, errors = schema.validate(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(errors, {})

        invalid_data = {"name": "John"}  # Missing required age
        is_valid, errors = schema.validate(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("age", str(errors))


if __name__ == "__main__":
    unittest.main()
