"""
Unit tests for stub alert platform.

This module contains tests for the stub platform implementation.
"""

import unittest
from focus_guard.core.alert.platform.stub import StubAlertPlatform


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


if __name__ == "__main__":
    unittest.main()
