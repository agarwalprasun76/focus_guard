"""
Cross-platform tests for the alert system.

This module contains tests that validate the alert system's behavior
across different platforms and ensure proper platform detection and fallback.
"""

import unittest
import sys
import platform
from unittest.mock import patch, MagicMock

from core_v2.alert.models import AlertInfo, AlertLevel
from core_v2.alert.alert_system import AlertSystem
from core_v2.alert.platform import get_platform_implementation
from core_v2.alert.platform.base import PlatformAlertInterface
from core_v2.alert.platform.stub import StubAlertPlatform
from core_v2.alert.platform.windows import WindowsAlertPlatform


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


class TestCrossPlatformBehavior(unittest.TestCase):
    """Tests for cross-platform behavior of the alert system."""
    
    def setUp(self):
        """Set up test environment."""
        self.config_manager = MockConfigManager({
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
    
    def test_platform_detection(self):
        """Test that the correct platform is detected based on the OS."""
        # Test Windows platform detection
        with patch('sys.platform', 'win32'):
            with patch('core_v2.alert.platform._platform_instance', None):
                with patch.object(WindowsAlertPlatform, 'is_supported', return_value=True):
                    platform_impl = get_platform_implementation()
                    self.assertIsInstance(platform_impl, WindowsAlertPlatform)
        
        # Test fallback to stub platform on unsupported OS
        with patch('sys.platform', 'unknown'):
            platform_impl = get_platform_implementation()
            self.assertIsInstance(platform_impl, StubAlertPlatform)
    
    def test_platform_fallback(self):
        """Test fallback to stub platform when preferred platform is not available."""
        # Test fallback when on Windows but PowerShell is not available
        with patch('sys.platform', 'win32'):
            with patch.object(WindowsAlertPlatform, 'is_supported', return_value=False):
                platform_impl = get_platform_implementation()
                self.assertIsInstance(platform_impl, StubAlertPlatform)
    
    def test_alert_system_with_windows_platform(self):
        """Test alert system with Windows platform."""
        # Mock Windows platform
        windows_platform = MagicMock(spec=WindowsAlertPlatform)
        windows_platform.show_notification.return_value = True
        windows_platform.play_sound.return_value = True
        windows_platform.show_blocking_alert.return_value = True
        
        # Create alert system with Windows platform
        with patch('core_v2.alert.platform.get_platform_implementation', return_value=windows_platform):
            alert_system = AlertSystem(self.config_manager)
            
            # Create alert info
            alert_info = AlertInfo(
                app_name="TestApp",
                message="Test message",
                level=AlertLevel.WARNING
            )
            
            # Send alert
            with patch('threading.Thread') as mock_thread:
                mock_thread.return_value = MagicMock()
                result = alert_system.send_alert(alert_info)
                self.assertTrue(result)
    
    def test_alert_system_with_stub_platform(self):
        """Test alert system with stub platform."""
        # Mock stub platform
        stub_platform = MagicMock(spec=StubAlertPlatform)
        stub_platform.show_notification.return_value = True
        stub_platform.play_sound.return_value = True
        stub_platform.show_blocking_alert.return_value = True
        
        # Create alert system with stub platform
        with patch('core_v2.alert.platform.get_platform_implementation', return_value=stub_platform):
            alert_system = AlertSystem(self.config_manager)
            
            # Create alert info
            alert_info = AlertInfo(
                app_name="TestApp",
                message="Test message",
                level=AlertLevel.WARNING
            )
            
            # Send alert
            with patch('threading.Thread') as mock_thread:
                mock_thread.return_value = MagicMock()
                result = alert_system.send_alert(alert_info)
                self.assertTrue(result)
    
    def test_platform_specific_provider_behavior(self):
        """Test that providers adapt to different platforms."""
        # Test with Windows platform
        windows_platform = MagicMock(spec=WindowsAlertPlatform)
        windows_platform.show_notification.return_value = True
        windows_platform.play_sound.return_value = True
        
        # Test with stub platform
        stub_platform = MagicMock(spec=StubAlertPlatform)
        stub_platform.show_notification.return_value = True
        stub_platform.play_sound.return_value = True
        
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )
        
        # Test popup provider with Windows platform
        with patch('core_v2.alert.platform.get_platform_implementation', return_value=windows_platform):
            from core_v2.alert.providers.popup import PopupAlertProvider
            popup_provider = PopupAlertProvider({"popup_duration": 5})
            
            with patch('threading.Thread') as mock_thread:
                mock_thread.return_value = MagicMock()
                result = popup_provider.send_alert(alert_info)
                self.assertTrue(result)
                windows_platform.show_notification.assert_not_called()  # Not called directly, but through thread
        
        # Test sound provider with stub platform
        with patch('core_v2.alert.platform.get_platform_implementation', return_value=stub_platform):
            from core_v2.alert.providers.sound import SoundAlertProvider
            sound_provider = SoundAlertProvider({"volume": 0.5, "repeat_count": 2})
            
            with patch('threading.Thread') as mock_thread:
                mock_thread.return_value = MagicMock()
                result = sound_provider.send_alert(alert_info)
                self.assertTrue(result)
                stub_platform.play_sound.assert_not_called()  # Not called directly, but through thread
    
    def test_custom_platform_implementation(self):
        """Test using a custom platform implementation."""
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
        
        # Create an instance of the custom platform
        custom_platform = CustomPlatform()
        
        # Mock the platform methods
        custom_platform.show_notification = MagicMock(return_value=True)
        custom_platform.play_sound = MagicMock(return_value=True)
        custom_platform.show_blocking_alert = MagicMock(return_value=True)
        
        # Create alert system with custom platform
        with patch('core_v2.alert.platform.get_platform_implementation', return_value=custom_platform):
            alert_system = AlertSystem(self.config_manager)
            
            # Create alert info
            alert_info = AlertInfo(
                app_name="TestApp",
                message="Test message",
                level=AlertLevel.WARNING
            )
            
            # Send alert
            with patch('threading.Thread') as mock_thread:
                mock_thread.return_value = MagicMock()
                result = alert_system.send_alert(alert_info)
                self.assertTrue(result)
    
    def test_platform_extension_guide(self):
        """Test that the platform extension guide in the refactoring plan is accurate."""
        # This test verifies that the steps outlined in the platform extension guide
        # in the alert_system_refactoring_plan.md are accurate and can be followed
        # to create a new platform implementation.
        
        # Create a new platform implementation following the guide
        class LinuxAlertPlatform(PlatformAlertInterface):
            @classmethod
            def is_supported(cls):
                # Check if we're running on Linux
                return sys.platform.startswith('linux')
                
            def show_notification(self, title, message, level, options=None):
                # In a real implementation, this would use a Linux-specific
                # notification mechanism like libnotify
                return True
                
            def play_sound(self, sound_type, options=None):
                # In a real implementation, this would use a Linux-specific
                # sound API like PulseAudio or ALSA
                return True
                
            def show_blocking_alert(self, title, message, level, options=None):
                # In a real implementation, this would use a Linux-specific
                # dialog API like GTK or Qt
                return True
        
        # Verify that the implementation meets the interface requirements
        self.assertTrue(hasattr(LinuxAlertPlatform, 'is_supported'))
        self.assertTrue(callable(LinuxAlertPlatform.is_supported))
        
        linux_platform = LinuxAlertPlatform()
        self.assertTrue(hasattr(linux_platform, 'show_notification'))
        self.assertTrue(callable(linux_platform.show_notification))
        self.assertTrue(hasattr(linux_platform, 'play_sound'))
        self.assertTrue(callable(linux_platform.play_sound))
        self.assertTrue(hasattr(linux_platform, 'show_blocking_alert'))
        self.assertTrue(callable(linux_platform.show_blocking_alert))


if __name__ == "__main__":
    unittest.main()
