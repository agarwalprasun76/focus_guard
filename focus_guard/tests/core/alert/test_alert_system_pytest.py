import pytest
import os
import json
import tempfile
import shutil
from datetime import datetime
from unittest.mock import MagicMock

from focus_guard.core.alert.models import AlertInfo, AlertLevel, AlertHistoryEntry
from focus_guard.core.alert.alert_system import AlertSystem
from focus_guard.core.alert.providers.base import AlertProvider
from focus_guard.core.alert.config import AlertConfigManager, AlertConfigKeys


class MockAlertProvider(AlertProvider):
    """Mock alert provider for testing."""
    
    def __init__(self, config=None, name=None):
        super().__init__(config or {})
        self.name = name or self.__class__.__name__
        self.alerts = []
        self.enabled = True
    
    def update_config(self, config: dict) -> None:
        """Update provider configuration."""
        self.config.update(config)
        if 'enabled' in config:
            self.enabled = config['enabled']
    
    def send_alert(self, alert_info: AlertInfo) -> bool:
        """Record the alert and return success."""
        self.alerts.append(alert_info)
        return True
    
    def get_alerts(self) -> list[AlertInfo]:
        """Get all sent alerts."""
        return self.alerts


class MockConfigManager:
    """Mock configuration manager for testing."""
    
    def __init__(self):
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
    
    def get_config_value(self, key: str, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set_config_value(self, key: str, value) -> None:
        """Set a configuration value."""
        self.config[key] = value
        if key in self.subscribers:
            for callback in self.subscribers[key]:
                callback(key, value)
    
    def subscribe(self, key: str, callback: callable) -> None:
        """Subscribe to configuration changes."""
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(callback)
    
    # Aliases for compatibility
    get = get_config_value
    set = set_config_value


@pytest.fixture
def setup_alert_system():
    temp_dir = tempfile.mkdtemp()
    history_file = os.path.join(temp_dir, "alert_history.json")

    popup_provider = MockAlertProvider({"enabled": True}, "popup")
    sound_provider = MockAlertProvider({"enabled": True}, "sound")
    blocking_provider = MockAlertProvider({"enabled": True}, "blocking")

    config_manager = MockConfigManager()

    alert_system = AlertSystem(history_file=history_file, config_manager=config_manager)
    alert_system.providers = {
        "popup": popup_provider,
        "sound": sound_provider,
        "blocking": blocking_provider
    }

    yield alert_system, popup_provider, sound_provider, blocking_provider, history_file

    shutil.rmtree(temp_dir)


def test_initialization(setup_alert_system):
    """Test alert system initialization."""
    alert_system, popup_provider, sound_provider, blocking_provider, _ = setup_alert_system
    
    # Check that providers are initialized
    assert "popup" in alert_system.providers
    assert "sound" in alert_system.providers
    assert "blocking" in alert_system.providers
    
    # Check that providers are properly configured
    assert popup_provider.enabled
    assert sound_provider.enabled
    assert blocking_provider.enabled
    
    # Check cooldown period (default is 60 seconds)
    assert alert_system.cooldown_period == 30  # From MockConfigManager


def test_send_alert(setup_alert_system):
    """Test sending an alert."""
    alert_system, popup_provider, sound_provider, blocking_provider, _ = setup_alert_system
    alert_system.alert_history = []
    
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
    result = alert_system.send_alert(alert_info)
    assert result
    
    # Check that alert was sent to all providers
    assert len(popup_provider.get_alerts()) == 1
    assert len(sound_provider.get_alerts()) == 1
    assert len(blocking_provider.get_alerts()) == 1
    
    # Verify alert content in providers
    for provider in [popup_provider, sound_provider, blocking_provider]:
        sent_alert = provider.get_alerts()[0]
        assert sent_alert.app_name == "TestApp"
        assert sent_alert.message == "Test message"
        assert sent_alert.level == AlertLevel.WARNING
        assert sent_alert.window_title == "Test Window"
        assert sent_alert.pid == 12345
    
    # Check that alert was added to history
    assert len(alert_system.alert_history) == 1
    history_entry = alert_system.alert_history[0]
    assert history_entry.alert_info.message == "Test message"
    assert history_entry.alert_info.app_name == "TestApp"
    assert history_entry.alert_info.level == AlertLevel.WARNING
    assert not history_entry.acknowledged
    assert history_entry.acknowledged_time is None


def test_send_alert_with_cooldown(setup_alert_system):
    """Test sending alerts with cooldown period."""
    alert_system, popup_provider, _, _, _ = setup_alert_system
    
    # Create alert info
    alert_info = AlertInfo(
        app_name="TestApp",
        message="Test message",
        level=AlertLevel.WARNING,
        timestamp=datetime.now()
    )
    
    # Send first alert (should work)
    result1 = alert_system.send_alert(alert_info)
    assert result1
    
    # Send second alert immediately (should be blocked by cooldown)
    result2 = alert_system.send_alert(alert_info)
    assert not result2
    
    # Check that providers only received one alert
    assert len(popup_provider.get_alerts()) == 1
    
    # Reset cooldown timer
    alert_system.reset_cooldown(alert_info.app_name)
    
    # Send third alert (should work after reset)
    result3 = alert_system.send_alert(alert_info)
    assert result3
    
    # Check that providers received second alert
    assert len(popup_provider.get_alerts()) == 2
    
    # Test cooldown with different app names
    other_alert = AlertInfo(
        app_name="OtherApp",
        message="Other message",
        level=AlertLevel.WARNING,
        timestamp=datetime.now()
    )
    
    # Should work since it's a different app
    result4 = alert_system.send_alert(other_alert)
    assert result4
    assert len(popup_provider.get_alerts()) == 3


def test_get_provider(setup_alert_system):
    """Test getting a provider."""
    alert_system, popup_provider, sound_provider, blocking_provider, _ = setup_alert_system
    
    # Test getting existing providers
    provider = alert_system.get_provider("popup")
    assert provider == popup_provider
    
    provider = alert_system.get_provider("sound")
    assert provider == sound_provider
    
    provider = alert_system.get_provider("blocking")
    assert provider == blocking_provider
    
    # Test getting non-existent provider
    with pytest.raises(KeyError):
        alert_system.get_provider("nonexistent")


def test_add_provider(setup_alert_system):
    """Test adding alert providers."""
    alert_system, popup_provider, _, _, _ = setup_alert_system
    
    # Test adding a new provider with valid name
    test_provider = MockAlertProvider({"enabled": True}, "test")
    alert_system.add_provider("test_provider", test_provider)
    assert "test_provider" in alert_system.providers
    assert alert_system.providers["test_provider"].enabled
    
    # Test adding a duplicate provider (should replace existing)
    assert popup_provider.enabled
    new_popup_provider = MockAlertProvider({"enabled": False}, "popup")
    alert_system.add_provider("popup", new_popup_provider)
    assert alert_system.providers["popup"] is new_popup_provider
    assert not alert_system.providers["popup"].enabled
    
    # Test adding a provider with invalid name (empty string)
    with pytest.raises(ValueError):
        alert_system.add_provider("", MockAlertProvider({}, "invalid"))
    
    # Test adding a provider with invalid name (None)
    with pytest.raises(ValueError):
        alert_system.add_provider(None, MockAlertProvider({}, "invalid"))
    
    # Test adding a None provider
    with pytest.raises(ValueError):
        alert_system.add_provider("invalid_provider", None)


def test_remove_provider(setup_alert_system):
    """Test removing a provider."""
    alert_system, _, _, _, _ = setup_alert_system
    
    # Remove provider
    result = alert_system.remove_provider("popup")
    assert result
    assert "popup" not in alert_system.providers
    
    # Remove non-existent provider
    result = alert_system.remove_provider("nonexistent")
    assert not result


def test_enable_disable_providers(setup_alert_system):
    """Test enabling and disabling providers."""
    alert_system, popup_provider, sound_provider, blocking_provider, _ = setup_alert_system
    
    # Disable providers
    alert_system.enable_providers(False)
    assert not popup_provider.enabled
    assert not sound_provider.enabled
    assert not blocking_provider.enabled
    
    # Enable providers
    alert_system.enable_providers(True)
    assert popup_provider.enabled
    assert sound_provider.enabled
    assert blocking_provider.enabled


def test_add_alert_to_history(setup_alert_system):
    """Test adding an alert to history."""
    alert_system, _, _, _, _ = setup_alert_system
    alert_system.alert_history = []
    
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
    alert_system._add_alert_to_history(alert_info)
    
    # Check that alert was added to history
    assert len(alert_system.alert_history) == 1
    assert alert_system.alert_history[0].alert_info.message == "Test message"
    assert alert_system.alert_history[0].alert_info.app_name == "TestApp"
    assert alert_system.alert_history[0].alert_info.level == AlertLevel.WARNING
    assert alert_system.alert_history[0].alert_info.window_title == "Test Window"
    assert alert_system.alert_history[0].alert_info.window_url == "http://example.com"


def test_history_size_limit(setup_alert_system):
    """Test history size limit."""
    alert_system, _, _, _, _ = setup_alert_system
    alert_system.max_history_size = 3
    alert_system.alert_history = []
    
    # Add multiple alerts
    for i in range(5):
        alert_info = AlertInfo(
            app_name="TestApp",
            message=f"Test message {i}",
            level=AlertLevel.WARNING,
            timestamp=datetime.now()
        )
        alert_system._add_alert_to_history(alert_info)
    
    # Check that history size is limited
    assert len(alert_system.alert_history) == 3
    
    # Check that oldest entries were removed
    assert alert_system.alert_history[0].alert_info.message == "Test message 2"
    assert alert_system.alert_history[1].alert_info.message == "Test message 3"
    assert alert_system.alert_history[2].alert_info.message == "Test message 4"


def test_save_load_history(setup_alert_system):
    alert_system, _, _, _, history_file = setup_alert_system
    alert_system.alert_history.clear()

    test_timestamps = [datetime(2023, 1, 1, i+1) for i in range(3)]
    alerts = []
    for i in range(3):
        alert_info = AlertInfo(
            app_name=f"TestApp{i}",
            message=f"Test message {i}",
            level=AlertLevel.WARNING,
            timestamp=test_timestamps[i]
        )
        alerts.append(alert_info)
        alert_system._add_alert_to_history(alert_info)

    alert_system._save_history()

    new_system = AlertSystem(history_file=history_file, config_manager=MockConfigManager())
    new_system._load_history()

    assert len(new_system.alert_history) == len(alerts)
    for i, alert_info in enumerate(alerts):
        loaded_entry = new_system.alert_history[i]
        assert loaded_entry.alert_info.message == alert_info.message
        assert loaded_entry.alert_info.app_name == alert_info.app_name
        assert loaded_entry.alert_info.level == alert_info.level
        assert loaded_entry.timestamp == alert_info.timestamp


def test_config_subscription(setup_alert_system):
    alert_system, popup_provider, _, _, _ = setup_alert_system
    assert popup_provider.enabled

    alert_system._on_provider_config_changed("popup", {"enabled": False})
    assert not popup_provider.enabled

    alert_system._on_provider_config_changed("popup", {
        "enabled": True,
        "popup_duration": 15
    })
    assert popup_provider.enabled

    alert_system._on_provider_config_changed("popup", False)
    assert not popup_provider.enabled

    alert_system._on_provider_config_changed("nonexistent", {"enabled": True})  # should not raise


def test_get_alert_history(setup_alert_system):
    alert_system, _, _, _, _ = setup_alert_system
    alert_system.alert_history.clear()

    for i in range(3):
        alert_info = AlertInfo(
            app_name="TestApp",
            message=f"Test message {i}",
            level=AlertLevel.WARNING,
            timestamp=datetime.now()
        )
        alert_system._add_alert_to_history(alert_info)

    history = alert_system.get_alert_history()
    assert len(history) == 3
    for i in range(3):
        assert history[i].alert_info.message == f"Test message {i}"


def test_clear_alert_history(setup_alert_system):
    alert_system, _, _, _, history_file = setup_alert_system
    for i in range(3):
        alert_info = AlertInfo(
            app_name="TestApp",
            message=f"Test message {i}",
            level=AlertLevel.WARNING,
            timestamp=datetime.now()
        )
        alert_system._add_alert_to_history(alert_info)

    alert_system.clear_alert_history()
    assert len(alert_system.alert_history) == 0
    assert os.path.exists(history_file)
    with open(history_file, "r") as f:
        data = json.load(f)
        assert len(data) == 0


# ---------------- AlertConfigManager Tests ----------------

@pytest.fixture
def setup_alert_config_manager():
    config_manager = MockConfigManager()
    alert_config = AlertConfigManager(config_manager)
    return config_manager, alert_config


def test_get_alert_history_max_size(setup_alert_config_manager):
    config_manager, alert_config = setup_alert_config_manager
    assert alert_config.get_alert_history_max_size() == 100

    config_manager.set("alert_history_max_size", 200)
    if hasattr(alert_config, '_history_size'):
        delattr(alert_config, '_history_size')
    assert alert_config.get_alert_history_max_size() == 200

    config_manager.set("alert_history_max_size", -1)
    if hasattr(alert_config, '_history_size'):
        delattr(alert_config, '_history_size')
    assert alert_config.get_alert_history_max_size() == 100


def test_get_cooldown_period(setup_alert_config_manager):
    config_manager, alert_config = setup_alert_config_manager
    assert alert_config.get_cooldown_period() == 30  # Should match the value in MockConfigManager

    config_manager.set("cooldown_period", 30)
    if hasattr(alert_config, '_cooldown_period'):
        delattr(alert_config, '_cooldown_period')
    assert alert_config.get_cooldown_period() == 30

    config_manager.set("cooldown_period", -1)
    if hasattr(alert_config, '_cooldown_period'):
        delattr(alert_config, '_cooldown_period')
    assert alert_config.get_cooldown_period() == 60


def test_is_provider_enabled(setup_alert_config_manager):
    config_manager, alert_config = setup_alert_config_manager
    config_manager.set("providers_enabled", {"popup": True, "email": False})
    assert alert_config.is_provider_enabled("popup")
    assert not alert_config.is_provider_enabled("email")
    assert not alert_config.is_provider_enabled("nonexistent")


def test_get_provider_config(setup_alert_config_manager):
    config_manager, alert_config = setup_alert_config_manager
    config_manager.set("providers_default_config", {"popup": {"enabled": True, "sound": True}})

    config = alert_config.get_provider_config("popup")
    assert config["enabled"]

    default = {"enabled": True, "option": "value"}
    config = alert_config.get_provider_config("nonexistent", default)
    assert config["enabled"]
    assert config["option"] == "value"


def test_set_provider_config(setup_alert_config_manager):
    config_manager, alert_config = setup_alert_config_manager
    new_config = {"enabled": True, "option": "new_value"}
    alert_config.set_provider_config("popup", new_config)

    updated = config_manager.get("providers_default_config", {})
    assert "popup" in updated
    assert updated["popup"] == new_config


def test_subscribe_to_config_changes(setup_alert_config_manager, mocker):
    _, alert_config = setup_alert_config_manager
    callback = mocker.MagicMock()

    mock_subscribe = mocker.patch.object(alert_config.config_manager, 'subscribe')
    alert_config.subscribe_to_config_changes(callback)

    expected_keys = [
        "alert_history_max_size",
        "cooldown_period",
        "providers_enabled",
        "providers_default_config"
    ]
    actual_calls = [call.args[0] for call in mock_subscribe.call_args_list]
    for key in expected_keys:
        assert key in actual_calls
        assert all(call.args[1] == callback for call in mock_subscribe.call_args_list)
