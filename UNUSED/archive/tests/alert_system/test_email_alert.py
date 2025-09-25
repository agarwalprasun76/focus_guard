"""
Unit tests for email alert provider.
These tests verify the functionality of the email alert provider in isolation.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import tempfile
import json
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.alert_system.email_alert import EmailAlertProvider

class TestEmailAlertProvider(unittest.TestCase):
    """Test cases for EmailAlertProvider."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = {
            "email_recipient": "agarwalprasun@gmail.com",  # Parent's email address
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "focusguardapp@gmail.com",  # App's email address
            "smtp_password": "roundCamp33",  # Replace with actual app password for testing
            "use_tls": True,
            "from_name": "FocusGuard App",
            "subject_prefix": "FocusGuard Alert",
            "max_emails_per_day": 5
        }
        self.window_info = {
            "app_name": "TestApp",
            "window_title": "Test Window",
            "pid": 12345,
            "timestamp": datetime.now().isoformat()
        }
        self.message = "Test email alert message"
        
    def test_initialization(self):
        """Test provider initialization."""
        provider = EmailAlertProvider(self.config)
        self.assertTrue(provider.enabled)
        self.assertEqual(provider.email_count, 0)
        self.assertEqual(provider.max_emails_per_day, 5)
        
    def test_disabled_provider(self):
        """Test that disabled provider doesn't send alerts."""
        provider = EmailAlertProvider({"enabled": False})
        # Override the enabled property directly
        provider.enabled = False
        result = provider.send_alert(self.window_info, self.message, "normal")
        self.assertFalse(result)
        
    def test_missing_configuration(self):
        """Test that provider is disabled when required configuration is missing."""
        # Test with missing email_recipient
        provider = EmailAlertProvider({
            "smtp_server": "smtp.gmail.com",
            "smtp_username": "test@example.com",
            "smtp_password": "password"
        })
        self.assertFalse(provider.enabled)
        
        # Test with missing smtp_server
        provider = EmailAlertProvider({
            "email_recipient": "test@example.com",
            "smtp_username": "test@example.com",
            "smtp_password": "password"
        })
        self.assertFalse(provider.enabled)
        
        # Test with missing smtp_username
        provider = EmailAlertProvider({
            "email_recipient": "test@example.com",
            "smtp_server": "smtp.gmail.com",
            "smtp_password": "password"
        })
        self.assertFalse(provider.enabled)
        
        # Test with missing smtp_password
        provider = EmailAlertProvider({
            "email_recipient": "test@example.com",
            "smtp_server": "smtp.gmail.com",
            "smtp_username": "test@example.com"
        })
        self.assertFalse(provider.enabled)
        
    @patch('smtplib.SMTP')
    def test_send_alert_tls(self, mock_smtp):
        """Test sending an alert with TLS."""
        # Configure the mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        provider = EmailAlertProvider(self.config)
        result = provider.send_alert(self.window_info, self.message, "normal")
        
        # Verify SMTP was used correctly
        mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with(
            "focusguardapp@gmail.com", 
            "roundCamp33"
        )
        mock_smtp_instance.send_message.assert_called_once()
        mock_smtp_instance.quit.assert_called_once()
        
        # Verify result
        self.assertTrue(result)
        
        # Verify email count was incremented
        self.assertEqual(provider.email_count, 1)
        
    @patch('smtplib.SMTP_SSL')
    def test_send_alert_ssl(self, mock_smtp_ssl):
        """Test sending an alert with SSL."""
        # Configure the mock
        mock_smtp_instance = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp_instance
        
        # Configure provider to use SSL
        config = self.config.copy()
        config["use_tls"] = False
        config["use_ssl"] = True
        
        provider = EmailAlertProvider(config)
        result = provider.send_alert(self.window_info, self.message, "normal")
        
        # Verify SMTP_SSL was used correctly
        mock_smtp_ssl.assert_called_once_with("smtp.gmail.com", 587)
        mock_smtp_instance.login.assert_called_once_with(
            "focusguardapp@gmail.com", 
            "roundCamp33"
        )
        mock_smtp_instance.send_message.assert_called_once()
        mock_smtp_instance.quit.assert_called_once()
        
        # Verify result
        self.assertTrue(result)
        
    @patch('smtplib.SMTP')
    def test_email_content_formatting(self, mock_smtp):
        """Test that email content is formatted correctly."""
        # Configure the mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        # Capture the email message
        def capture_message(msg):
            self.email_message = msg
            
        mock_smtp_instance.send_message.side_effect = capture_message
        
        provider = EmailAlertProvider(self.config)
        provider.send_alert(self.window_info, self.message, "normal")
        
        # Verify email headers
        self.assertEqual(self.email_message["Subject"], "FocusGuard Alert - Normal")
        self.assertEqual(self.email_message["To"], "agarwalprasun@gmail.com")
        
        # Verify email content contains key information
        content = self.email_message.get_content()
        self.assertIn("FocusGuard Distraction Alert", content)
        self.assertIn("Level: NORMAL", content)
        self.assertIn("Message: Test email alert message", content)
        self.assertIn("Application: TestApp", content)
        self.assertIn("Window Title: Test Window", content)
        
    @patch('smtplib.SMTP')
    def test_email_daily_limit(self, mock_smtp):
        """Test that daily email limit is enforced."""
        # Configure the mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        provider = EmailAlertProvider(self.config)
        
        # Send emails up to the limit
        for i in range(5):
            result = provider.send_alert(self.window_info, f"Test message {i}", "normal")
            self.assertTrue(result)
            self.assertEqual(provider.email_count, i + 1)
        
        # Try to send one more email
        result = provider.send_alert(self.window_info, "This should not be sent", "normal")
        self.assertFalse(result)
        self.assertEqual(provider.email_count, 5)  # Count should not increase
        
    @patch('smtplib.SMTP')
    def test_alert_levels(self, mock_smtp):
        """Test that different alert levels are handled correctly."""
        # Configure the mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        provider = EmailAlertProvider(self.config)
        
        # Test normal level
        provider.send_alert(self.window_info, self.message, "normal")
        self.assertEqual(mock_smtp_instance.send_message.call_count, 1)
        
        # Test warning level
        provider.send_alert(self.window_info, self.message, "warning")
        self.assertEqual(mock_smtp_instance.send_message.call_count, 2)
        
        # Test critical level
        provider.send_alert(self.window_info, self.message, "critical")
        self.assertEqual(mock_smtp_instance.send_message.call_count, 3)
        
    @patch('smtplib.SMTP')
    def test_smtp_error_handling(self, mock_smtp):
        """Test that SMTP errors are handled gracefully."""
        # Configure the mock to raise an exception
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.login.side_effect = Exception("Authentication failed")
        mock_smtp.return_value = mock_smtp_instance
        
        provider = EmailAlertProvider(self.config)
        result = provider.send_alert(self.window_info, self.message, "normal")
        
        # Verify result is False when SMTP fails
        self.assertFalse(result)
        
        # Verify email count was not incremented
        self.assertEqual(provider.email_count, 0)
        
    @patch('smtplib.SMTP')
    @patch('base64.b64decode')
    def test_screenshot_attachment(self, mock_b64decode, mock_smtp):
        """Test that screenshots are attached correctly."""
        # Configure the mocks
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        
        # Mock the base64 decode to return valid image data
        mock_b64decode.return_value = b'fake_image_data'
        
        # Create window info with screenshot
        window_info_with_screenshot = self.window_info.copy()
        window_info_with_screenshot["screenshot"] = "validbase64encodedscreenshot"
        
        # Configure provider to include screenshots
        config = self.config.copy()
        config["include_screenshot"] = True
        
        provider = EmailAlertProvider(config)
        result = provider.send_alert(window_info_with_screenshot, self.message, "normal")
        
        # Verify result
        self.assertTrue(result)
        
        # Verify base64 decode was called with the screenshot data
        mock_b64decode.assert_called_once_with("validbase64encodedscreenshot")
        
        # Verify send_message was called (email with attachment was sent)
        mock_smtp_instance.send_message.assert_called_once()


class TestEmailAlertIntegration(unittest.TestCase):
    """
    Integration tests for EmailAlertProvider.
    
    These tests actually send emails and should only be run manually.
    Comment out the @unittest.skip decorator to run these tests.
    """
    
    def setUp(self):
        """Set up test environment."""
        self.config = {
            "email_recipient": "agarwalprasun@gmail.com",  # Parent's email address
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "focusguardapp@gmail.com",  # App's email address
            "smtp_password": "",  # Add the app password for focusguardapp@gmail.com here
            "use_tls": True,
            "from_name": "FocusGuard App",
            "subject_prefix": "FocusGuard Alert",
            "max_emails_per_day": 5
        }
        self.window_info = {
            "app_name": "TestApp",
            "window_title": "Test Window",
            "pid": 12345,
            "timestamp": datetime.now().isoformat(),
            "url": "https://example.com/distraction",
            "duration": 120  # 2 minutes
        }
        self.message = "This is a test email from the FocusGuard test suite."
        
    @unittest.skip("Skip actual email sending by default")
    def test_send_real_email(self):
        """Test sending an actual email. Only run manually."""
        # Skip this test if no password is provided
        if not self.config["smtp_password"]:
            self.skipTest("No SMTP password provided")
            
        provider = EmailAlertProvider(self.config)
        result = provider.send_alert(self.window_info, self.message, "normal")
        self.assertTrue(result)
        
    @unittest.skip("Skip actual email sending by default")
    def test_send_real_email_warning(self):
        """Test sending an actual warning email. Only run manually."""
        # Skip this test if no password is provided
        if not self.config["smtp_password"]:
            self.skipTest("No SMTP password provided")
            
        provider = EmailAlertProvider(self.config)
        result = provider.send_alert(self.window_info, self.message, "warning")
        self.assertTrue(result)
        
    @unittest.skip("Skip actual email sending by default")
    def test_send_real_email_critical(self):
        """Test sending an actual critical email. Only run manually."""
        # Skip this test if no password is provided
        if not self.config["smtp_password"]:
            self.skipTest("No SMTP password provided")
            
        provider = EmailAlertProvider(self.config)
        result = provider.send_alert(self.window_info, self.message, "critical")
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
