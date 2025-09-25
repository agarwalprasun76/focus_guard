"""
Unit tests for base alert providers.

This module contains tests for the base AlertProvider classes.
"""

import unittest
import time
from unittest.mock import patch, MagicMock

from core_v2.alert.models import AlertInfo, AlertLevel
from core_v2.alert.providers.base import AlertProvider, CompositeAlertProvider, ConditionalAlertProvider


class MockAlertProvider(AlertProvider):
    """Mock alert provider for testing."""
    
    def __init__(self, config=None, name=None):
        super().__init__(config)
        if name:
            self.name = name
        self.alerts = []
    
    def send_alert(self, alert_info):
        self.alerts.append(alert_info)
        return True
    
    def get_alerts(self):
        return self.alerts


class TestAlertProvider(unittest.TestCase):
    """Tests for the base AlertProvider class."""
    
    def setUp(self):
        """Set up test environment."""
        self.provider = MockAlertProvider({"enabled": True})
    
    def test_initialization(self):
        """Test provider initialization."""
        self.assertTrue(self.provider.enabled)
        self.assertEqual(self.provider.name, "MockAlertProvider")
    
    def test_is_enabled(self):
        """Test is_enabled method."""
        self.assertTrue(self.provider.is_enabled())
        
        # Disable provider
        self.provider.enabled = False
        self.assertFalse(self.provider.is_enabled())
    
    def test_configure(self):
        """Test configure method."""
        self.provider.configure({"enabled": False, "test_option": "value"})
        self.assertFalse(self.provider.enabled)
        self.assertEqual(self.provider.config["test_option"], "value")
    
    def test_get_name(self):
        """Test get_name method."""
        self.assertEqual(self.provider.get_name(), "MockAlertProvider")
        
        # Custom name
        provider = MockAlertProvider(name="CustomName")
        self.assertEqual(provider.get_name(), "CustomName")


class TestCompositeAlertProvider(unittest.TestCase):
    """Tests for the CompositeAlertProvider class."""
    
    def setUp(self):
        """Set up test environment."""
        self.provider1 = MockAlertProvider(name="Provider1")
        self.provider2 = MockAlertProvider(name="Provider2")
        self.composite = CompositeAlertProvider()
    
    def test_add_provider(self):
        """Test adding providers."""
        self.composite.add_provider(self.provider1)
        self.composite.add_provider(self.provider2)
        self.assertEqual(len(self.composite.providers), 2)
    
    def test_remove_provider(self):
        """Test removing providers."""
        self.composite.add_provider(self.provider1)
        self.composite.add_provider(self.provider2)
        
        # Remove provider
        result = self.composite.remove_provider("Provider1")
        self.assertTrue(result)
        self.assertEqual(len(self.composite.providers), 1)
        self.assertEqual(self.composite.providers[0].get_name(), "Provider2")
        
        # Remove non-existent provider
        result = self.composite.remove_provider("NonExistent")
        self.assertFalse(result)
    
    def test_send_alert(self):
        """Test sending alerts to child providers."""
        self.composite.add_provider(self.provider1)
        self.composite.add_provider(self.provider2)
        
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time()
        )
        
        # Send alert
        result = self.composite.send_alert(alert_info)
        self.assertTrue(result)
        
        # Check that both providers received the alert
        self.assertEqual(len(self.provider1.get_alerts()), 1)
        self.assertEqual(len(self.provider2.get_alerts()), 1)
        self.assertEqual(self.provider1.get_alerts()[0], alert_info)
        self.assertEqual(self.provider2.get_alerts()[0], alert_info)
    
    def test_disabled_provider(self):
        """Test that disabled providers don't receive alerts."""
        self.provider1.enabled = False
        self.composite.add_provider(self.provider1)
        self.composite.add_provider(self.provider2)
        
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time()
        )
        
        # Send alert
        result = self.composite.send_alert(alert_info)
        self.assertTrue(result)
        
        # Check that only enabled provider received the alert
        self.assertEqual(len(self.provider1.get_alerts()), 0)
        self.assertEqual(len(self.provider2.get_alerts()), 1)
    
    def test_disabled_composite(self):
        """Test that disabled composite doesn't send alerts."""
        self.composite.enabled = False
        self.composite.add_provider(self.provider1)
        self.composite.add_provider(self.provider2)
        
        # Create alert info
        alert_info = AlertInfo(
            app_name="TestApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time()
        )
        
        # Send alert
        result = self.composite.send_alert(alert_info)
        self.assertFalse(result)
        
        # Check that no providers received the alert
        self.assertEqual(len(self.provider1.get_alerts()), 0)
        self.assertEqual(len(self.provider2.get_alerts()), 0)


class TestConditionalAlertProvider(unittest.TestCase):
    """Tests for the ConditionalAlertProvider class."""
    
    def setUp(self):
        """Set up test environment."""
        self.wrapped_provider = MockAlertProvider()
        self.conditional = ConditionalAlertProvider(
            {
                "min_level": "warning",
                "app_whitelist": ["AllowedApp"],
                "app_blacklist": ["BlockedApp"]
            },
            self.wrapped_provider
        )
    
    def test_level_condition(self):
        """Test alert level condition."""
        # Reset the wrapped provider's alerts
        self.wrapped_provider.alerts = []
        
        # Create a new conditional provider with only min_level set
        # This ensures we're only testing the level condition
        from core_v2.alert.providers.base import ConditionalAlertProvider
        conditional = ConditionalAlertProvider(
            {
                "min_level": "warning",
                # No app whitelist or blacklist
            },
            self.wrapped_provider
        )
        
        # Create alerts with different levels
        from datetime import datetime
        timestamp = datetime.now()
        
        normal_alert = AlertInfo(
            app_name="TestApp",
            message="Normal message",
            level=AlertLevel.NORMAL,
            timestamp=timestamp
        )
        
        warning_alert = AlertInfo(
            app_name="TestApp",
            message="Warning message",
            level=AlertLevel.WARNING,
            timestamp=timestamp
        )
        
        # Send alerts
        normal_result = conditional.send_alert(normal_alert)
        warning_result = conditional.send_alert(warning_alert)
        
        # Check results
        self.assertFalse(normal_result)  # Below min_level
        self.assertTrue(warning_result)  # At min_level
        
        # Check that only warning alert was forwarded
        alerts = self.wrapped_provider.get_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0], warning_alert)
    
    def test_app_whitelist(self):
        """Test app whitelist condition."""
        # Create alerts for different apps
        allowed_alert = AlertInfo(
            app_name="AllowedApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time()
        )
        
        other_alert = AlertInfo(
            app_name="OtherApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=time.time()
        )
        
        # Send alerts
        allowed_result = self.conditional.send_alert(allowed_alert)
        other_result = self.conditional.send_alert(other_alert)
        
        # Check results
        self.assertTrue(allowed_result)  # In whitelist
        self.assertFalse(other_result)   # Not in whitelist
        
        # Check that only allowed alert was forwarded
        alerts = self.wrapped_provider.get_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0], allowed_alert)
    
    def test_app_blacklist(self):
        """Test app blacklist condition."""
        # Reset the wrapped provider's alerts
        self.wrapped_provider.alerts = []
        
        # Create a new conditional provider with only blacklist
        conditional = ConditionalAlertProvider(
            {
                "min_level": "normal",
                "app_blacklist": ["BlockedApp"]
            },
            self.wrapped_provider
        )
        
        # Create alerts for different apps
        from datetime import datetime
        timestamp = datetime.now()
        
        blocked_alert = AlertInfo(
            app_name="BlockedApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=timestamp
        )
        
        allowed_alert = AlertInfo(
            app_name="AllowedApp",
            message="Test message",
            level=AlertLevel.WARNING,
            timestamp=timestamp
        )
        
        # Send alerts
        blocked_result = conditional.send_alert(blocked_alert)
        allowed_result = conditional.send_alert(allowed_alert)
        
        # Check results
        self.assertFalse(blocked_result)  # In blacklist
        self.assertTrue(allowed_result)   # Not in blacklist
        
        # Check that only allowed alert was forwarded
        self.assertEqual(len(self.wrapped_provider.get_alerts()), 1)  # Only the allowed alert


if __name__ == "__main__":
    unittest.main()
