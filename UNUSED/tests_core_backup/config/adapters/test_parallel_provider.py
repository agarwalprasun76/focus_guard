"""
Unit tests for the parallel configuration provider.
"""

import unittest
from unittest.mock import patch, MagicMock, call

from core_v2.config.interfaces import ConfigPath, ConfigProvider, ConfigScope
from core_v2.config.adapters.interfaces import LegacyConfigAdapter
from core_v2.config.adapters.parallel_provider import ParallelConfigProvider


class TestParallelConfigProvider(unittest.TestCase):
    """Test cases for the ParallelConfigProvider class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock objects
        self.mock_new_provider = MagicMock(spec=ConfigProvider)
        self.mock_legacy_adapter = MagicMock(spec=LegacyConfigAdapter)
        
        # Set up return values for the mock objects
        self.mock_new_provider.get_name.return_value = "mock_provider"
        self.mock_new_provider.get_scope.return_value = ConfigScope.USER
        
        # Set up path translations
        self.mock_legacy_adapter.translate_new_path.side_effect = lambda path: f"legacy_{path}" if path else None
        self.mock_legacy_adapter.translate_legacy_path.side_effect = lambda path: path.replace("legacy_", "") if path.startswith("legacy_") else None
        
        # Create the provider
        self.provider = ParallelConfigProvider(
            new_provider=self.mock_new_provider,
            legacy_adapter=self.mock_legacy_adapter,
            write_to_legacy=True,
            write_to_new=True,
            read_legacy_fallback=True
        )
    
    def test_get_name(self):
        """Test getting the provider name."""
        self.assertEqual(self.provider.get_name(), "parallel_mock_provider")
    
    def test_get_value_from_new(self):
        """Test getting a value from the new provider."""
        # Set up the mock to return a value
        self.mock_new_provider.has_value.return_value = True
        self.mock_new_provider.get_value.return_value = "new_value"
        
        # Get the value
        value = self.provider.get_value("test_path")
        
        # Check if the value is correct
        self.assertEqual(value, "new_value")
        
        # Check if the new provider was called
        self.mock_new_provider.has_value.assert_called_once_with("test_path")
        self.mock_new_provider.get_value.assert_called_once_with("test_path", None)
        
        # Check if the legacy adapter was not called
        self.mock_legacy_adapter.has_legacy_value.assert_not_called()
        self.mock_legacy_adapter.get_legacy_value.assert_not_called()
    
    def test_get_value_from_legacy(self):
        """Test getting a value from the legacy adapter."""
        # Set up the mocks
        self.mock_new_provider.has_value.return_value = False
        self.mock_legacy_adapter.has_legacy_value.return_value = True
        self.mock_legacy_adapter.get_legacy_value.return_value = "legacy_value"
        self.mock_legacy_adapter.migrate_value.return_value = "migrated_value"
        
        # Get the value
        value = self.provider.get_value("test_path")
        
        # Check if the value is correct
        self.assertEqual(value, "legacy_value")
        
        # Check if the new provider was called
        self.mock_new_provider.has_value.assert_called_once_with("test_path")
        
        # Check if the legacy adapter was called
        self.mock_legacy_adapter.translate_new_path.assert_called_once_with("test_path")
        self.mock_legacy_adapter.has_legacy_value.assert_called_once_with("legacy_test_path")
        self.mock_legacy_adapter.get_legacy_value.assert_called_once_with("legacy_test_path")
        
        # Check if the value was migrated to the new provider
        self.mock_legacy_adapter.migrate_value.assert_called_once_with("legacy_test_path", "test_path")
        self.mock_new_provider.set_value.assert_called_once_with("test_path", "migrated_value")
    
    def test_get_value_not_found(self):
        """Test getting a value that does not exist."""
        # Set up the mocks
        self.mock_new_provider.has_value.return_value = False
        self.mock_legacy_adapter.has_legacy_value.return_value = False
        
        # Get the value with a default
        value = self.provider.get_value("test_path", "default_value")
        
        # Check if the value is the default
        self.assertEqual(value, "default_value")
    
    def test_set_value(self):
        """Test setting a value."""
        # Set up the mocks
        self.mock_new_provider.set_value.return_value = True
        self.mock_legacy_adapter.set_legacy_value.return_value = True
        
        # Set the value
        result = self.provider.set_value("test_path", "test_value")
        
        # Check if the result is correct
        self.assertTrue(result)
        
        # Check if both providers were called
        self.mock_new_provider.set_value.assert_called_once_with("test_path", "test_value")
        self.mock_legacy_adapter.translate_new_path.assert_called_once_with("test_path")
        self.mock_legacy_adapter.set_legacy_value.assert_called_once_with("legacy_test_path", "test_value")
    
    def test_set_value_new_only(self):
        """Test setting a value with write_to_legacy=False."""
        # Create a provider with write_to_legacy=False
        provider = ParallelConfigProvider(
            new_provider=self.mock_new_provider,
            legacy_adapter=self.mock_legacy_adapter,
            write_to_legacy=False,
            write_to_new=True,
            read_legacy_fallback=True
        )
        
        # Set up the mock
        self.mock_new_provider.set_value.return_value = True
        
        # Set the value
        result = provider.set_value("test_path", "test_value")
        
        # Check if the result is correct
        self.assertTrue(result)
        
        # Check if only the new provider was called
        self.mock_new_provider.set_value.assert_called_once_with("test_path", "test_value")
        self.mock_legacy_adapter.set_legacy_value.assert_not_called()
    
    def test_set_value_legacy_only(self):
        """Test setting a value with write_to_new=False."""
        # Create a provider with write_to_new=False
        provider = ParallelConfigProvider(
            new_provider=self.mock_new_provider,
            legacy_adapter=self.mock_legacy_adapter,
            write_to_legacy=True,
            write_to_new=False,
            read_legacy_fallback=True
        )
        
        # Set up the mock
        self.mock_legacy_adapter.set_legacy_value.return_value = True
        
        # Set the value
        result = provider.set_value("test_path", "test_value")
        
        # Check if the result is correct
        self.assertTrue(result)
        
        # Check if only the legacy adapter was called
        self.mock_new_provider.set_value.assert_not_called()
        self.mock_legacy_adapter.translate_new_path.assert_called_once_with("test_path")
        self.mock_legacy_adapter.set_legacy_value.assert_called_once_with("legacy_test_path", "test_value")
    
    def test_delete_value(self):
        """Test deleting a value."""
        # Set up the mocks
        self.mock_new_provider.delete_value.return_value = True
        self.mock_legacy_adapter.delete_legacy_value.return_value = True
        
        # Delete the value
        result = self.provider.delete_value("test_path")
        
        # Check if the result is correct
        self.assertTrue(result)
        
        # Check if both providers were called
        self.mock_new_provider.delete_value.assert_called_once_with("test_path")
        self.mock_legacy_adapter.translate_new_path.assert_called_once_with("test_path")
        self.mock_legacy_adapter.delete_legacy_value.assert_called_once_with("legacy_test_path")
    
    def test_has_value_in_new(self):
        """Test checking if a value exists in the new provider."""
        # Set up the mock
        self.mock_new_provider.has_value.return_value = True
        
        # Check if the value exists
        result = self.provider.has_value("test_path")
        
        # Check if the result is correct
        self.assertTrue(result)
        
        # Check if only the new provider was called
        self.mock_new_provider.has_value.assert_called_once_with("test_path")
        self.mock_legacy_adapter.has_legacy_value.assert_not_called()
    
    def test_has_value_in_legacy(self):
        """Test checking if a value exists in the legacy adapter."""
        # Set up the mocks
        self.mock_new_provider.has_value.return_value = False
        self.mock_legacy_adapter.has_legacy_value.return_value = True
        
        # Check if the value exists
        result = self.provider.has_value("test_path")
        
        # Check if the result is correct
        self.assertTrue(result)
        
        # Check if both providers were called
        self.mock_new_provider.has_value.assert_called_once_with("test_path")
        self.mock_legacy_adapter.translate_new_path.assert_called_once_with("test_path")
        self.mock_legacy_adapter.has_legacy_value.assert_called_once_with("legacy_test_path")
    
    def test_has_value_not_found(self):
        """Test checking if a value exists when it does not."""
        # Set up the mocks
        self.mock_new_provider.has_value.return_value = False
        self.mock_legacy_adapter.has_legacy_value.return_value = False
        
        # Check if the value exists
        result = self.provider.has_value("test_path")
        
        # Check if the result is correct
        self.assertFalse(result)
    
    def test_get_all_paths(self):
        """Test getting all configuration paths."""
        # Set up the mocks
        self.mock_new_provider.get_all_paths.return_value = {"new_path1", "new_path2"}
        self.mock_legacy_adapter.get_all_legacy_paths.return_value = {"legacy_path1", "legacy_path2"}
        self.mock_legacy_adapter.translate_legacy_path.side_effect = lambda path: path.replace("legacy_", "")
        
        # Get all paths
        paths = self.provider.get_all_paths()
        
        # Check if the paths are correct
        self.assertEqual(paths, {"new_path1", "new_path2", "path1", "path2"})
        
        # Check if both providers were called
        self.mock_new_provider.get_all_paths.assert_called_once_with(None)
        self.mock_legacy_adapter.get_all_legacy_paths.assert_called_once_with(None)
    
    def test_get_all_paths_with_prefix(self):
        """Test getting all configuration paths with a prefix."""
        # Set up the mocks
        self.mock_new_provider.get_all_paths.return_value = {"prefix.path1", "prefix.path2"}
        self.mock_legacy_adapter.get_all_legacy_paths.return_value = {"legacy_prefix.path3", "legacy_other.path"}
        self.mock_legacy_adapter.translate_legacy_path.side_effect = lambda path: path.replace("legacy_", "")
        
        # Get paths with prefix
        paths = self.provider.get_all_paths("prefix")
        
        # Check if the paths are correct
        self.assertEqual(paths, {"prefix.path1", "prefix.path2", "prefix.path3"})
    
    def test_get_scope(self):
        """Test getting the provider scope."""
        # Get the scope
        scope = self.provider.get_scope()
        
        # Check if the scope is correct
        self.assertEqual(scope, ConfigScope.USER)
        
        # Check if the new provider was called
        self.mock_new_provider.get_scope.assert_called_once()
    
    def test_load(self):
        """Test loading the configuration data."""
        # Set up the mocks
        self.mock_new_provider.load.return_value = True
        self.mock_legacy_adapter.load_legacy.return_value = True
        
        # Load the configuration
        result = self.provider.load()
        
        # Check if the result is correct
        self.assertTrue(result)
        
        # Check if both providers were called
        self.mock_new_provider.load.assert_called_once()
        self.mock_legacy_adapter.load_legacy.assert_called_once()
    
    def test_save(self):
        """Test saving the configuration data."""
        # Set up the mocks
        self.mock_new_provider.save.return_value = True
        self.mock_legacy_adapter.save_legacy.return_value = True
        
        # Save the configuration
        result = self.provider.save()
        
        # Check if the result is correct
        self.assertTrue(result)
        
        # Check if both providers were called
        self.mock_new_provider.save.assert_called_once()
        self.mock_legacy_adapter.save_legacy.assert_called_once()
    
    def test_clear(self):
        """Test clearing the configuration data."""
        # Set up the mock
        self.mock_new_provider.clear.return_value = True
        
        # Clear the configuration
        result = self.provider.clear()
        
        # Check if the result is correct
        self.assertTrue(result)
        
        # Check if only the new provider was called
        self.mock_new_provider.clear.assert_called_once()
        
        # Check if the legacy adapter was not called
        # We don't clear the legacy system to avoid data loss
        self.mock_legacy_adapter.assert_not_called()
    
    def test_migrate_all_to_new(self):
        """Test migrating all values from legacy to new."""
        # Set up the mocks
        self.mock_legacy_adapter.migrate_all.return_value = {
            "path1": "value1",
            "path2": "value2"
        }
        self.mock_new_provider.set_value.return_value = True
        self.mock_new_provider.save.return_value = True
        
        # Migrate all values
        result = self.provider.migrate_all_to_new()
        
        # Check if the result is correct
        self.assertTrue(result)
        
        # Check if the legacy adapter was called
        self.mock_legacy_adapter.migrate_all.assert_called_once()
        
        # Check if the new provider was called for each value
        self.mock_new_provider.set_value.assert_has_calls([
            call("path1", "value1"),
            call("path2", "value2")
        ], any_order=True)
        
        # Check if the new provider was saved
        self.mock_new_provider.save.assert_called_once()
    
    def test_migrate_all_to_new_disabled(self):
        """Test migrating all values with write_to_new=False."""
        # Create a provider with write_to_new=False
        provider = ParallelConfigProvider(
            new_provider=self.mock_new_provider,
            legacy_adapter=self.mock_legacy_adapter,
            write_to_legacy=True,
            write_to_new=False,
            read_legacy_fallback=True
        )
        
        # Migrate all values
        result = provider.migrate_all_to_new()
        
        # Check if the result is correct
        self.assertFalse(result)
        
        # Check if the legacy adapter was not called
        self.mock_legacy_adapter.migrate_all.assert_not_called()
        
        # Check if the new provider was not called
        self.mock_new_provider.set_value.assert_not_called()
        self.mock_new_provider.save.assert_not_called()
    
    def test_get_new_provider(self):
        """Test getting the new provider."""
        # Get the new provider
        provider = self.provider.get_new_provider()
        
        # Check if the provider is correct
        self.assertEqual(provider, self.mock_new_provider)
    
    def test_get_legacy_adapter(self):
        """Test getting the legacy adapter."""
        # Get the legacy adapter
        adapter = self.provider.get_legacy_adapter()
        
        # Check if the adapter is correct
        self.assertEqual(adapter, self.mock_legacy_adapter)


if __name__ == "__main__":
    unittest.main()
