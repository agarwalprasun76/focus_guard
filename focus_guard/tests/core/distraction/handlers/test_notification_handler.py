"""
Tests for the notification alert handler.

This module contains tests for the NotificationHandler class.
"""

import unittest
from unittest.mock import MagicMock
from datetime import datetime

from focus_guard.core.distraction.models import DistractionAlert, AlertLevel
from focus_guard.core.distraction.handlers.notification_handler import NotificationHandler
from focus_guard.core.alert.providers.base import AlertProvider


class TestNotificationHandler(unittest.TestCase):
    """Tests for the NotificationHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.alert_provider = MagicMock(spec=AlertProvider)
        self.handler = NotificationHandler(
            alert_provider=self.alert_provider,
            min_level=AlertLevel.WARNING,
            cooldown_seconds=60
        )
    
    def test_can_handle_sufficient_level(self):
        """Test can_handle with sufficient alert level."""
        # Create an alert with WARNING level
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.WARNING,
            message="Test message",
            metadata={"key": "value"},
            timestamp=datetime.now()
        )
        
        # Test can_handle
        self.assertTrue(self.handler.can_handle(alert))
        
        # Create an alert with CRITICAL level
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.CRITICAL,
            message="Test message",
            metadata={"key": "value"},
            timestamp=datetime.now()
        )
        
        # Test can_handle
        self.assertTrue(self.handler.can_handle(alert))
    
    def test_can_handle_insufficient_level(self):
        """Test can_handle with insufficient alert level."""
        # Create an alert with INFO level
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.INFO,
            message="Test message",
            metadata={"key": "value"},
            timestamp=datetime.now()
        )
        
        # Test can_handle
        self.assertFalse(self.handler.can_handle(alert))
    
    def test_can_handle_cooldown(self):
        """Test can_handle with cooldown period."""
        # Create an alert
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.WARNING,
            message="Test message",
            metadata={"key": "value"},
            timestamp=datetime.now()
        )
        
        # Handle the alert
        self.handler.handle(alert)
        
        # Test can_handle during cooldown
        self.assertFalse(self.handler.can_handle(alert))
    
    def test_handle(self):
        """Test handle method."""
        # Create an alert
        alert = DistractionAlert(
            rule_name="Test Rule",
            level=AlertLevel.WARNING,
            message="Test message",
            metadata={"key": "value"},
            timestamp=datetime.now()
        )
        
        # Handle the alert
        self.handler.handle(alert)
        
        # Verify alert was sent
        self.alert_provider.send_alert.assert_called_once()
        alert_info = self.alert_provider.send_alert.call_args[0][0]
        self.assertEqual(alert_info.app_name, "Focus Guard")
        self.assertEqual(alert_info.message, "Test message")
        self.assertEqual(alert_info.level, "warning")
        self.assertEqual(alert_info.context["rule_name"], "Test Rule")
    
    def test_get_notification_level(self):
        """Test _get_notification_level method."""
        self.assertEqual(self.handler._get_notification_level(AlertLevel.INFO), "info")
        self.assertEqual(self.handler._get_notification_level(AlertLevel.WARNING), "warning")
        self.assertEqual(self.handler._get_notification_level(AlertLevel.CRITICAL), "error")


if __name__ == "__main__":
    unittest.main()
