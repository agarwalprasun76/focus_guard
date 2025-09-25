"""
Unit tests for webhook alert provider.

This module contains tests for the WebhookAlertProvider class.
"""

import unittest
import time
import json
from unittest.mock import patch, MagicMock

from core_v2.alert.models import AlertInfo, AlertLevel
from core_v2.alert.providers.webhook import WebhookAlertProvider


class TestWebhookAlertProvider(unittest.TestCase):
    """Tests for the WebhookAlertProvider class."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = {
            "enabled": True,
            "urls": ["https://example.com/webhook"],
            "headers": {"Content-type": "application/json"},
            "method": "POST",
            "include_window_info": True,
            "min_level": "warning",
            "cooldown_period": 60
        }
        self.provider = WebhookAlertProvider(self.config)
    
    def test_initialization(self):
        """Test provider initialization."""
        self.assertTrue(self.provider.enabled)
        self.assertEqual(self.provider.urls, ["https://example.com/webhook"])
        self.assertEqual(self.provider.headers, {"Content-type": "application/json"})
        self.assertEqual(self.provider.method, "POST")
        self.assertTrue(self.provider.include_window_info)
        self.assertEqual(self.provider.min_level, AlertLevel.WARNING)
        self.assertEqual(self.provider.cooldown_period, 60)
    
    def test_is_configured(self):
        """Test is_configured method."""
        # The webhook provider doesn't have an _is_configured method
        # Instead, it checks if URLs are configured in send_alert
        
        # Test with URLs configured
        self.assertTrue(bool(self.provider.urls))
        
        # Test with incomplete configuration
        provider = WebhookAlertProvider({
            "enabled": True,
            # Missing urls
        })
        self.assertFalse(bool(provider.urls))
    
    @patch('threading.Thread')
    def test_send_alert(self, mock_thread):
        """Test sending a webhook alert."""
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
    
    def test_level_filtering(self):
        """Test alert level filtering."""
        # Create alert info with normal level (below min_level)
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.NORMAL,
            timestamp=time.time()
        )
        
        # Send alert
        result = self.provider.send_alert(alert_info)
        self.assertFalse(result)
    
    @patch('urllib.request.urlopen')
    def test_send_webhook_request(self, mock_urlopen):
        """Test sending a webhook request."""
        # Mock urlopen
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time(),
            window_title="Test Window",
            window_url="http://example.com"
        )
        
        # Create payload
        payload = self.provider._create_payload(alert_info)
        
        # Send webhook request
        self.provider._send_webhook(self.provider.urls[0], payload)
        
        # Check that urlopen was called
        mock_urlopen.assert_called_once()
        
        # Verify the request object
        request_obj = mock_urlopen.call_args[0][0]
        self.assertEqual(request_obj.full_url, self.provider.urls[0])
        self.assertEqual(request_obj.method, self.provider.method)
        self.assertEqual(request_obj.headers, self.provider.headers)
    
    def test_cooldown_period(self):
        """Test cooldown period."""
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time()
        )
        
        # Send first alert
        with patch('threading.Thread') as mock_thread:
            mock_thread.return_value = MagicMock()
            result1 = self.provider.send_alert(alert_info)
            self.assertTrue(result1)
        
        # Send second alert immediately (should be blocked by cooldown)
        with patch('threading.Thread') as mock_thread:
            result2 = self.provider.send_alert(alert_info)
            self.assertFalse(result2)
            mock_thread.assert_not_called()
        
        # Simulate cooldown period passed
        url = self.provider.urls[0]
        self.provider.last_webhook_times[url] = time.time() - self.provider.cooldown_period - 1
        
        # Send third alert (should work)
        with patch('threading.Thread') as mock_thread:
            mock_thread.return_value = MagicMock()
            result3 = self.provider.send_alert(alert_info)
            self.assertTrue(result3)
            mock_thread.assert_called_once()
    
    def test_add_webhook_url(self):
        """Test adding a webhook URL."""
        self.provider.add_url("https://example.com/webhook2")
        self.assertIn("https://example.com/webhook2", self.provider.urls)
        self.assertEqual(self.provider.config["urls"], self.provider.urls)
    
    def test_remove_webhook_url(self):
        """Test removing a webhook URL."""
        # Add a URL first
        self.provider.add_url("https://example.com/webhook2")
        
        # Remove URL
        result = self.provider.remove_url("https://example.com/webhook2")
        self.assertTrue(result)
        self.assertNotIn("https://example.com/webhook2", self.provider.urls)
        self.assertEqual(self.provider.config["urls"], self.provider.urls)
        
        # Remove non-existent URL
        result = self.provider.remove_url("https://nonexistent.com")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
