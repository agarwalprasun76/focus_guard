"""
Unit tests for email alert provider.

This module contains tests for the EmailAlertProvider class.
"""

import unittest
import time
from unittest.mock import patch, MagicMock

from core_v2.alert.models import AlertInfo, AlertLevel
from core_v2.alert.providers.email import EmailAlertProvider


class TestEmailAlertProvider(unittest.TestCase):
    """Tests for the EmailAlertProvider class."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = {
            "enabled": True,
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "use_tls": True,
            "username": "test@example.com",
            "password": "password123",
            "sender": "alerts@example.com",
            "recipients": ["user@example.com"],
            "subject_prefix": "[FocusGuard]",
            "min_level": "warning",
            "cooldown_period": 60
        }
        self.provider = EmailAlertProvider(self.config)
    
    def test_initialization(self):
        """Test provider initialization."""
        self.assertTrue(self.provider.enabled)
        self.assertEqual(self.provider.smtp_server, "smtp.example.com")
        self.assertEqual(self.provider.smtp_port, 587)
        self.assertTrue(self.provider.use_tls)
        self.assertEqual(self.provider.username, "test@example.com")
        self.assertEqual(self.provider.password, "password123")
        self.assertEqual(self.provider.sender, "alerts@example.com")
        self.assertEqual(self.provider.recipients, ["user@example.com"])
        self.assertEqual(self.provider.subject_prefix, "[FocusGuard]")
        self.assertEqual(self.provider.min_level, AlertLevel.WARNING)
        self.assertEqual(self.provider.cooldown_period, 60)
    
    def test_is_configured(self):
        """Test is_configured method."""
        self.assertTrue(self.provider._is_configured())
        
        # Test with incomplete configuration
        provider = EmailAlertProvider({
            "enabled": True,
            "smtp_server": "smtp.example.com",
            # Missing other required fields
        })
        self.assertFalse(provider._is_configured())
    
    @patch('threading.Thread')
    def test_send_alert(self, mock_thread):
        """Test sending an email alert."""
        # Mock thread to avoid actual execution
        mock_thread.return_value = MagicMock()
        
        # Create alert info
        from datetime import datetime
        timestamp = datetime.now()
        
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=timestamp
        )
        
        # Send alert
        result = self.provider.send_alert(alert_info)
        self.assertTrue(result)
        mock_thread.assert_called_once()
    
    def test_level_filtering(self):
        """Test alert level filtering."""
        # Create alert info with normal level (below min_level)
        from datetime import datetime
        timestamp = datetime.now()
        
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.NORMAL,
            timestamp=timestamp
        )
        
        # Send alert
        result = self.provider.send_alert(alert_info)
        self.assertFalse(result)
    
    def test_send_email(self):
        """Test sending an email."""
        # Create alert info
        from datetime import datetime
        timestamp = datetime.now()
        
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=timestamp,
            window_title="Test Window"
            # window_url removed as it doesn't exist in the model
        )
        
        # Mock the entire SMTP context
        with patch('smtplib.SMTP') as mock_smtp:
            # Create a mock instance and configure it
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance
            mock_instance.__enter__.return_value = mock_instance
            
            # Send email
            self.provider._send_email(alert_info)
            
            # Verify SMTP was instantiated with correct server and port
            mock_smtp.assert_called_once_with(self.provider.smtp_server, self.provider.smtp_port)
            
            # Verify email was sent
            self.assertTrue(mock_instance.send_message.called, "send_message was not called")
            
            # Check email content
            if mock_instance.send_message.call_args:
                email_msg = mock_instance.send_message.call_args[0][0]
                self.assertEqual(email_msg["From"], self.provider.sender)
                self.assertEqual(email_msg["To"], ", ".join(self.provider.recipients))
                self.assertTrue(email_msg["Subject"].startswith(self.provider.subject_prefix))
    
    def test_cooldown_period(self):
        """Test cooldown period."""
        # Set cooldown period to 60 seconds
        self.provider.cooldown_period = 60
        
        # Create alert info
        from datetime import datetime, timedelta
        timestamp = datetime.now()
        
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=timestamp,
            window_title="Test Window"
        )
        
        # Mock the _send_email method to avoid actual email sending
        with patch.object(self.provider, '_send_email', return_value=True):
            # First alert should be sent
            with patch('threading.Thread'):
                result1 = self.provider.send_alert(alert_info)
                self.assertTrue(result1)
            
            # Second alert within cooldown period should not be sent
            with patch('threading.Thread'):
                result2 = self.provider.send_alert(alert_info)
                self.assertFalse(result2)
            
            # Simulate time passing beyond cooldown period
            self.provider.last_email_time = timestamp - timedelta(seconds=61)
            
            # Third alert after cooldown period should be sent
            with patch('threading.Thread'):
                result3 = self.provider.send_alert(alert_info)
                self.assertTrue(result3)
    
    def test_add_recipient(self):
        """Test adding a recipient."""
        self.provider.add_recipient("new@example.com")
        self.assertIn("new@example.com", self.provider.recipients)
        self.assertEqual(self.provider.config["recipients"], self.provider.recipients)
    
    def test_remove_recipient(self):
        """Test removing a recipient."""
        # Add a recipient first
        self.provider.add_recipient("new@example.com")
        
        # Remove recipient
        result = self.provider.remove_recipient("new@example.com")
        self.assertTrue(result)
        self.assertNotIn("new@example.com", self.provider.recipients)
        self.assertEqual(self.provider.config["recipients"], self.provider.recipients)
        
        # Remove non-existent recipient
        result = self.provider.remove_recipient("nonexistent@example.com")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
