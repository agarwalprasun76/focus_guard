"""
Unit tests for the legacy JSON configuration adapter.
"""

import os
import json
import unittest
import tempfile
from unittest.mock import patch, MagicMock

from core_v2.config.adapters.json_adapter import LegacyJsonConfigAdapter, CategoryMappingAdapter


class TestLegacyJsonConfigAdapter(unittest.TestCase):
    """Test cases for the LegacyJsonConfigAdapter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = os.path.join(self.temp_dir.name, "legacy_config.json")
        
        # Define test data
        self.test_data = {
            "app": {
                "name": "Focus Guard",
                "version": "1.0.0"
            },
            "user": {
                "name": "Test User",
                "email": "test@example.com",
                "preferences": {
                    "theme": "dark",
                    "notifications": True
                }
            },
            "settings": {
                "auto_start": True,
                "idle_timeout": 300
            }
        }
        
        # Write test data to the file
        with open(self.config_file, "w") as f:
            json.dump(self.test_data, f)
        
        # Define path mappings
        self.path_mappings = {
            "app.name": "application.name",
            "app.version": "application.version",
            "user": "user_profile",
            "settings": "application.settings"
        }
        
        # Create the adapter
        self.adapter = LegacyJsonConfigAdapter(
            legacy_file_path=self.config_file,
            path_mappings=self.path_mappings
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()
    
    def test_get_name(self):
        """Test getting the adapter name."""
        self.assertEqual(self.adapter.get_name(), "legacy_json")
    
    def test_get_legacy_value(self):
        """Test getting a value from the legacy configuration."""
        # Test getting existing values
        self.assertEqual(self.adapter.get_legacy_value("app.name"), "Focus Guard")
        self.assertEqual(self.adapter.get_legacy_value("user.preferences.theme"), "dark")
        self.assertEqual(self.adapter.get_legacy_value("settings.auto_start"), True)
        
        # Test getting non-existent values
        self.assertIsNone(self.adapter.get_legacy_value("app.description"))
        self.assertEqual(self.adapter.get_legacy_value("app.description", "Default"), "Default")
    
    def test_set_legacy_value(self):
        """Test setting a value in the legacy configuration."""
        # Set an existing value
        self.assertTrue(self.adapter.set_legacy_value("app.name", "New Focus Guard"))
        self.assertEqual(self.adapter.get_legacy_value("app.name"), "New Focus Guard")
        
        # Set a new value
        self.assertTrue(self.adapter.set_legacy_value("app.description", "A focus management tool"))
        self.assertEqual(self.adapter.get_legacy_value("app.description"), "A focus management tool")
        
        # Set a nested value
        self.assertTrue(self.adapter.set_legacy_value("user.preferences.language", "en"))
        self.assertEqual(self.adapter.get_legacy_value("user.preferences.language"), "en")
    
    def test_delete_legacy_value(self):
        """Test deleting a value from the legacy configuration."""
        # Delete an existing value
        self.assertTrue(self.adapter.delete_legacy_value("user.preferences.theme"))
        self.assertIsNone(self.adapter.get_legacy_value("user.preferences.theme"))
        
        # Delete a non-existent value
        self.assertFalse(self.adapter.delete_legacy_value("app.description"))
        
        # Add a language preference to ensure preferences dict isn't empty
        self.adapter.set_legacy_value("user.preferences.language", "en")
        
        # Delete a nested path and check if parent is cleaned up when empty
        self.assertTrue(self.adapter.delete_legacy_value("user.preferences.notifications"))
        self.assertFalse(self.adapter.has_legacy_value("user.preferences.notifications"))
        
        # Check if the preferences dictionary still exists (it should, as we added 'language')
        self.assertTrue(self.adapter.has_legacy_value("user.preferences"))
    
    def test_has_legacy_value(self):
        """Test checking if a legacy configuration path exists."""
        # Test existing paths
        self.assertTrue(self.adapter.has_legacy_value("app.name"))
        self.assertTrue(self.adapter.has_legacy_value("user.preferences.theme"))
        
        # Test non-existent paths
        self.assertFalse(self.adapter.has_legacy_value("app.description"))
        self.assertFalse(self.adapter.has_legacy_value("user.preferences.language"))
    
    def test_get_all_legacy_paths(self):
        """Test getting all legacy configuration paths."""
        # Get all paths
        paths = self.adapter.get_all_legacy_paths()
        
        # Check if all expected paths are present
        self.assertIn("app.name", paths)
        self.assertIn("app.version", paths)
        self.assertIn("user.name", paths)
        self.assertIn("user.email", paths)
        self.assertIn("user.preferences.theme", paths)
        self.assertIn("user.preferences.notifications", paths)
        self.assertIn("settings.auto_start", paths)
        self.assertIn("settings.idle_timeout", paths)
        
        # Get paths with prefix
        user_paths = self.adapter.get_all_legacy_paths("user")
        
        # Check if filtered paths are correct
        self.assertIn("user.name", user_paths)
        self.assertIn("user.email", user_paths)
        self.assertIn("user.preferences.theme", user_paths)
        self.assertIn("user.preferences.notifications", user_paths)
        self.assertNotIn("app.name", user_paths)
        self.assertNotIn("settings.auto_start", user_paths)
    
    def test_translate_legacy_path(self):
        """Test translating a legacy path to a new path."""
        # Test exact matches
        self.assertEqual(self.adapter.translate_legacy_path("app.name"), "application.name")
        self.assertEqual(self.adapter.translate_legacy_path("user"), "user_profile")
        
        # Test prefix matches
        self.assertEqual(self.adapter.translate_legacy_path("user.name"), "user_profile.name")
        self.assertEqual(self.adapter.translate_legacy_path("user.preferences.theme"), "user_profile.preferences.theme")
        
        # Test non-existent paths
        self.assertIsNone(self.adapter.translate_legacy_path("non_existent"))
    
    def test_translate_new_path(self):
        """Test translating a new path to a legacy path."""
        # Test exact matches
        self.assertEqual(self.adapter.translate_new_path("application.name"), "app.name")
        self.assertEqual(self.adapter.translate_new_path("user_profile"), "user")
        
        # Test prefix matches
        self.assertEqual(self.adapter.translate_new_path("user_profile.name"), "user.name")
        self.assertEqual(self.adapter.translate_new_path("user_profile.preferences.theme"), "user.preferences.theme")
        
        # Test non-existent paths
        self.assertIsNone(self.adapter.translate_new_path("non_existent"))
    
    def test_get_path_mappings(self):
        """Test getting all path mappings."""
        mappings = self.adapter.get_path_mappings()
        
        # Check if the mappings match the original
        self.assertEqual(mappings, self.path_mappings)
        
        # Check if the returned mappings are a copy
        mappings["new_path"] = "new_value"
        self.assertNotIn("new_path", self.adapter.get_path_mappings())
    
    def test_migrate_value(self):
        """Test migrating a value from legacy to new configuration."""
        # Test migrating existing values
        self.assertEqual(self.adapter.migrate_value("app.name", "application.name"), "Focus Guard")
        self.assertEqual(self.adapter.migrate_value("user.preferences.theme", "user_profile.preferences.theme"), "dark")
        
        # Test migrating non-existent values
        self.assertIsNone(self.adapter.migrate_value("app.description", "application.description"))
    
    def test_migrate_all(self):
        """Test migrating all values from legacy to new configuration."""
        migrated = self.adapter.migrate_all()
        
        # Check if all mapped paths are migrated
        self.assertEqual(migrated["application.name"], "Focus Guard")
        self.assertEqual(migrated["application.version"], "1.0.0")
        self.assertIn("user_profile", migrated)
        self.assertIn("application.settings", migrated)
        
        # Check if the user profile is correctly migrated
        user_profile = migrated["user_profile"]
        self.assertEqual(user_profile["name"], "Test User")
        self.assertEqual(user_profile["email"], "test@example.com")
        self.assertEqual(user_profile["preferences"]["theme"], "dark")
    
    def test_save_legacy(self):
        """Test saving the legacy configuration."""
        # Modify the configuration
        self.adapter.set_legacy_value("app.name", "New Focus Guard")
        self.adapter.set_legacy_value("app.description", "A focus management tool")
        
        # Save the configuration
        self.assertTrue(self.adapter.save_legacy())
        
        # Load the configuration from file and check if changes are saved
        with open(self.config_file, "r") as f:
            data = json.load(f)
        
        self.assertEqual(data["app"]["name"], "New Focus Guard")
        self.assertEqual(data["app"]["description"], "A focus management tool")
    
    def test_load_legacy(self):
        """Test loading the legacy configuration."""
        # Modify the file directly
        modified_data = {
            "app": {
                "name": "Modified Focus Guard",
                "version": "2.0.0"
            }
        }
        
        with open(self.config_file, "w") as f:
            json.dump(modified_data, f)
        
        # Load the configuration
        self.assertTrue(self.adapter.load_legacy())
        
        # Check if changes are loaded
        self.assertEqual(self.adapter.get_legacy_value("app.name"), "Modified Focus Guard")
        self.assertEqual(self.adapter.get_legacy_value("app.version"), "2.0.0")
        self.assertIsNone(self.adapter.get_legacy_value("user.name"))


class TestCategoryMappingAdapter(unittest.TestCase):
    """Test cases for the CategoryMappingAdapter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = os.path.join(self.temp_dir.name, "legacy_config.json")
        
        # Define test data
        self.test_data = {
            "domains": {
                "facebook.com": {
                    "category": "social",
                    "enabled": True
                },
                "youtube.com": {
                    "category": "entertainment",
                    "enabled": True
                },
                "github.com": {
                    "category": "work",
                    "enabled": False
                }
            }
        }
        
        # Write test data to the file
        with open(self.config_file, "w") as f:
            json.dump(self.test_data, f)
        
        # Define path mappings
        self.path_mappings = {
            "domains": "site_settings.domains"
        }
        
        # Define category enum mapping
        self.category_enum_mapping = {
            "social": 1,  # SOCIAL_MEDIA enum value
            "entertainment": 2,  # ENTERTAINMENT enum value
            "work": 3,  # PRODUCTIVITY enum value
            "unknown": 0  # UNKNOWN enum value
        }
        
        # Create the adapter
        self.adapter = CategoryMappingAdapter(
            legacy_file_path=self.config_file,
            path_mappings=self.path_mappings,
            category_enum_mapping=self.category_enum_mapping
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()
    
    def test_transform_category(self):
        """Test transforming category values."""
        # Test transforming known categories
        self.assertEqual(self.adapter._transform_category("social"), 1)
        self.assertEqual(self.adapter._transform_category("entertainment"), 2)
        self.assertEqual(self.adapter._transform_category("work"), 3)
        
        # Test transforming unknown categories
        self.assertEqual(self.adapter._transform_category("unknown_category"), "unknown_category")
        self.assertEqual(self.adapter._transform_category(123), 123)
    
    def test_migrate_value(self):
        """Test migrating values with category transformation."""
        # Get the domains
        domains = self.adapter.get_legacy_value("domains")
        
        # Migrate the domains
        migrated_domains = self.adapter.migrate_value("domains", "site_settings.domains")
        
        # Check if categories are transformed
        self.assertEqual(migrated_domains["facebook.com"]["category"], 1)
        self.assertEqual(migrated_domains["youtube.com"]["category"], 2)
        self.assertEqual(migrated_domains["github.com"]["category"], 3)
        
        # Check if other values are preserved
        self.assertEqual(migrated_domains["facebook.com"]["enabled"], True)
        self.assertEqual(migrated_domains["youtube.com"]["enabled"], True)
        self.assertEqual(migrated_domains["github.com"]["enabled"], False)


if __name__ == "__main__":
    unittest.main()
