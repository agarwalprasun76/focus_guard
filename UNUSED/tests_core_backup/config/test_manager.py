"""
Unit tests for configuration manager.

This module contains unit tests for the configuration manager.
"""

import unittest
from unittest.mock import MagicMock, patch
from typing import Any, Dict, Optional, Set

from core_v2.config.interfaces import ConfigPath, ConfigProvider, ConfigScope
from core_v2.config.manager import DefaultConfigurationManager


class TestConfigManager(unittest.TestCase):
    """Test cases for configuration manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock providers
        self.system_provider = MagicMock(spec=ConfigProvider)
        self.system_provider.get_name.return_value = "system"
        self.system_provider.get_scope.return_value = ConfigScope.SYSTEM
        
        self.user_provider = MagicMock(spec=ConfigProvider)
        self.user_provider.get_name.return_value = "user"
        self.user_provider.get_scope.return_value = ConfigScope.USER
        
        # Create the manager
        self.manager = DefaultConfigurationManager()
    
    def test_register_provider(self):
        """Test registering providers."""
        # Register providers
        self.assertTrue(self.manager.register_provider(self.system_provider))
        self.assertTrue(self.manager.register_provider(self.user_provider))
        
        # Try to register the same provider again
        self.assertFalse(self.manager.register_provider(self.system_provider))
    
    def test_unregister_provider(self):
        """Test unregistering providers."""
        # Register providers
        self.manager.register_provider(self.system_provider)
        self.manager.register_provider(self.user_provider)
        
        # Unregister providers
        self.assertTrue(self.manager.unregister_provider("system"))
        self.assertTrue(self.manager.unregister_provider("user"))
        
        # Try to unregister a non-existent provider
        self.assertFalse(self.manager.unregister_provider("nonexistent"))
    
    def test_get_provider(self):
        """Test getting providers."""
        # Register providers
        self.manager.register_provider(self.system_provider)
        self.manager.register_provider(self.user_provider)
        
        # Get providers
        self.assertEqual(self.manager.get_provider("system"), self.system_provider)
        self.assertEqual(self.manager.get_provider("user"), self.user_provider)
        self.assertIsNone(self.manager.get_provider("nonexistent"))
    
    def test_get_providers_by_scope(self):
        """Test getting providers by scope."""
        # Register providers
        self.manager.register_provider(self.system_provider)
        self.manager.register_provider(self.user_provider)
        
        # Get providers by scope
        system_providers = self.manager.get_providers_by_scope(ConfigScope.SYSTEM)
        user_providers = self.manager.get_providers_by_scope(ConfigScope.USER)
        
        self.assertEqual(len(system_providers), 1)
        self.assertEqual(len(user_providers), 1)
        self.assertEqual(system_providers[0], self.system_provider)
        self.assertEqual(user_providers[0], self.user_provider)
    
    def test_get_value(self):
        """Test getting values."""
        # Set up provider return values
        self.system_provider.has_value.return_value = True
        self.system_provider.get_value.return_value = "system_value"
        
        self.user_provider.has_value.return_value = True
        self.user_provider.get_value.return_value = "user_value"
        
        # Register providers
        self.manager.register_provider(self.system_provider)
        self.manager.register_provider(self.user_provider)
        
        # Get values
        # User provider should take precedence over system provider
        self.assertEqual(self.manager.get_value("path"), "user_value")
        
        # Test with scope
        self.assertEqual(self.manager.get_value("path", scope=ConfigScope.SYSTEM), "system_value")
        self.assertEqual(self.manager.get_value("path", scope=ConfigScope.USER), "user_value")
        
        # Test with default value
        self.user_provider.has_value.return_value = False
        self.system_provider.has_value.return_value = False
        self.assertEqual(self.manager.get_value("path", default="default"), "default")
    
    def test_set_value(self):
        """Test setting values."""
        # Set up provider return values
        self.user_provider.set_value.return_value = True
        
        # Register providers
        self.manager.register_provider(self.system_provider)
        self.manager.register_provider(self.user_provider)
        
        # Set values
        self.assertTrue(self.manager.set_value("path", "value"))
        self.user_provider.set_value.assert_called_once_with("path", "value")
        
        # Test with scope
        self.manager.set_value("path", "value", scope=ConfigScope.SYSTEM)
        self.system_provider.set_value.assert_called_once_with("path", "value")
    
    def test_delete_value(self):
        """Test deleting values."""
        # Set up provider return values
        self.user_provider.delete_value.return_value = True
        
        # Register providers
        self.manager.register_provider(self.system_provider)
        self.manager.register_provider(self.user_provider)
        
        # Delete values
        self.assertTrue(self.manager.delete_value("path"))
        self.user_provider.delete_value.assert_called_once_with("path")
        
        # Test with scope
        self.manager.delete_value("path", scope=ConfigScope.SYSTEM)
        self.system_provider.delete_value.assert_called_once_with("path")
    
    def test_has_value(self):
        """Test checking if values exist."""
        # Set up provider return values
        self.system_provider.has_value.return_value = True
        self.user_provider.has_value.return_value = False
        
        # Register providers
        self.manager.register_provider(self.system_provider)
        self.manager.register_provider(self.user_provider)
        
        # Check if values exist
        self.assertTrue(self.manager.has_value("path"))
        
        # Test with scope
        self.assertTrue(self.manager.has_value("path", scope=ConfigScope.SYSTEM))
        self.assertFalse(self.manager.has_value("path", scope=ConfigScope.USER))
    
    def test_get_all_paths(self):
        """Test getting all paths."""
        # Set up provider return values
        self.system_provider.get_all_paths.return_value = {"path1", "path2"}
        self.user_provider.get_all_paths.return_value = {"path2", "path3"}
        
        # Register providers
        self.manager.register_provider(self.system_provider)
        self.manager.register_provider(self.user_provider)
        
        # Get all paths
        paths = self.manager.get_all_paths()
        self.assertEqual(paths, {"path1", "path2", "path3"})
        
        # Test with scope
        self.assertEqual(self.manager.get_all_paths(scope=ConfigScope.SYSTEM), {"path1", "path2"})
        self.assertEqual(self.manager.get_all_paths(scope=ConfigScope.USER), {"path2", "path3"})
        
        # Test with prefix
        self.system_provider.get_all_paths.return_value = {"prefix/path1", "other/path2"}
        self.user_provider.get_all_paths.return_value = {"prefix/path3"}
        
        self.assertEqual(
            self.manager.get_all_paths(prefix="prefix"),
            {"prefix/path1", "prefix/path3"}
        )
    
    def test_save(self):
        """Test saving configuration."""
        # Set up provider return values
        self.system_provider.save.return_value = True
        self.user_provider.save.return_value = True
        
        # Register providers
        self.manager.register_provider(self.system_provider)
        self.manager.register_provider(self.user_provider)
        
        # Save configuration
        self.assertTrue(self.manager.save())
        self.system_provider.save.assert_called_once()
        self.user_provider.save.assert_called_once()
        
        # Test with scope
        self.manager.save(scope=ConfigScope.SYSTEM)
        self.assertEqual(self.system_provider.save.call_count, 2)
        self.assertEqual(self.user_provider.save.call_count, 1)
    
    def test_reload(self):
        """Test reloading configuration."""
        # Set up provider return values
        self.system_provider.load.return_value = True
        self.user_provider.load.return_value = True
        
        # Register providers
        self.manager.register_provider(self.system_provider)
        self.manager.register_provider(self.user_provider)
        
        # Reload configuration
        self.assertTrue(self.manager.reload())
        self.system_provider.load.assert_called_once()
        self.user_provider.load.assert_called_once()
        
        # Test with scope
        self.manager.reload(scope=ConfigScope.SYSTEM)
        self.assertEqual(self.system_provider.load.call_count, 2)
        self.assertEqual(self.user_provider.load.call_count, 1)
    
    def test_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing to configuration changes."""
        # Create a mock callback
        callback = MagicMock()
        
        # Subscribe to changes
        self.manager.subscribe("path", callback)
        
        # Set a value to trigger the callback
        self.manager.register_provider(self.user_provider)
        self.user_provider.has_value.return_value = True
        self.user_provider.get_value.return_value = "value"
        
        self.manager.set_value("path", "value")
        callback.assert_called_once_with("path", "value")
        
        # Unsubscribe from changes
        self.manager.unsubscribe("path", callback)
        
        # Set a value again, callback should not be called
        callback.reset_mock()
        self.manager.set_value("path", "new_value")
        callback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
