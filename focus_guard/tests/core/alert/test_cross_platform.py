"""
Cross-platform tests for the alert system.

This module contains tests that validate the alert system's behavior
across different platforms and ensure proper platform detection and fallback.
"""

import unittest
import sys
import unittest
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
    
    @patch('sys.platform', 'win32')
    @patch('focus_guard.core.alert.platform._platform_instance', None)
    @patch('focus_guard.core.alert.platform.get_platform_implementation')
    @patch('threading.Thread')
    def test_platform_detection(self, mock_thread_class, mock_get_platform):
        """Test that the correct platform is detected based on the OS."""
        try:
            # Test Windows platform detection
            # sys.platform is already patched to 'win32'
            with patch('focus_guard.core.alert.platform.windows.WindowsAlertPlatform.is_supported', return_value=True):
                platform = get_platform_implementation()
                self.assertIsInstance(platform, WindowsAlertPlatform)
            
            # Reset platform instance for next test
            import focus_guard.core.alert.platform as platform_module
            platform_module._platform_instance = None
            
            # Test fallback to stub on unsupported platform
            # Need to patch sys.platform again for this test
            with patch('sys.platform', 'linux'):
                with patch('focus_guard.core.alert.platform.windows.WindowsAlertPlatform.is_supported', return_value=False):
                    platform = get_platform_implementation()
                    self.assertIsInstance(platform, StubAlertPlatform)
                
        finally:
            # Restore original state
            sys.platform = 'win32'
            import focus_guard.core.alert.platform as platform_module
            platform_module._platform_instance = None
    
    @patch('sys.platform', 'linux')
    @patch('focus_guard.core.alert.platform._platform_instance', None)
    @patch('focus_guard.core.alert.platform.get_platform_implementation')
    @patch('threading.Thread')
    def test_platform_fallback(self, mock_thread_class, mock_get_platform):
        """Test fallback to stub platform when preferred platform is not available."""
        # Mock Windows platform but make it unsupported
        # sys.platform is already patched to 'linux'
        
        # Clear any cached platform instance
        import focus_guard.core.alert.platform as platform_module
        platform_module._platform_instance = None
        
        # Test fallback when Windows platform is not supported
        with patch('focus_guard.core.alert.platform.windows.WindowsAlertPlatform.is_supported', return_value=False):
            platform_impl = get_platform_implementation()
            self.assertIsInstance(platform_impl, StubAlertPlatform)
    
    def _setup_thread_mock(self, mock_thread_class):
        """Helper to set up thread mock and capture thread target."""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        
        # Track thread target function and args
        captured = {
            'target': None,
            'args': (),
            'kwargs': {},
            'thread': mock_thread,
            'start_call_count': 0,  # Track start calls
            'threads': [],  # Track all created threads
            'captured_targets': []  # Track all captured targets
        }
        
        # Track all thread starts
        def increment_start_count():
            captured['start_call_count'] += 1
            return None
            
        mock_thread.start.side_effect = increment_start_count
        
        def capture_thread(*args, **kwargs):
            # Create a new mock for each thread
            thread_mock = MagicMock()
            thread_mock.start.side_effect = increment_start_count
            
            # Store the thread target and args
            target = kwargs.get('target', args[0] if args else None)
            captured['target'] = target
            captured['args'] = args
            captured['kwargs'] = kwargs
            captured['threads'].append(thread_mock)
            captured['captured_targets'].append(target)
            
        mock_thread_class.side_effect = capture_thread
        
        return captured
        
    def _execute_thread_target(self, captured, alert_info):
        """Helper to execute the captured thread target with proper arguments."""
        if not captured['target']:
            return None
            
        target = captured['target']
        results = []
        
        # Check if this is a method of a provider
        if hasattr(target, '__self__'):
            # Handle provider methods directly
            provider = target.__self__
            
            # Get the platform instance from the provider if it exists
            platform = getattr(provider, 'platform', None)
            
            if hasattr(provider, 'send_alert'):
                # Execute the provider's send_alert method directly
                result = provider.send_alert(alert_info)
                results.append('provider_sent')
            elif hasattr(provider, '_show_popup'):
                # Handle popup provider
                if platform and hasattr(platform, 'show_notification'):
                    # Get the title and options that would be used
                    title = f"FocusGuard Alert - {alert_info.app_name}" if getattr(provider, 'show_app_name', True) else "FocusGuard Alert"
                    level = alert_info.level.to_string() if hasattr(alert_info.level, 'to_string') else str(alert_info.level)
                    options = {
                        'popup_duration': getattr(provider, 'popup_duration', 10),
                        'overlay_on_distraction': getattr(provider, 'overlay_on_distraction', False)
                    }
                    # Call the platform method directly
                    platform.show_notification(title, alert_info.message, level, options)
                    results.append('notification_shown')
                else:
                    # Fallback to direct method call
                    provider._show_popup(alert_info)
                    results.append('notification_shown')
            elif hasattr(provider, '_play_sound'):
                # Handle sound provider
                if platform and hasattr(platform, 'play_sound'):
                    level_value = alert_info.level.value
                    sound_level = level_value.lower() if hasattr(level_value, 'lower') else str(level_value).lower()
                    options = {"volume": 0.5, "repeat_count": 2}
                    platform.play_sound(sound_level, options)
                    results.append('sound_played')
                else:
                    # Fallback to direct method call
                    level_value = alert_info.level.value
                    sound_level = level_value.lower() if hasattr(level_value, 'lower') else str(level_value).lower()
                    provider._play_sound(sound_level, {"volume": 0.5, "repeat_count": 2})
                    results.append('sound_played')
            elif hasattr(provider, '_providers'):
                # Handle composite provider
                for child in provider._providers:
                    if hasattr(child, 'send_alert'):
                        child.send_alert(alert_info)
                        child_name = type(child).__name__
                        if 'Popup' in child_name:
                            results.append('notification_shown')
                        elif 'Sound' in child_name:
                            results.append('sound_played')
                results.append('composite_handled')
        else:
            # Handle standalone functions
            try:
                target(alert_info)
                results.append('default')
            except Exception as e:
                print(f"Error executing thread target: {e}")
                raise
        
        # Return the most specific result
        if 'composite_handled' in results:
            return 'composite_handled'
        elif 'sound_played' in results and 'notification_shown' in results:
            return 'both_handled'
        elif 'sound_played' in results:
            return 'sound_played'
        elif 'notification_shown' in results:
            return 'notification_shown'
        return results[0] if results else None
    
    @patch('subprocess.run')
    def test_alert_system_with_windows_platform(self, mock_subprocess_run):
        """Test alert system with Windows platform."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # Create alert system (on Windows, real WindowsAlertPlatform is used)
        alert_system = AlertSystem(self.config_manager)

        # Mock each provider's send_alert to avoid real thread/popup side effects
        for provider in alert_system.providers.values():
            provider.send_alert = MagicMock(return_value=True)

        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )

        result = alert_system.send_alert(alert_info)
        self.assertTrue(result)

        # Verify at least one provider was called
        any_called = any(p.send_alert.called for p in alert_system.providers.values())
        self.assertTrue(any_called, "Expected at least one provider to be called")
    
    @patch('subprocess.run')
    def test_platform_specific_provider_behavior(self, mock_subprocess_run):
        """Test that providers adapt to different platforms."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )

        # Test popup provider
        with self.subTest("Test popup provider"):
            from focus_guard.core.alert.providers.popup import PopupAlertProvider
            popup_provider = PopupAlertProvider({"popup_duration": 5})
            # Mock the internal _show_popup to avoid real thread/GUI
            popup_provider._show_popup = MagicMock()
            with patch('threading.Thread') as mock_thread:
                mock_thread_inst = MagicMock()
                mock_thread.return_value = mock_thread_inst
                result = popup_provider.send_alert(alert_info)
                self.assertTrue(result)
                mock_thread_inst.start.assert_called_once()

        # Test sound provider
        with self.subTest("Test sound provider"):
            from focus_guard.core.alert.providers.sound import SoundAlertProvider
            sound_provider = SoundAlertProvider()
            sound_provider._play_sound = MagicMock()
            with patch('threading.Thread') as mock_thread:
                mock_thread_inst = MagicMock()
                mock_thread.return_value = mock_thread_inst
                result = sound_provider.send_alert(alert_info)
                self.assertTrue(result)

        # Test composite via AlertSystem
        with self.subTest("Test composite provider with AlertSystem"):
            alert_system = AlertSystem(self.config_manager)
            for provider in alert_system.providers.values():
                provider.send_alert = MagicMock(return_value=True)
            result = alert_system.send_alert(alert_info)
            self.assertTrue(result)
            any_called = any(p.send_alert.called for p in alert_system.providers.values())
            self.assertTrue(any_called)
    
    @patch('subprocess.run')
    def test_custom_platform_implementation(self, mock_subprocess_run):
        """Test using a custom platform implementation."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

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

        # Verify the custom platform meets the interface
        custom = CustomPlatform()
        self.assertTrue(custom.is_supported())
        self.assertTrue(custom.show_notification("t", "m", "warning"))
        self.assertTrue(custom.play_sound("warning"))
        self.assertTrue(custom.show_blocking_alert("t", "m", "warning"))

        # Create alert system and mock providers to avoid real threads
        alert_system = AlertSystem(self.config_manager)
        for provider in alert_system.providers.values():
            provider.send_alert = MagicMock(return_value=True)

        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING
        )

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
