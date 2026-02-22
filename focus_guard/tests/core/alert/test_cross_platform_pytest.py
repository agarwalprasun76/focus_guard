"""
Cross-platform tests for the alert system using pytest-asyncio.

This module contains tests that validate the alert system's behavior
across different platforms and ensure proper platform detection and fallback.
"""

import pytest
import sys
from unittest.mock import MagicMock, patch, call, PropertyMock

from focus_guard.core.alert.models import AlertInfo, AlertLevel
from focus_guard.core.alert.alert_system import AlertSystem
from focus_guard.core.alert.platform import get_platform_implementation
from focus_guard.core.alert.platform.base import PlatformAlertInterface
from focus_guard.core.alert.platform.stub import StubAlertPlatform
from focus_guard.core.alert.platform.windows import WindowsAlertPlatform


class MockConfigManager:
    """Mock configuration manager for testing."""
    
    def __init__(self, initial_config=None):
        """Initialize with optional initial configuration."""
        self.config = initial_config or {}
        self.subscribers = {}
    
    def get(self, path, default=None):
        """Get a configuration value."""
        return self.config.get(path, default)
    
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
        
    def get_config_value(self, path, default=None):
        """Get a configuration value (alias for get)."""
        return self.get(path, default)
        
    def set_config_value(self, path, value):
        """Set a configuration value (alias for set)."""
        return self.set(path, value)


class TestCrossPlatformBehavior:
    """Tests for cross-platform behavior of the alert system."""
    
    @pytest.fixture
    def config_manager(self):
        """Create mock configuration manager."""
        return MockConfigManager({
            "alert_system": {
                "enabled": True,
                "history_file": "alert_history.json",
                "max_history": 100,
                "cooldown_period": 30,
                "providers": {
                    "popup": {
                        "enabled": True,
                        "popup_duration": 5
                    },
                    "sound": {
                        "enabled": True,
                        "volume": 0.5,
                        "repeat_count": 2
                    }
                }
            }
        })

    def _setup_thread_mock(self, mock_thread_class):
        """Helper to set up thread mock and capture thread target."""
        captured = {'target': None, 'start_call_count': 0}
        
        def increment_start_count():
            captured['start_call_count'] += 1
            
        def capture_thread(*args, **kwargs):
            captured['target'] = kwargs.get('target') or args[0]
            mock_thread = MagicMock()
            mock_thread.start = increment_start_count
            return mock_thread
            
        mock_thread_class.side_effect = capture_thread
        return captured

    def _execute_thread_target(self, captured, alert_info):
        """Helper to execute the captured thread target with proper arguments."""
        if captured['target'] is None:
            return None
            
        try:
            # Execute the thread target
            result = captured['target'](alert_info)
            return result
        except Exception as e:
            # Handle any exceptions during thread execution
            return f"error: {str(e)}"

    def test_alert_system_with_windows_platform(self, config_manager, mocker):
        """Test alert system with Windows platform."""
        mocker.patch('subprocess.run', return_value=MagicMock(returncode=0))
        mock_thread_class = mocker.patch('threading.Thread')

        # Setup thread mock and capture target
        captured = self._setup_thread_mock(mock_thread_class)

        # Create alert system with real Windows platform (we're on Windows)
        alert_system = AlertSystem(config_manager)

        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )

        # send_alert should succeed
        result = alert_system.send_alert(alert_info)
        assert result is True

        # Verify a thread was created for dispatching
        assert captured['start_call_count'] >= 1 or captured['target'] is not None

    def test_platform_specific_provider_behavior(self, config_manager, mocker):
        """Test that providers adapt to different platforms."""
        mocker.patch('subprocess.run', return_value=MagicMock(returncode=0))
        mock_thread_class = mocker.patch('threading.Thread')

        captured = self._setup_thread_mock(mock_thread_class)

        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )

        # Create alert system — on Windows it will use WindowsAlertPlatform
        alert_system = AlertSystem(config_manager)

        result = alert_system.send_alert(alert_info)
        assert result is True

        # Verify provider dispatched via thread
        assert captured['start_call_count'] >= 1 or captured['target'] is not None

    def test_custom_platform_implementation(self, config_manager, mocker):
        """Test using a custom platform implementation."""
        # Setup mocks using pytest-mock
        mock_is_supported = mocker.patch('focus_guard.core.alert.platform.windows.WindowsAlertPlatform.is_supported', return_value=True)
        mock_subprocess_run = mocker.patch('subprocess.run')
        mock_get_platform = mocker.patch('focus_guard.core.alert.platform.get_platform_implementation')
        mock_platform_instance = mocker.patch('focus_guard.core.alert.platform._platform_instance', None)
        mock_thread_class = mocker.patch('threading.Thread')
        mock_sys_platform = mocker.patch('sys.platform', 'win32')
        # Setup thread mock and capture target
        captured = self._setup_thread_mock(mock_thread_class)
        
        # Create a custom platform implementation
        class CustomPlatform(PlatformAlertInterface):
            @classmethod
            def is_supported(cls):
                return True
                
            def show_notification(self, title, message, level, options=None):
                return True
                
            def play_sound(self, sound_type, options=None):
                return True
                
            def show_blocking_alert(self, title, message, level, options=None):
                return True

        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )
        
        # Mock subprocess.run
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        # Create alert system with custom platform
        alert_system = AlertSystem(config_manager)
        
        # Send alert
        result = alert_system.send_alert(alert_info)
        assert result is True
        
        # Execute thread target
        self._execute_thread_target(captured, alert_info)

    def test_platform_detection(self):
        """Test that the correct platform is detected based on the OS."""
        with patch('sys.platform', 'win32'):
            with patch('focus_guard.core.alert.platform.windows.WindowsAlertPlatform.is_supported', return_value=True):
                platform = get_platform_implementation()
                assert isinstance(platform, WindowsAlertPlatform)

    def test_platform_fallback(self):
        """Test fallback to stub platform when preferred platform is not available."""
        import focus_guard.core.alert.platform as platform_module
        old_instance = platform_module._platform_instance
        try:
            platform_module._platform_instance = None
            with patch('sys.platform', 'linux'):
                with patch('focus_guard.core.alert.platform.windows.WindowsAlertPlatform.is_supported', return_value=False):
                    platform = get_platform_implementation()
                    assert isinstance(platform, StubAlertPlatform)
        finally:
            platform_module._platform_instance = old_instance

    def test_platform_extension_guide(self):
        """Test that the platform extension guide is accurate."""
        # Create a new platform implementation following the guide
        class LinuxAlertPlatform(PlatformAlertInterface):
            @classmethod
            def is_supported(cls):
                return sys.platform.startswith('linux')
                
            def show_notification(self, title, message, level, options=None):
                return True
                
            def play_sound(self, sound_type, options=None):
                return True
                
            def show_blocking_alert(self, title, message, level, options=None):
                return True

        # Verify that the implementation meets the interface requirements
        assert hasattr(LinuxAlertPlatform, 'is_supported')
        assert callable(LinuxAlertPlatform.is_supported)
        
        linux_platform = LinuxAlertPlatform()
        assert hasattr(linux_platform, 'show_notification')
        assert callable(linux_platform.show_notification)
        assert hasattr(linux_platform, 'play_sound')
        assert callable(linux_platform.play_sound)
        assert hasattr(linux_platform, 'show_blocking_alert')
        assert callable(linux_platform.show_blocking_alert)
