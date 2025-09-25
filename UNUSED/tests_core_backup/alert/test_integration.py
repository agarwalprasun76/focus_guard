"""
Integration tests for the alert system.

This module contains tests that verify the integration between
different components of the alert system.
"""

import unittest
import time
import json
import os
import tempfile
from unittest.mock import patch, MagicMock

from core_v2.alert.models import AlertInfo, AlertLevel, AlertHistoryEntry
from core_v2.alert.alert_system import AlertSystem
from core_v2.alert.providers.base import AlertProvider, CompositeAlertProvider
from core_v2.alert.providers.popup import PopupAlertProvider
from core_v2.alert.providers.sound import SoundAlertProvider
from core_v2.alert.providers.blocking import BlockingAlertProvider
from core_v2.alert.providers.email import EmailAlertProvider
from core_v2.alert.providers.webhook import WebhookAlertProvider
from core_v2.alert.providers.app import AppAlertProvider
from core_v2.alert.platform import get_platform_implementation


class MockConfigManager:
    """Mock configuration manager for testing."""
    
    def __init__(self, initial_config=None):
        """Initialize with optional initial configuration."""
        self.config = initial_config or {}
        self.subscribers = {}
    
    def get(self, path, default=None):
        """Get a configuration value."""
        return self.config.get(path, default)
    
    def get_config_value(self, path, default=None):
        """Get a configuration value (alias for get)."""
        return self.get(path, default)
        
    def set_config_value(self, path, value):
        """Set a configuration value (alias for set)."""
        return self.set(path, value)
    
    def set(self, path, value):
        """Set a configuration value and notify subscribers."""
        self.config[path] = value
        if path in self.subscribers:
            for callback in self.subscribers[path]:
                callback(path, value)
        return True
    
    def subscribe(self, path, callback):
        """Subscribe to configuration changes."""
        if path not in self.subscribers:
            self.subscribers[path] = []
        self.subscribers[path].append(callback)
        return True


class TestAlertSystemIntegration(unittest.TestCase):
    """Integration tests for the alert system."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for alert history
        self.temp_dir = tempfile.TemporaryDirectory()
        self.history_path = os.path.join(self.temp_dir.name, "alert_history.json")
        
        # Mock platform
        self.platform = MagicMock()
        
        # Mock config manager with history file path
        self.config_manager = MockConfigManager({
            "alert_system": {
                "enabled": True,
                "history_file": self.history_path,
                "max_history": 100,
                "cooldown_period": 30,
                "providers": {
                    "popup": {
                        "enabled": True,
                        "popup_duration": 5
                    },
                    "sound": {
                        "enabled": True,
                        "sound_file": "alert.wav"
                    },
                    "desktop": {
                        "enabled": True
                    },
                    "blocking": {
                        "enabled": True,
                        "timeout": 0
                    },
                    "email": {
                        "enabled": False,
                        "smtp_server": "smtp.example.com",
                        "smtp_port": 587,
                        "username": "test@example.com",
                        "password": "password",
                        "from_address": "alerts@example.com",
                        "to_address": "user@example.com"
                    },
                    "webhook": {
                        "enabled": False,
                        "url": "https://example.com/webhook",
                        "headers": {"Content-Type": "application/json"},
                        "method": "POST"
                    },
                    "app": {
                        "enabled": False,
                        "app_id": "com.example.focusguard",
                        "api_key": "test_api_key",
                        "device_ids": ["device1", "device2"],
                        "min_level": "warning",
                        "include_window_info": True,
                        "cooldown_period": 60
                    }
                }
            }
        })
        
        # Create alert system
        with patch('core_v2.alert.platform.get_platform_implementation', return_value=self.platform):
            self.alert_system = AlertSystem(self.config_manager)
            
        # Explicitly set the history path in the alert system
        self.alert_system.history_path = self.history_path
        print(f"Setting alert system history path to: {self.history_path}")
        
        # Clear alert history to ensure consistent count
        self.alert_system.alert_history = []
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_alert_system_initialization(self):
        """Test alert system initialization with config."""
        # Check that providers were created
        self.assertEqual(len(self.alert_system.providers), 3)  # Only enabled providers
        
        # Check provider types
        provider_types = [type(p) for p in self.alert_system.providers.values()]
        self.assertIn(PopupAlertProvider, provider_types)
        self.assertIn(SoundAlertProvider, provider_types)
        self.assertIn(BlockingAlertProvider, provider_types)
    
    def test_alert_dispatch_to_providers(self):
        """Test that alerts are dispatched to all enabled providers."""
        # Create mock composite provider
        mock_composite = MagicMock(spec=CompositeAlertProvider)
        mock_composite.send_alert.return_value = True
        
        # Replace the composite provider
        self.alert_system.composite_provider = mock_composite
        
        # Send alert using the alert method
        result = self.alert_system.alert(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )
        
        # Check that the alert was dispatched to the composite provider
        self.assertTrue(result)
        self.assertTrue(mock_composite.send_alert.called)
        
        # Verify the alert info in the call
        call_args = mock_composite.send_alert.call_args[0][0]
        self.assertEqual(call_args.app_name, "TestApp")
        self.assertEqual(call_args.message, "Test message")
        self.assertEqual(call_args.level, AlertLevel.WARNING)
    
    def test_alert_history_persistence(self):
        """Test that alert history is persisted to disk."""
        # Mock the composite provider to avoid actual alert dispatching
        mock_composite = MagicMock(spec=CompositeAlertProvider)
        mock_composite.send_alert.return_value = True
        self.alert_system.composite_provider = mock_composite
        
        # Print debug info
        print(f"Test history path: {self.history_path}")
        print(f"Alert system history path: {self.alert_system.history_path}")
        
        # Send alert using the alert method
        self.alert_system.alert(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )
        
        # Save history (using the private method since there's no public method)
        self.alert_system._save_history()
        
        # Check that history file exists
        print(f"Checking if history file exists: {self.history_path}")
        exists = os.path.exists(self.history_path)
        print(f"History file exists: {exists}")
        self.assertTrue(exists)
        
        # Load history from file
        with open(self.history_path, 'r') as f:
            history_data = json.load(f)
        
        # Check that history contains our alert
        print(f"History data length: {len(history_data)}")
        self.assertEqual(len(history_data), 1)
        entry = history_data[0]
        # The structure might be nested with alert_info
        if "alert_info" in entry:
            alert_info = entry["alert_info"]
            self.assertEqual(alert_info["app_name"], "TestApp")
            self.assertEqual(alert_info["message"], "Test message")
            self.assertEqual(alert_info["level"], "warning")
        else:
            self.assertEqual(entry["app_name"], "TestApp")
            self.assertEqual(entry["message"], "Test message")
            self.assertEqual(entry["level"], "warning")
    
    def test_config_changes_propagate_to_providers(self):
        """Test that configuration changes propagate to providers."""
        # Create a real provider to test config propagation
        popup_provider = PopupAlertProvider({"popup_duration": 5})
        popup_provider.platform = self.platform
        
        # Replace providers with our test provider
        self.alert_system.providers = {"popup": popup_provider}
        
        # Set up the alert config manager to handle the configuration change
        from core_v2.alert.config import AlertConfigManager
        self.alert_system.alert_config = AlertConfigManager(self.config_manager)
        
        # Configure the provider through the alert system
        new_config = {"popup_duration": 10}
        self.alert_system.configure_provider("popup", new_config)
        
        # Check that provider config was updated
        self.assertEqual(popup_provider.config["popup_duration"], 10)
    
    def test_provider_addition_and_removal(self):
        """Test adding and removing providers."""
        # Create providers
        popup = PopupAlertProvider({"popup_duration": 5})
        sound = SoundAlertProvider({"volume": 0.5})
        
        # Clear existing providers
        self.alert_system.providers = {}
        self.alert_system.composite_provider = CompositeAlertProvider()
        
        # Add providers
        self.alert_system.add_provider("popup", popup)
        self.alert_system.add_provider("sound", sound)
        
        # Check that providers were added
        self.assertEqual(len(self.alert_system.providers), 2)
        self.assertEqual(self.alert_system.providers["popup"], popup)
        self.assertEqual(self.alert_system.providers["sound"], sound)
        
        # Remove a provider
        self.alert_system.remove_provider("popup")
        
        # Check that provider was removed
        self.assertEqual(len(self.alert_system.providers), 1)
        self.assertNotIn("popup", self.alert_system.providers)
        self.assertIn("sound", self.alert_system.providers)
    
    def test_cooldown_enforcement(self):
        """Test that cooldown periods are enforced."""
        # Mock the composite provider to track calls
        mock_composite = MagicMock(spec=CompositeAlertProvider)
        mock_composite.send_alert.return_value = True
        self.alert_system.composite_provider = mock_composite
        
        # Set app name for consistent testing
        app_name = "TestApp"
        
        # Send first alert
        result1 = self.alert_system.alert(
            app_name=app_name,
            message="Test message 1",
            level=AlertLevel.WARNING
        )
        self.assertTrue(result1)
        self.assertEqual(mock_composite.send_alert.call_count, 1)
        
        # Send second alert immediately (should be blocked by cooldown)
        mock_composite.reset_mock()
        result2 = self.alert_system.alert(
            app_name=app_name,
            message="Test message 2",
            level=AlertLevel.WARNING
        )
        self.assertFalse(result2)  # Should be blocked by cooldown
        self.assertEqual(mock_composite.send_alert.call_count, 0)
        
        # Simulate cooldown period passed by directly modifying the cooldown timer
        from datetime import datetime, timedelta
        self.alert_system.cooldown_timers[app_name] = datetime.now() - timedelta(seconds=self.alert_system.cooldown_period + 1)
        
        # Send third alert (should work now that cooldown has passed)
        mock_composite.reset_mock()
        result3 = self.alert_system.alert(
            app_name=app_name,
            message="Test message 3",
            level=AlertLevel.WARNING
        )
        self.assertTrue(result3)
        self.assertEqual(mock_composite.send_alert.call_count, 1)
    
    def test_end_to_end_alert_flow(self):
        """Test the end-to-end alert flow with real components."""
        # Mock platform methods
        self.platform.show_notification.return_value = True
        self.platform.play_sound.return_value = True
        self.platform.show_blocking_alert.return_value = True
        
        # Create alert system with real providers
        with patch('core_v2.alert.platform.get_platform_implementation', return_value=self.platform):
            alert_system = AlertSystem(self.config_manager)
            
        # Clear alert history to ensure consistent count
        alert_system.alert_history = []
        
        # Send alert using the alert method (not send_alert)
        with patch('threading.Thread') as mock_thread:
            mock_thread.return_value = MagicMock()
            result = alert_system.alert(
                app_name="TestApp",
                message="Test message",
                level=AlertLevel.WARNING,
                window_info={"title": "Test Window"}
            )
            self.assertTrue(result)
        
        # Check that alert was added to history
        self.assertEqual(len(alert_system.alert_history), 1)
        history_entry = alert_system.alert_history[0]
        self.assertEqual(history_entry.alert_info.app_name, "TestApp")
        self.assertEqual(history_entry.alert_info.message, "Test message")
        self.assertEqual(history_entry.alert_info.level, AlertLevel.WARNING)


if __name__ == "__main__":
    unittest.main()
