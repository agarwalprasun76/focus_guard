"""
Unit tests for alert system platform implementations.

This module contains tests for the platform interface and implementations.
"""

import unittest
import sys
from unittest.mock import patch, MagicMock

from core_v2.alert.platform.base import PlatformAlertInterface
from core_v2.alert.platform import get_platform_implementation
from core_v2.alert.platform.stub import StubAlertPlatform
from core_v2.alert.platform.windows import WindowsAlertPlatform


class TestPlatformInterface(unittest.TestCase):
    """Tests for the platform interface."""
    
    def test_abstract_methods(self):
        """Test that abstract methods are defined."""
        methods = [
            'show_notification',
            'play_sound',
            'show_blocking_alert',
            'is_supported'
        ]
        
        for method in methods:
            self.assertTrue(hasattr(PlatformAlertInterface, method))


class TestPlatformFactory(unittest.TestCase):
    """Tests for the platform factory."""
    
    @patch('core_v2.alert.platform.sys')
    def test_windows_platform_detection(self, mock_sys):
        """Test Windows platform detection."""
        # Reset the platform singleton instance
        from core_v2.alert.platform import _platform_instance
        import core_v2.alert.platform
        core_v2.alert.platform._platform_instance = None
        
        # Mock Windows environment
        mock_sys.platform = 'win32'
        
        # Mock is_supported to return True
        with patch.object(WindowsAlertPlatform, 'is_supported', return_value=True):
            platform = get_platform_implementation()
            self.assertIsInstance(platform, WindowsAlertPlatform)
    
    @patch('core_v2.alert.platform.sys')
    def test_fallback_to_stub(self, mock_sys):
        """Test fallback to stub when no platform is supported."""
        # Mock an unsupported platform
        mock_sys.platform = 'unknown'
        
        # Mock all platform implementations to be unsupported
        with patch.object(WindowsAlertPlatform, 'is_supported', return_value=False):
            platform = get_platform_implementation()
            self.assertIsInstance(platform, StubAlertPlatform)
    
    @patch('core_v2.alert.platform._platform_instance')
    def test_singleton_behavior(self, mock_instance):
        """Test that the platform factory returns a singleton."""
        # First call should create a new instance
        mock_instance.return_value = None
        platform1 = get_platform_implementation()
        
        # Second call should return the same instance
        mock_instance.return_value = platform1
        platform2 = get_platform_implementation()
        
        self.assertIs(platform1, platform2)


class TestStubPlatform(unittest.TestCase):
    """Tests for the stub platform implementation."""
    
    def setUp(self):
        """Set up test environment."""
        self.platform = StubAlertPlatform()
    
    def test_is_supported(self):
        """Test that stub platform is always supported."""
        self.assertTrue(StubAlertPlatform.is_supported())
    
    def test_show_notification(self):
        """Test showing a notification."""
        result = self.platform.show_notification(
            title="Test Title",
            message="Test Message",
            level="normal",
            options={"app_name": "TestApp"}
        )
        self.assertTrue(result)
    
    def test_play_sound(self):
        """Test playing a sound."""
        result = self.platform.play_sound(
            sound_type="normal",
            options={"repeat_count": 2}
        )
        self.assertTrue(result)
    
    def test_show_blocking_alert(self):
        """Test showing a blocking alert."""
        result = self.platform.show_blocking_alert(
            title="Test Title",
            message="Test Message",
            level="warning",
            options={"app_name": "TestApp"}
        )
        self.assertTrue(result)


@unittest.skipIf(sys.platform != 'win32', "Windows-only tests")
class TestWindowsPlatform(unittest.TestCase):
    """Tests for the Windows platform implementation."""
    
    def setUp(self):
        """Set up test environment."""
        # Skip actual instantiation if not on Windows
        if sys.platform == 'win32':
            # Mock is_supported to avoid actual system checks
            with patch.object(WindowsAlertPlatform, 'is_supported', return_value=True):
                self.platform = WindowsAlertPlatform()
    
    def test_is_supported(self):
        """Test Windows platform support detection."""
        # Reset any singleton instance
        from core_v2.alert.platform import _platform_instance
        _platform_instance = None
        
        # Test Windows platform with PowerShell available
        with patch('sys.platform', 'win32'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                self.assertTrue(WindowsAlertPlatform.is_supported())
        
        # Test non-Windows platform
        with patch('sys.platform', 'linux'):
            self.assertFalse(WindowsAlertPlatform.is_supported())
        
        # Test Windows platform with PowerShell not available
        # We need to patch subprocess.run to simulate PowerShell not being available
        with patch('sys.platform', 'win32'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=1)  # Non-zero return code indicates failure
                self.assertFalse(WindowsAlertPlatform.is_supported())
    
    @patch('threading.Thread')
    def test_show_notification(self, mock_thread):
        """Test showing a notification."""
        if not hasattr(self, 'platform'):
            self.skipTest("Not running on Windows")
        
        # Mock thread to avoid actual execution
        mock_thread.return_value = MagicMock()
        
        result = self.platform.show_notification(
            title="Test Title",
            message="Test Message",
            level="normal",
            options={"app_name": "TestApp"}
        )
        
        self.assertTrue(result)
        mock_thread.assert_called_once()
    
    @patch('threading.Thread')
    def test_play_sound(self, mock_thread):
        """Test playing a sound."""
        if not hasattr(self, 'platform'):
            self.skipTest("Not running on Windows")
        
        # Mock thread to avoid actual execution
        mock_thread.return_value = MagicMock()
        
        result = self.platform.play_sound(
            sound_type="normal",
            options={"repeat_count": 2}
        )
        
        self.assertTrue(result)
        mock_thread.assert_called_once()
    
    @patch('subprocess.run')
    def test_show_blocking_alert(self, mock_run):
        """Test showing a blocking alert."""
        if not hasattr(self, 'platform'):
            self.skipTest("Not running on Windows")
        
        # Mock subprocess.run to simulate MessageBox
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.platform.show_blocking_alert(
            title="Test Title",
            message="Test Message",
            level="warning",
            options={"app_name": "TestApp"}
        )
        
        self.assertTrue(result)
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_show_blocking_alert_timeout(self, mock_run):
        """Test showing a blocking alert with timeout."""
        if not hasattr(self, 'platform'):
            self.skipTest("Not running on Windows")
        
        # Mock subprocess.run to simulate timeout
        mock_run.side_effect = TimeoutError("Timed out")
        
        result = self.platform.show_blocking_alert(
            title="Test Title",
            message="Test Message",
            level="warning",
            options={"timeout": 1}
        )
        
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
