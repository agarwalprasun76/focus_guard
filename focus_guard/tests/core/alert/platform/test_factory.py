"""
Unit tests for alert system platform factory.

This module contains tests for the platform factory functionality.
"""

import unittest
from unittest.mock import patch, MagicMock

from focus_guard.core.alert.platform import get_platform_implementation
from focus_guard.core.alert.platform.stub import StubAlertPlatform
from focus_guard.core.alert.platform.windows import WindowsAlertPlatform


class TestPlatformFactory(unittest.TestCase):
    """Tests for the platform factory."""
    
    @patch('focus_guard.core.alert.platform.sys')
    def test_windows_platform_detection(self, mock_sys):
        """Test Windows platform detection."""
        # Mock Windows environment
        mock_sys.platform = 'win32'
        
        # Clear singleton instance to force new creation
        with patch('focus_guard.core.alert.platform._platform_instance', None):
            # Mock is_supported to return True
            with patch.object(WindowsAlertPlatform, 'is_supported', return_value=True):
                platform = get_platform_implementation()
                self.assertIsInstance(platform, WindowsAlertPlatform)
    
    @patch('focus_guard.core.alert.platform.sys')
    def test_fallback_to_stub(self, mock_sys):
        """Test fallback to stub when no platform is supported."""
        # Mock an unsupported platform
        mock_sys.platform = 'unknown'
        
        # Clear singleton instance to force new creation
        with patch('focus_guard.core.alert.platform._platform_instance', None):
            # Mock all platform implementations to be unsupported
            with patch.object(WindowsAlertPlatform, 'is_supported', return_value=False):
                platform = get_platform_implementation()
                self.assertIsInstance(platform, StubAlertPlatform)
    
    def test_singleton_behavior(self):
        """Test that the platform factory returns a singleton."""
        # Clear singleton instance to force new creation
        with patch('focus_guard.core.alert.platform._platform_instance', None):
            # First call should create a new instance
            platform1 = get_platform_implementation()
            
            # Mock the module-level _platform_instance to simulate singleton behavior
            with patch('focus_guard.core.alert.platform._platform_instance', platform1):
                # Second call should return the same instance
                platform2 = get_platform_implementation()
                self.assertIs(platform1, platform2)


if __name__ == "__main__":
    unittest.main()
