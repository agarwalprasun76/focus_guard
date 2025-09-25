"""
Unit tests for popup alert provider.

This module contains tests for the PopupAlertProvider class.
"""

import unittest
import time
from unittest.mock import patch, MagicMock

from core_v2.alert.models import AlertInfo, AlertLevel
from core_v2.alert.providers.popup import PopupAlertProvider


class TestPopupAlertProvider(unittest.TestCase):
    """Tests for the PopupAlertProvider class."""
    
    def setUp(self):
        """Set up test environment."""
        self.platform = MagicMock()
        self.provider = PopupAlertProvider({"popup_duration": 5})
        self.provider.platform = self.platform
    
    @patch('threading.Thread')
    def test_send_alert(self, mock_thread):
        """Test sending a popup alert."""
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
    
    @patch('time.sleep')
    def test_show_popup(self, mock_sleep):
        """Test showing a popup."""
        # Mock sleep to avoid waiting
        mock_sleep.return_value = None
        
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time()
        )
        
        # Show popup
        self.provider._show_popup(alert_info)
        
        # Check that platform.show_notification was called
        self.platform.show_notification.assert_called_once()
        args = self.platform.show_notification.call_args[0]
        self.assertIn("FocusGuard Alert", args[0])  # Title
        self.assertEqual("Test message", args[1])   # Message
        self.assertEqual("warning", args[2])        # Level


if __name__ == "__main__":
    unittest.main()
