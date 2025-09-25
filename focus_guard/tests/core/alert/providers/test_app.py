"""
Unit tests for app alert provider.

This module contains tests for the AppAlertProvider class.
"""

import unittest
import time
from unittest.mock import patch, MagicMock

from focus_guard.core.alert.models import AlertInfo, AlertLevel
from focus_guard.core.alert.providers.app import AppAlertProvider


class TestAppAlertProvider(unittest.TestCase):
    """Tests for the AppAlertProvider class."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = {
            "enabled": True,
            "app_id": "com.example.focusguard",
            "api_key": "test_api_key",
            "device_ids": ["device1", "device2"],
            "min_level": "warning",
            "include_window_info": True,
            "cooldown_period": 60
        }
        self.provider = AppAlertProvider(self.config)
    
    def test_initialization(self):
        """Test provider initialization."""
        self.assertTrue(self.provider.enabled)
        self.assertEqual(self.provider.app_id, "com.example.focusguard")
        self.assertEqual(self.provider.api_key, "test_api_key")
        self.assertEqual(self.provider.device_ids, ["device1", "device2"])
        self.assertEqual(self.provider.min_level, AlertLevel.WARNING)
        self.assertTrue(self.provider.include_window_info)
        self.assertEqual(self.provider.cooldown_period, 60)
    
    def test_is_configured(self):
        """Test is_configured method."""
        self.assertTrue(self.provider._is_configured())
        
        # Test with incomplete configuration
        provider = AppAlertProvider({
            "enabled": True,
            # Missing app_id and api_key
        })
        self.assertFalse(provider._is_configured())
    
    def test_send_alert(self):
        """Test sending an app alert."""
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time()
        )
        
        # Send alert
        with patch('logging.Logger.info') as mock_log:
            result = self.provider.send_alert(alert_info)
            self.assertTrue(result)
            # Check that the log was called with the expected message
            self.assertEqual(mock_log.call_count, 2)  # Two log calls are made
            # Check first log call contains APP ALERT STUB
            self.assertIn("[APP ALERT STUB]", mock_log.call_args_list[0][0][0])
            # Check second log call contains SUCCESS
            self.assertIn("[SUCCESS]", mock_log.call_args_list[1][0][0])
    
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
        with patch('logging.Logger.info') as mock_log:
            result1 = self.provider.send_alert(alert_info)
            self.assertTrue(result1)
            self.assertEqual(mock_log.call_count, 2)  # Two log calls are made
        
        # Send second alert immediately (should be blocked by cooldown)
        with patch('logging.Logger.info') as mock_log:
            result2 = self.provider.send_alert(alert_info)
            self.assertFalse(result2)
            mock_log.assert_not_called()
        
        # Simulate cooldown period passed
        self.provider.last_alert_time = time.time() - self.provider.cooldown_period - 1
        
        # Send third alert (should work)
        with patch('logging.Logger.info') as mock_log:
            result3 = self.provider.send_alert(alert_info)
            self.assertTrue(result3)
            self.assertEqual(mock_log.call_count, 2)  # Two log calls are made
    
    def test_add_device(self):
        """Test adding a device."""
        self.provider.add_device("device3")
        self.assertIn("device3", self.provider.device_ids)
        self.assertEqual(self.provider.config["device_ids"], self.provider.device_ids)
    
    def test_remove_device(self):
        """Test removing a device."""
        # Add a device first
        self.provider.add_device("device3")
        
        # Remove device
        result = self.provider.remove_device("device3")
        self.assertTrue(result)
        self.assertNotIn("device3", self.provider.device_ids)
        self.assertEqual(self.provider.config["device_ids"], self.provider.device_ids)
        
        # Remove non-existent device
        result = self.provider.remove_device("nonexistent")
        self.assertFalse(result)
    
    def test_set_api_credentials(self):
        """Test setting API credentials."""
        self.provider.set_api_credentials("new_app_id", "new_api_key")
        self.assertEqual(self.provider.app_id, "new_app_id")
        self.assertEqual(self.provider.api_key, "new_api_key")
        self.assertEqual(self.provider.config["app_id"], "new_app_id")
        self.assertEqual(self.provider.config["api_key"], "new_api_key")


if __name__ == "__main__":
    unittest.main()
