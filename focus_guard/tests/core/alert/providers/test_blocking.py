"""
Unit tests for blocking alert provider.

This module contains tests for the BlockingAlertProvider class.
"""

import unittest
import time
from unittest.mock import patch, MagicMock

from focus_guard.core.alert.models import AlertInfo, AlertLevel
from focus_guard.core.alert.providers.blocking import BlockingAlertProvider


class TestBlockingAlertProvider(unittest.TestCase):
    """Tests for the BlockingAlertProvider class."""
    
    def setUp(self):
        """Set up test environment."""
        self.platform = MagicMock()
        self.provider = BlockingAlertProvider({
            "timeout": 10,
            "buttons": ["OK", "Cancel"],
            "default_button": 0,
            "min_level": "warning"
        })
        self.provider.platform = self.platform
    
    def test_send_alert(self):
        """Test sending a blocking alert."""
        # Mock platform.show_blocking_alert
        self.platform.show_blocking_alert.return_value = True
        
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
        
        # Check that platform.show_blocking_alert was called
        self.platform.show_blocking_alert.assert_called_once()
        args = self.platform.show_blocking_alert.call_args[0]
        self.assertIn("FocusGuard Alert", args[0])  # Title
        self.assertEqual("Test message", args[1])   # Message
        self.assertEqual("warning", args[2])        # Level
    
    def test_min_level_filtering(self):
        """Test that alerts below min_level are filtered."""
        # Create alert info with normal level
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.NORMAL,
            timestamp=time.time()
        )
        
        # Send alert
        result = self.provider.send_alert(alert_info)
        self.assertFalse(result)
        
        # Check that platform.show_blocking_alert was not called
        self.platform.show_blocking_alert.assert_not_called()
    
    def test_escalation(self):
        """Test alert escalation."""
        # Mock platform.show_blocking_alert
        self.platform.show_blocking_alert.return_value = True
        
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time()
        )
        
        # Send multiple alerts to trigger escalation
        for _ in range(self.provider.escalation_threshold + 1):
            self.provider.send_alert(alert_info)
        
        # Check that the last call included escalation message
        last_call = self.platform.show_blocking_alert.call_args
        self.assertIn("[ESCALATED]", last_call[0][1])


if __name__ == "__main__":
    unittest.main()
