"""
Unit tests for sound alert provider.

This module contains tests for the SoundAlertProvider class.
"""

import unittest
import time
from unittest.mock import patch, MagicMock

from focus_guard.core.alert.models import AlertInfo, AlertLevel
from focus_guard.core.alert.providers.sound import SoundAlertProvider


class TestSoundAlertProvider(unittest.TestCase):
    """Tests for the SoundAlertProvider class."""
    
    def setUp(self):
        """Set up test environment."""
        self.platform = MagicMock()
        self.provider = SoundAlertProvider({"volume": 0.5, "repeat_count": 2})
        self.provider.platform = self.platform
    
    @patch('threading.Thread')
    def test_send_alert(self, mock_thread):
        """Test sending a sound alert."""
        # Mock thread to avoid actual execution
        mock_thread.return_value = MagicMock()
        
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time()
        )
        
        # Send alert
        result = self.provider.send_alert(alert_info)
        self.assertTrue(result)
        mock_thread.assert_called_once()
    
    def test_play_sound(self):
        """Test playing a sound."""
        # Play sound
        self.provider._play_sound("warning", {"volume": 0.5, "repeat_count": 2})
        
        # Check that platform.play_sound was called
        self.platform.play_sound.assert_called_once_with("warning", {"volume": 0.5, "repeat_count": 2})


if __name__ == "__main__":
    unittest.main()
