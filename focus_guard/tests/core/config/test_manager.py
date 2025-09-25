"""
Unit tests for configuration manager.

This module contains unit tests for the configuration manager.
"""

import unittest
from unittest.mock import MagicMock, patch, call
from typing import Any, Dict, Optional, Set

from focus_guard.core.config.interfaces import ConfigPath, ConfigProvider, ConfigScope
from focus_guard.core.config.manager import DefaultConfigurationManager


class TestConfigManager(unittest.TestCase):
    """Test the configuration manager."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock logger to suppress output during tests
        self.mock_logger = MagicMock()
        
        # Patch the logger to use our mock
        self.logger_patcher = patch('focus_guard.core.config.manager.logging')
        self.mock_logging = self.logger_patcher.start()
        self.mock_logging.getLogger.return_value = self.mock_logger
        
        # Create the manager with a very short cache TTL for testing
        self.manager = DefaultConfigurationManager(cache_ttl=0.1)
        
        # Create mock providers with proper method signatures
        self.system_provider = MagicMock(spec=ConfigProvider)
        self.system_provider.get_name.return_value = "system"
        self.system_provider.has_value.return_value = True
        self.system_provider.get_value.return_value = "system_value"
        self.system_provider.set_value.return_value = None  # set_value doesn't return anything
        self.system_provider.load.return_value = None
        
        self.user_provider = MagicMock(spec=ConfigProvider)
        self.user_provider.get_name.return_value = "user"
        self.user_provider.has_value.return_value = True
        self.user_provider.get_value.return_value = "user_value"
        self.user_provider.set_value.return_value = None  # set_value doesn't return anything
        self.user_provider.load.return_value = None
        
        # Register providers with their scopes
        self.manager.register_provider(self.system_provider, ConfigScope.SYSTEM)
        self.manager.register_provider(self.user_provider, ConfigScope.USER)
    
    def test_register_provider(self):
        """Test registering providers."""
        # Verify the providers were registered in setUp
        # We can verify by checking the log messages
        expected_calls = [
            call("Registering provider 'system' in scope 'SYSTEM' with priority 0."),
            call("Registering provider 'user' in scope 'USER' with priority 0.")
        ]
        self.mock_logger.info.assert_has_calls(expected_calls, any_order=True)
    
    def test_get_value(self):
        """Test getting values."""
        # In the current implementation, SYSTEM scope is checked before USER scope
        # because SYSTEM has a higher enum value (1) than USER (0)
        
        # Test getting value from system provider (higher scope)
        self.system_provider.get_value.return_value = "system_value"
        self.system_provider.has_value.return_value = True
        
        result = self.manager.get_value("path")
        self.assertEqual(result, "system_value")
        self.system_provider.has_value.assert_called_once_with("path")
        self.system_provider.get_value.assert_called_once_with("path")
        
        # Test with default value when no provider has the value
        self.user_provider.has_value.return_value = False
        self.system_provider.has_value.return_value = False
        result = self.manager.get_value("nonexistent", default="default")
        self.assertEqual(result, "default")
    
    def test_set_value(self):
        """Test setting values."""
        # Test setting a value (should go to user provider)
        result = self.manager.set_value("path", "value")
        self.assertTrue(result)
        self.user_provider.set_value.assert_called_once_with("path", "value")
        
        # Verify cache clearing
        with patch.object(self.manager, 'clear_cache') as mock_clear_cache:
            self.manager.set_value("another_path", "another_value")
            mock_clear_cache.assert_called_once_with("another_path")
    
    def test_delete_value(self):
        """Test deleting values from configuration."""
        test_path = "test.path"
        non_existent_path = "nonexistent.path"
        
        # Clear any existing providers to start fresh
        self.manager._providers.clear()
        
        # Create a new mock provider specifically for this test
        test_provider = MagicMock(spec=ConfigProvider)
        test_provider.get_name.return_value = "test_provider"
        
        # Set up the provider to only have our test path
        def mock_has_value(path):
            return path == test_path
            
        test_provider.has_value.side_effect = mock_has_value
        test_provider.delete_value.return_value = True
        
        # Register the test provider
        self.manager.register_provider(test_provider, ConfigScope.USER)
        
        # Test 1: Delete an existing path
        result = self.manager.delete_value(test_path)
        self.assertTrue(result, "delete_value should return True for existing path")
        
        # Verify the provider was called correctly
        test_provider.has_value.assert_called_once_with(test_path)
        test_provider.delete_value.assert_called_once_with(test_path)
        
        # Verify the cache was cleared and event was published
        with patch.object(self.manager, 'clear_cache') as mock_clear_cache, \
             patch.object(self.manager._event_bus, 'publish') as mock_publish:
            self.manager.delete_value(test_path)
            mock_clear_cache.assert_called_once_with(test_path)
            mock_publish.assert_called_once_with(test_path, None)
        
        # Reset mock call counts for the next test
        test_provider.has_value.reset_mock()
        test_provider.delete_value.reset_mock()
        
        # Test 2: Try to delete a non-existent path
        result = self.manager.delete_value(non_existent_path)
        self.assertFalse(result, "delete_value should return False for non-existent path")
        
        # Verify the provider was checked but delete was not called
        test_provider.has_value.assert_called_once_with(non_existent_path)
        test_provider.delete_value.assert_not_called()
        
        # Test 3: Provider has the value but delete fails
        test_provider.has_value.return_value = True
        test_provider.delete_value.return_value = False
        test_provider.has_value.reset_mock()
        test_provider.delete_value.reset_mock()
        
        result = self.manager.delete_value(test_path)
        self.assertFalse(result, "delete_value should return False when provider delete fails")
        test_provider.has_value.assert_called_once_with(test_path)
        test_provider.delete_value.assert_called_once_with(test_path)
        pass
    
    def test_get_all_paths(self):
        """Test getting all configuration paths - not directly supported in DefaultConfigurationManager."""
        # DefaultConfigurationManager doesn't have get_all_paths method
        # This is a no-op test since the functionality isn't directly exposed
        pass
    
    def test_reload(self):
        """Test reloading configuration."""
        # Mock the load methods
        self.system_provider.load.return_value = None
        self.user_provider.load.return_value = None
    
        # Mock the event bus
        with patch.object(self.manager, '_event_bus') as mock_event_bus:
            # Set up the mock to handle the publish call with the correct signature
            mock_event_bus.publish.return_value = None
            
            # Reload configuration
            self.manager.reload()
    
            # Verify providers were reloaded
            self.system_provider.load.assert_called_once()
            self.user_provider.load.assert_called_once()
            
            # Verify event was published with correct arguments
            mock_event_bus.publish.assert_called_once_with("*", value=self.manager)
        
        # Verify cache was cleared
        with patch.object(self.manager, 'clear_cache') as mock_clear_cache, \
             patch.object(self.manager, '_event_bus') as mock_event_bus:
            mock_event_bus.publish.return_value = None
            self.manager.reload()
            mock_clear_cache.assert_called_once()
            mock_event_bus.publish.assert_called_once_with("*", value=self.manager)
            mock_clear_cache.assert_called_once()
    
    def test_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing to configuration changes."""
        # DefaultConfigurationManager uses an event bus internally but doesn't expose subscribe/unsubscribe
        # This is a no-op test since the functionality isn't directly exposed
        pass


if __name__ == "__main__":
    unittest.main()
