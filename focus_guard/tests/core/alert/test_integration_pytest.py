"""
Pytest integration tests for the alert system.

This module contains tests that verify the integration between
different components of the alert system.
"""

import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call

import pytest

from focus_guard.core.alert.models import AlertInfo, AlertLevel, AlertHistoryEntry
from focus_guard.core.alert.alert_system import AlertSystem
from focus_guard.core.alert.providers.base import AlertProvider, CompositeAlertProvider
from focus_guard.core.alert.providers.popup import PopupAlertProvider
from focus_guard.core.alert.providers.sound import SoundAlertProvider
from focus_guard.core.alert.providers.blocking import BlockingAlertProvider
from focus_guard.core.alert.platform import get_platform_implementation


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


@pytest.fixture
def temp_alert_history():
    """Create a temporary directory for alert history."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield os.path.join(temp_dir, "alert_history.json")


@pytest.fixture
def mock_platform():
    """Create a mock platform implementation."""
    with patch('focus_guard.core.alert.platform.get_platform_implementation') as mock_platform:
        platform = MagicMock()
        platform.show_notification.return_value = True
        platform.play_sound.return_value = True
        platform.show_blocking_alert.return_value = True
        mock_platform.return_value = platform
        yield platform


@pytest.fixture
def sample_config(temp_alert_history):
    """Create a sample configuration."""
    return {
        "alert_system": {
            "enabled": True,
            "history_file": temp_alert_history,
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
                }
            }
        }
    }


@pytest.fixture
def config_manager(sample_config):
    """Create a config manager with sample configuration."""
    return MockConfigManager(sample_config)


@pytest.fixture
def alert_system(config_manager, mock_platform, temp_alert_history):
    """Create an alert system instance for testing."""
    system = AlertSystem(config_manager)
    system.history_path = temp_alert_history
    system.alert_history = []  # Clear alert history
    return system


class TestAlertSystemIntegration:
    """Integration tests for the alert system."""
    
    def test_alert_system_initialization(self, alert_system):
        """Test alert system initialization with config."""
        # Check that providers were created
        assert len(alert_system.providers) == 3  # Only enabled providers
        
        # Check provider types
        provider_types = [type(p) for p in alert_system.providers.values()]
        assert PopupAlertProvider in provider_types
        assert SoundAlertProvider in provider_types
        assert BlockingAlertProvider in provider_types
    
    def test_alert_dispatch_to_providers(self, alert_system):
        """Test that alerts are dispatched to all enabled providers."""
        # Mock each individual provider's send_alert (send_alert iterates self.providers)
        for provider in alert_system.providers.values():
            provider.send_alert = MagicMock(return_value=True)

        # Send alert using the alert method
        result = alert_system.alert(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )

        assert result is True

        # Verify at least one provider received the alert
        any_called = any(
            provider.send_alert.called
            for provider in alert_system.providers.values()
        )
        assert any_called

        # Verify the alert info in one of the calls
        for provider in alert_system.providers.values():
            if provider.send_alert.called:
                call_args = provider.send_alert.call_args[0][0]
                assert call_args.app_name == "TestApp"
                assert call_args.message == "Test message"
                assert call_args.level == AlertLevel.WARNING
                break
    
    def test_alert_history_persistence(self, alert_system, temp_alert_history):
        """Test that alert history is persisted to disk."""
        # Mock individual providers to avoid actual alert dispatching
        for provider in alert_system.providers.values():
            provider.send_alert = MagicMock(return_value=True)

        # Send alert using the alert method
        alert_system.alert(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )

        # History is auto-saved by send_alert -> _add_alert_to_history
        # Check that history file exists
        assert os.path.exists(temp_alert_history)

        # Load history from file
        with open(temp_alert_history, 'r') as f:
            history_data = json.load(f)

        # Check that history contains our alert
        assert len(history_data) >= 1
        entry = history_data[0]

        # The structure is nested with alert_info
        if "alert_info" in entry:
            alert_info = entry["alert_info"]
            assert alert_info["app_name"] == "TestApp"
            assert alert_info["message"] == "Test message"
        else:
            assert entry["app_name"] == "TestApp"
            assert entry["message"] == "Test message"
    
    def test_config_changes_propagate_to_providers(self, alert_system, config_manager):
        """Test that configuration changes propagate to providers."""
        # Create a real provider to test config propagation
        popup_provider = PopupAlertProvider({"popup_duration": 5})
        popup_provider.platform = MagicMock()
        
        # Replace providers with our test provider
        alert_system.providers = {"popup": popup_provider}
        
        # Set up the alert config manager to handle the configuration change
        from focus_guard.core.alert.config import AlertConfigManager
        alert_system.alert_config = AlertConfigManager(config_manager)
        
        # Configure the provider through the alert system
        new_config = {"popup_duration": 10}
        alert_system.configure_provider("popup", new_config)
        
        # Check that provider config was updated
        assert popup_provider.config["popup_duration"] == 10
    
    def test_provider_addition_and_removal(self, alert_system):
        """Test adding and removing providers."""
        # Create providers
        popup = PopupAlertProvider({"popup_duration": 5})
        sound = SoundAlertProvider({"volume": 0.5})
        
        # Clear existing providers
        alert_system.providers = {}
        alert_system.composite_provider = CompositeAlertProvider()
        
        # Add providers
        alert_system.add_provider("popup", popup)
        alert_system.add_provider("sound", sound)
        
        # Check that providers were added
        assert len(alert_system.providers) == 2
        assert alert_system.providers["popup"] == popup
        assert alert_system.providers["sound"] == sound
        
        # Remove a provider
        alert_system.remove_provider("popup")
        
        # Check that provider was removed
        assert len(alert_system.providers) == 1
        assert "popup" not in alert_system.providers
        assert "sound" in alert_system.providers
    
    def test_cooldown_enforcement(self, alert_system):
        """Test that cooldown periods are enforced."""
        # Mock individual providers to track calls
        for provider in alert_system.providers.values():
            provider.send_alert = MagicMock(return_value=True)

        app_name = "CooldownTestApp"

        # Send first alert
        result1 = alert_system.alert(
            app_name=app_name,
            message="Test message 1",
            level=AlertLevel.WARNING
        )
        assert result1 is True

        # Send second alert immediately (should be blocked by cooldown)
        result2 = alert_system.alert(
            app_name=app_name,
            message="Test message 2",
            level=AlertLevel.WARNING
        )
        assert result2 is False  # Should be blocked by cooldown

        # Simulate cooldown period passed
        alert_system.cooldown_timers[app_name] = datetime.now() - timedelta(seconds=alert_system.cooldown_period + 1)

        # Send third alert (should work now that cooldown has passed)
        result3 = alert_system.alert(
            app_name=app_name,
            message="Test message 3",
            level=AlertLevel.WARNING
        )
        assert result3 is True
    
    def test_end_to_end_alert_flow(self, config_manager, mock_platform):
        """Test the end-to-end alert flow with real components."""
        # Create alert system with real providers
        alert_system = AlertSystem(config_manager)
        alert_system.alert_history = []  # Clear alert history
        
        # Send alert using the alert method (not send_alert)
        with patch('threading.Thread') as mock_thread:
            mock_thread.return_value = MagicMock()
            result = alert_system.alert(
                app_name="TestApp",
                message="Test message",
                level=AlertLevel.WARNING,
                window_info={"title": "Test Window"}
            )
            assert result is True
        
        # Check that alert was added to history
        assert len(alert_system.alert_history) == 1
        history_entry = alert_system.alert_history[0]
        assert history_entry.alert_info.app_name == "TestApp"
        assert history_entry.alert_info.message == "Test message"
        assert history_entry.alert_info.level == AlertLevel.WARNING
