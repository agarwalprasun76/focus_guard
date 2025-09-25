"""
Unit tests for the AlertSystem core logic.

This module contains tests for the AlertSystem class and related functionality.
"""

import unittest
import os
import json
import tempfile
import shutil
import time
from unittest.mock import patch, MagicMock, call, ANY
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from core_v2.alert.models import AlertInfo, AlertLevel, AlertHistoryEntry
from core_v2.alert.alert_system import AlertSystem
from core_v2.alert.providers.base import AlertProvider
from core_v2.alert.config import AlertConfigManager, AlertConfigKeys
from core_v2.config.interfaces import ConfigurationManager


class MockAlertProvider(AlertProvider):
    """Mock alert provider for testing."""
    
    def __init__(self, config=None, name=None):
        super().__init__(config or {})
        self.name = name or self.__class__.__name__
        self.alerts = []
        self.enabled = True
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update provider configuration.
        
        Args:
            config: New configuration values
        """
        self.config.update(config)
        if 'enabled' in config:
            self.enabled = config['enabled']
    
    def send_alert(self, alert_info: AlertInfo) -> bool:
        """Record the alert and return success."""
        self.alerts.append(alert_info)
        return True
    
    def get_alerts(self) -> List[AlertInfo]:
        """Get all sent alerts."""
        return self.alerts
    
    def clear(self) -> None:
        """Clear recorded alerts."""
        self.alerts = []


class MockConfigManager(ConfigurationManager):
    """Mock configuration manager for testing."""
    
    def __init__(self):
        super().__init__()
        self.config = {
            f"{AlertConfigKeys.ALERTS_ROOT}.{AlertConfigKeys.HISTORY_SIZE}": 100,
            f"{AlertConfigKeys.ALERTS_ROOT}.{AlertConfigKeys.COOLDOWN_PERIOD}": 30,
            f"{AlertConfigKeys.ALERTS_ROOT}.{AlertConfigKeys.ENABLED}": True,
            f"{AlertConfigKeys.ALERTS_ROOT}.{AlertConfigKeys.PROVIDERS_ROOT}": {
                AlertConfigKeys.POPUP_PROVIDER: {"enabled": True},
                AlertConfigKeys.SOUND_PROVIDER: {"enabled": True},
                AlertConfigKeys.BLOCKING_PROVIDER: {"enabled": True},
                "email": {"enabled": False},
                "webhook": {"enabled": False},
                "app": {"enabled": False}
            }
        }
        self.subscribers = {}
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        # Handle nested keys
        if key.startswith(f"{AlertConfigKeys.ALERTS_ROOT}."):
            parts = key.split('.')
            value = self.config
            for part in parts[1:]:  # Skip the 'alerts' part
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value
        return self.config.get(key, default)
    
    def set_config_value(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self.config[key] = value
        if key in self.subscribers:
            for callback in self.subscribers[key]:
                callback(key, value)
    
    def subscribe(self, key: str, callback: callable) -> callable:
        """Subscribe to configuration changes."""
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(callback)
        return lambda: self.subscribers[key].remove(callback)
    
    def get_section(self, section_name: str) -> Dict[str, Any]:
        """Get a configuration section."""
        return self.config.get(section_name, {})
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value (alias for get_config_value)."""
        return self.get_config_value(key, default)
    
    def set_value(self, key: str, value: Any) -> None:
        """Set a configuration value (alias for set_config_value)."""
        self.set_config_value(key, value)
    
    def register_provider(self, provider: Any) -> None:
        """Register a configuration provider."""
        pass  # Not needed for testing
    
    def register_schema(self, schema: Any) -> None:
        """Register a configuration schema."""
        pass  # Not needed for testing
    
    def reload(self) -> None:
        """Reload configuration from source."""
        pass  # Not needed for testing
    
    def save(self) -> None:
        """Save configuration to persistent storage."""
        pass  # Not needed for testing
    
    def unsubscribe(self, callback: callable) -> None:
        """Unsubscribe from configuration changes."""
        for key in self.subscribers:
            if callback in self.subscribers[key]:
                self.subscribers[key].remove(callback)
    
    # Alias for test compatibility
    get = get_config_value
    set = set_config_value


class TestAlertSystem(unittest.TestCase):
    """Tests for the AlertSystem class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for alert history
        self.temp_dir = tempfile.mkdtemp()
        self.history_file = os.path.join(self.temp_dir, "alert_history.json")
        
        # Create mock providers
        self.popup_provider = MockAlertProvider({"enabled": True}, "popup")
        self.sound_provider = MockAlertProvider({"enabled": True}, "sound")
        self.blocking_provider = MockAlertProvider({"enabled": True}, "blocking")
        
        # Create mock config manager
        self.config_manager = MockConfigManager()
        
        # Create alert system
        self.alert_system = AlertSystem(
            history_file=self.history_file,
            config_manager=self.config_manager
        )
        
        # Replace providers with mocks
        self.alert_system.providers = {
            "popup": self.popup_provider,
            "sound": self.sound_provider,
            "blocking": self.blocking_provider
        }
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test alert system initialization."""
        # Check that providers are initialized
        self.assertIn(AlertConfigKeys.POPUP_PROVIDER, self.alert_system.providers)
        self.assertIn(AlertConfigKeys.SOUND_PROVIDER, self.alert_system.providers)
        self.assertIn(AlertConfigKeys.BLOCKING_PROVIDER, self.alert_system.providers)
        
        # Check that history file is set
        self.assertEqual(self.alert_system.history_path, self.history_file)
        self.assertEqual(self.alert_system.max_history_size, 100)
        # Default cooldown period is 60 seconds
        self.assertEqual(self.alert_system.cooldown_period, 60)
        
        # Verify providers are properly configured
        self.assertTrue(self.alert_system.providers[AlertConfigKeys.POPUP_PROVIDER].enabled)
        self.assertTrue(self.alert_system.providers[AlertConfigKeys.SOUND_PROVIDER].enabled)
        self.assertTrue(self.alert_system.providers[AlertConfigKeys.BLOCKING_PROVIDER].enabled)
    
    def test_send_alert(self):
        """Test sending an alert."""
        # Clear the alert history first
        self.alert_system.alert_history = []
        
        # Create alert info
        test_timestamp = datetime.now()
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=test_timestamp,
            window_title="Test Window",
            pid=12345
        )
        
        # Send alert
        result = self.alert_system.send_alert(alert_info)
        self.assertTrue(result)
        
        # Check that alert was sent to all providers
        self.assertEqual(len(self.popup_provider.get_alerts()), 1)
        self.assertEqual(len(self.sound_provider.get_alerts()), 1)
        self.assertEqual(len(self.blocking_provider.get_alerts()), 1)
        
        # Verify alert content in providers
        for provider in [self.popup_provider, self.sound_provider, self.blocking_provider]:
            sent_alert = provider.get_alerts()[0]
            self.assertEqual(sent_alert.app_name, "TestApp")
            self.assertEqual(sent_alert.message, "Test message")
            self.assertEqual(sent_alert.level, AlertLevel.WARNING)
            self.assertEqual(sent_alert.window_title, "Test Window")
            self.assertEqual(sent_alert.pid, 12345)
        
        # Check that alert was added to history
        self.assertEqual(len(self.alert_system.alert_history), 1)
        history_entry = self.alert_system.alert_history[0]
        self.assertEqual(history_entry.alert_info.message, "Test message")
        self.assertEqual(history_entry.alert_info.app_name, "TestApp")
        self.assertEqual(history_entry.alert_info.level, AlertLevel.WARNING)
        self.assertFalse(history_entry.acknowledged)
        self.assertIsNone(history_entry.acknowledged_time)
    
    def test_send_alert_with_cooldown(self):
        """Test sending alerts with cooldown period."""
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=datetime.now()
        )
        
        # Send first alert (should work)
        result1 = self.alert_system.send_alert(alert_info)
        self.assertTrue(result1)
        
        # Send second alert immediately (should be blocked by cooldown)
        result2 = self.alert_system.send_alert(alert_info)
        self.assertFalse(result2)
        
        # Check that providers only received one alert
        self.assertEqual(len(self.popup_provider.get_alerts()), 1)
        
        # Reset cooldown timer
        self.alert_system.reset_cooldown(alert_info.app_name)
        
        # Send third alert (should work after reset)
        result3 = self.alert_system.send_alert(alert_info)
        self.assertTrue(result3)
        
        # Check that providers received second alert
        self.assertEqual(len(self.popup_provider.get_alerts()), 2)
        
        # Test cooldown with different app names
        other_alert = AlertInfo(
            app_name="OtherApp",
            message="Other message",
            level=AlertLevel.WARNING,
            timestamp=datetime.now()
        )
        
        # Should work since it's a different app
        result4 = self.alert_system.send_alert(other_alert)
        self.assertTrue(result4)
        self.assertEqual(len(self.popup_provider.get_alerts()), 3)
    
    def test_get_provider(self):
        """Test getting a provider."""
        # Test getting existing providers
        provider = self.alert_system.get_provider(AlertConfigKeys.POPUP_PROVIDER)
        self.assertEqual(provider, self.popup_provider)
        
        provider = self.alert_system.get_provider(AlertConfigKeys.SOUND_PROVIDER)
        self.assertEqual(provider, self.sound_provider)
        
        provider = self.alert_system.get_provider(AlertConfigKeys.BLOCKING_PROVIDER)
        self.assertEqual(provider, self.blocking_provider)
        
        # Test getting non-existent provider
        with self.assertRaises(KeyError):
            self.alert_system.get_provider("nonexistent")
    
    def test_add_provider(self):
        """Test adding alert providers."""
        # Test adding a new provider with valid name
        test_provider = MockAlertProvider({"enabled": True}, "test")
        self.alert_system.add_provider("test_provider", test_provider)
        self.assertIn("test_provider", self.alert_system.providers)
        self.assertEqual(self.alert_system.providers["test_provider"].enabled, True)
        
        # Test adding a duplicate provider (should replace existing)
        # First, verify the initial state of the popup provider
        self.assertTrue(self.alert_system.providers["popup"].enabled)
        
        # Create a new popup provider with enabled=False
        new_popup_provider = MockAlertProvider({"enabled": False}, "popup")
        
        # Replace the existing popup provider
        self.alert_system.add_provider("popup", new_popup_provider)
        
        # Verify the provider was replaced and has the correct enabled state
        self.assertIs(self.alert_system.providers["popup"], new_popup_provider)
        self.assertFalse(self.alert_system.providers["popup"].enabled)
        
        # Test adding a provider with invalid name (empty string)
        with self.assertRaises(ValueError):
            self.alert_system.add_provider("", MockAlertProvider({}, "invalid"))
            
        # Test adding a provider with invalid name (None)
        with self.assertRaises(ValueError):
            self.alert_system.add_provider(None, MockAlertProvider({}, "invalid"))
        
        # Test adding a None provider
        with self.assertRaises(ValueError):
            self.alert_system.add_provider("invalid_provider", None)
        
    def test_remove_provider(self):
        """Test removing a provider."""
        # Remove provider
        result = self.alert_system.remove_provider("popup")
        self.assertTrue(result)
        self.assertNotIn("popup", self.alert_system.providers)
        
        # Remove non-existent provider
        result = self.alert_system.remove_provider("nonexistent")
        self.assertFalse(result)
    
    def test_enable_disable_providers(self):
        """Test enabling and disabling providers."""
        # Disable providers
        self.alert_system.enable_providers(False)
        self.assertFalse(self.popup_provider.enabled)
        self.assertFalse(self.sound_provider.enabled)
        self.assertFalse(self.blocking_provider.enabled)
        
        # Enable providers
        self.alert_system.enable_providers(True)
        self.assertTrue(self.popup_provider.enabled)
        self.assertTrue(self.sound_provider.enabled)
        self.assertTrue(self.blocking_provider.enabled)
    
    def test_add_alert_to_history(self):
        """Test adding an alert to history."""
        # Clear the alert history first
        self.alert_system.alert_history = []
        
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=datetime.now(),
            window_title="Test Window",
            window_url="http://example.com"
        )
        
        # Add to history
        self.alert_system._add_alert_to_history(alert_info)
        
        # Check that alert was added to history
        self.assertEqual(len(self.alert_system.alert_history), 1)
        self.assertEqual(self.alert_system.alert_history[0].alert_info.message, "Test message")
        self.assertEqual(self.alert_system.alert_history[0].alert_info.app_name, "TestApp")
        self.assertEqual(self.alert_system.alert_history[0].alert_info.level, AlertLevel.WARNING)
        self.assertEqual(self.alert_system.alert_history[0].alert_info.window_title, "Test Window")
        self.assertEqual(self.alert_system.alert_history[0].alert_info.window_url, "http://example.com")
    
    def test_history_size_limit(self):
        """Test history size limit."""
        # Set small history size
        self.alert_system.max_history_size = 3
        
        # Add multiple alerts
        for i in range(5):
            alert_info = AlertInfo(
                app_name="TestApp",
                message=f"Test message {i}",
                level=AlertLevel.WARNING,
                timestamp=datetime.now()
            )
            self.alert_system._add_alert_to_history(alert_info)
        
        # Check that history size is limited
        self.assertEqual(len(self.alert_system.alert_history), 3)
        
        # Check that oldest entries were removed
        self.assertEqual(self.alert_system.alert_history[0].alert_info.message, "Test message 2")
        self.assertEqual(self.alert_system.alert_history[1].alert_info.message, "Test message 3")
        self.assertEqual(self.alert_system.alert_history[2].alert_info.message, "Test message 4")
    
    def test_save_load_history(self):
        """Test saving and loading alert history."""
        # Clear the alert history first
        self.alert_system.alert_history = []
        
        # Add some alerts to history with unique timestamps
        test_timestamps = [datetime(2023, 1, 1, i+1) for i in range(3)]
        alerts = []
        for i in range(3):
            alert_info = AlertInfo(
                app_name=f"TestApp{i}",  # Make app names unique
                message=f"Test message {i}",
                level=AlertLevel.WARNING,
                timestamp=test_timestamps[i]
            )
            alerts.append(alert_info)
            self.alert_system._add_alert_to_history(alert_info)
        
        # Save history
        self.alert_system._save_history()
        
        # Create a new alert system with the same history file
        new_system = AlertSystem(
            history_file=self.history_file,
            config_manager=self.config_manager
        )
        
        # Clear any existing history in the new system
        new_system.alert_history = []
        
        # Load history
        new_system._load_history()
        
        # Check that the history was loaded correctly
        self.assertEqual(len(new_system.alert_history), len(alerts))
        
        # Verify each alert was loaded correctly
        for i, alert_info in enumerate(alerts):
            loaded_entry = new_system.alert_history[i]
            self.assertEqual(loaded_entry.alert_info.message, alert_info.message)
            self.assertEqual(loaded_entry.alert_info.app_name, alert_info.app_name)
            self.assertEqual(loaded_entry.alert_info.level, alert_info.level)
            self.assertEqual(loaded_entry.timestamp, alert_info.timestamp)
    
    def test_config_subscription(self):
        """Test configuration subscription."""
        # Get the popup provider that was added in setup
        popup_provider = self.alert_system.providers.get("popup")
        self.assertIsNotNone(popup_provider, "Popup provider not found in test setup")
        
        # Verify initial state
        self.assertTrue(popup_provider.enabled, "Popup provider should be enabled by default")
        
        # Test 1: Update just the enabled state
        self.alert_system._on_provider_config_changed("popup", {"enabled": False})
        self.assertFalse(popup_provider.enabled, "Popup provider should be disabled after config update")
        
        # Test 2: Update with full config
        self.alert_system._on_provider_config_changed("popup", {
            "enabled": True,
            "popup_duration": 15,
            "overlay_on_distraction": True
        })
        self.assertTrue(popup_provider.enabled, "Popup provider should be re-enabled after config update")
        
        # Test 3: Update just a boolean value
        self.alert_system._on_provider_config_changed("popup", False)
        self.assertFalse(popup_provider.enabled, "Popup provider should be disabled with direct boolean update")
        
        # Test 4: Update with invalid provider (should not raise)
        self.alert_system._on_provider_config_changed("nonexistent", {"enabled": True})
    
    def test_get_alert_history(self):
        """Test getting alert history."""
        # Clear the alert history first
        self.alert_system.alert_history = []
        
        # Add some alerts to history
        for i in range(3):
            alert_info = AlertInfo(
                app_name="TestApp",
                message=f"Test message {i}",
                level=AlertLevel.WARNING,
                timestamp=datetime.now()
            )
            self.alert_system._add_alert_to_history(alert_info)
        
        # Get history
        history = self.alert_system.get_alert_history()
        self.assertEqual(len(history), 3)
        
        # Check history entries
        for i in range(3):
            self.assertEqual(history[i].alert_info.message, f"Test message {i}")
            self.assertEqual(history[i].alert_info.app_name, "TestApp")
    
    def test_clear_alert_history(self):
        """Test clearing alert history."""
        # Add some alerts to history
        for i in range(3):
            alert_info = AlertInfo(
                app_name="TestApp",
                message=f"Test message {i}",
                level=AlertLevel.WARNING,
                timestamp=datetime.now()
            )
            self.alert_system._add_alert_to_history(alert_info)
        
        # Clear history
        self.alert_system.clear_alert_history()
        self.assertEqual(len(self.alert_system.alert_history), 0)
        
        # Check that history file was updated
        self.assertTrue(os.path.exists(self.history_file))
        with open(self.history_file, "r") as f:
            data = json.load(f)
            self.assertEqual(len(data), 0)


class TestAlertConfigManager(unittest.TestCase):
    """Tests for the AlertConfigManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.config_manager = MockConfigManager()
        self.alert_config = AlertConfigManager(self.config_manager)
    
    def test_get_alert_history_max_size(self):
        """Test getting alert history max size."""
        # Test default value (from mock config in setup)
        self.assertEqual(self.alert_config.get_alert_history_max_size(), 100)
        
        # Test custom value
        self.config_manager.set("alert_history_max_size", 200)
        # Clear the cache to force a fresh read
        if hasattr(self.alert_config, '_history_size'):
            delattr(self.alert_config, '_history_size')
        self.assertEqual(self.alert_config.get_alert_history_max_size(), 200)
        
        # Test invalid value (should use default)
        self.config_manager.set("alert_history_max_size", -1)
        if hasattr(self.alert_config, '_history_size'):
            delattr(self.alert_config, '_history_size')
        self.assertEqual(self.alert_config.get_alert_history_max_size(), 100)  # Should return default
    
    def test_get_cooldown_period(self):
        """Test getting alert cooldown period."""
        # Test default value (60 seconds from implementation)
        self.assertEqual(self.alert_config.get_cooldown_period(), 60)
        
        # Test custom value
        self.config_manager.set("cooldown_period", 30)
        # Clear the cache to force a fresh read
        if hasattr(self.alert_config, '_cooldown_period'):
            delattr(self.alert_config, '_cooldown_period')
        self.assertEqual(self.alert_config.get_cooldown_period(), 30)
        
        # Test invalid value (should use default)
        self.config_manager.set("cooldown_period", -1)
        if hasattr(self.alert_config, '_cooldown_period'):
            delattr(self.alert_config, '_cooldown_period')
        self.assertEqual(self.alert_config.get_cooldown_period(), 60)  # Should return default
    
    def test_is_provider_enabled(self):
        """Test checking if a specific provider is enabled."""
        # Test enabled provider (popup is enabled in our mock config)
        self.config_manager.set("providers_enabled", {"popup": True, "email": False})
        self.assertTrue(self.alert_config.is_provider_enabled("popup"))
        
        # Test disabled provider
        self.assertFalse(self.alert_config.is_provider_enabled("email"))
        
        # Test non-existent provider (should default to disabled)
        self.assertFalse(self.alert_config.is_provider_enabled("nonexistent"))
    
    def test_get_provider_config(self):
        """Test getting provider configuration."""
        # Setup mock config
        self.config_manager.set("providers_default_config", {"popup": {"enabled": True, "sound": True}})
        
        # Test existing provider
        config = self.alert_config.get_provider_config("popup")
        self.assertIsNotNone(config)
        self.assertTrue(config.get("enabled", False))
        
        # Test with default config for non-existent provider
        default_config = {"enabled": True, "option": "value"}
        config = self.alert_config.get_provider_config("nonexistent", default_config)
        self.assertEqual(config["enabled"], True)
        self.assertEqual(config["option"], "value")
    
    def test_set_provider_config(self):
        """Test setting provider configuration."""
        # Set provider config
        new_config = {"enabled": True, "option": "new_value"}
        self.alert_config.set_provider_config("popup", new_config)
        
        # Check that config was updated in the config manager
        updated_config = self.config_manager.get("providers_default_config", {})
        self.assertIn("popup", updated_config)
        self.assertEqual(updated_config["popup"], new_config)
    
    def test_subscribe_to_config_changes(self):
        """Test subscribing to configuration changes."""
        # Create a callback function
        callback = MagicMock()
        
        # Mock the config manager's subscribe method
        with patch.object(self.alert_config.config_manager, 'subscribe') as mock_subscribe:
            # Subscribe to config changes
            self.alert_config.subscribe_to_config_changes(callback)
            
            # Check that subscribe was called for each key
            expected_keys = [
                "alert_history_max_size",
                "cooldown_period",
                "providers_enabled",
                "providers_default_config"
            ]
            
            # Verify subscribe was called for each key with the callback
            self.assertEqual(mock_subscribe.call_count, len(expected_keys))
            
            # Get all the actual calls
            actual_calls = [call[0][0] for call in mock_subscribe.call_args_list]
            
            # Verify all expected keys were subscribed to
            for key in expected_keys:
                self.assertIn(key, actual_calls)
                
            # Verify the callback was passed correctly
            for call in mock_subscribe.call_args_list:
                self.assertEqual(call[0][1], callback)


if __name__ == "__main__":
    unittest.main()
