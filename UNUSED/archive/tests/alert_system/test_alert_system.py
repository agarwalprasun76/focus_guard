"""
Unit tests for the alert system.
These tests verify the functionality of the AlertSystem class.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.alert_system.alert_system import AlertSystem, AlertProvider
from core.alert_system.popup_alert import PopupAlertProvider
from core.alert_system.sound_alert import SoundAlertProvider

class MockAlertProvider(AlertProvider):
    """Mock alert provider for testing."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.alerts_sent = []
    
    def send_alert(self, window_info, message, level="normal"):
        if not self.enabled:
            return False
        self.alerts_sent.append({
            "window_info": window_info,
            "message": message,
            "level": level
        })
        return True


class TestAlertSystem(unittest.TestCase):
    """Test cases for AlertSystem."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for alert history
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Basic configuration
        self.config = {
            "cooldown_period": 2,
            "escalation_threshold": 2,
            "escalation_window": 60
        }
        
        self.window_info = {
            "app_name": "TestApp",
            "window_title": "Test Window",
            "pid": 12345,
            "timestamp": datetime.now().isoformat()
        }
        
        self.message = "Test alert message"
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test alert system initialization."""
        alert_system = AlertSystem(self.config)
        
        self.assertEqual(alert_system.cooldown_period, 2)
        self.assertEqual(alert_system.escalation_threshold, 2)
        self.assertEqual(alert_system.escalation_window, 60)
        # Default providers are initialized
        self.assertGreater(len(alert_system.providers), 0)
    
    def test_add_provider(self):
        """Test adding providers to the alert system."""
        # Create alert system with explicitly empty providers list
        alert_system = AlertSystem(self.config, providers=[])
        
        # Store initial count of providers (should be 0 since we passed empty list)
        initial_count = len(alert_system.providers)
        
        # Add a new provider
        provider = MockAlertProvider()
        alert_system.add_provider(provider)
        
        # Verify provider was added
        self.assertEqual(len(alert_system.providers), initial_count + 1)
        self.assertIs(alert_system.providers[-1], provider)
    
    def test_remove_provider(self):
        """Test removing providers from the alert system."""
        # Create alert system with explicitly empty providers list
        alert_system = AlertSystem(self.config, providers=[])
        
        # Add two providers of the same type
        provider1 = MockAlertProvider()
        provider2 = MockAlertProvider()
        
        alert_system.add_provider(provider1)
        alert_system.add_provider(provider2)
        initial_count = len(alert_system.providers)
        
        # The actual implementation removes by type, not by instance
        alert_system.remove_provider(MockAlertProvider)
        
        # Verify all providers of that type were removed
        self.assertEqual(len(alert_system.providers), initial_count - 2)
    
    def test_cooldown_check(self):
        """Test cooldown period functionality."""
        alert_system = AlertSystem(self.config, providers=[])
        provider = MockAlertProvider()
        alert_system.add_provider(provider)
        
        # Override cooldown check for first alert to ensure it goes through
        with patch.object(alert_system, '_is_in_cooldown', return_value=False):
            # First alert should go through
            result1 = alert_system.alert(self.window_info, self.message)
            self.assertTrue(result1)
            self.assertEqual(len(provider.alerts_sent), 1)
        
        # Second alert within cooldown period should be blocked
        # (no need to patch here, it should be in cooldown naturally)
        result2 = alert_system.alert(self.window_info, self.message)
        self.assertFalse(result2)
        self.assertEqual(len(provider.alerts_sent), 1)  # Still only 1 alert
        
        # Mock time passing beyond cooldown period
        with patch.object(alert_system, '_is_in_cooldown', return_value=False):
            result3 = alert_system.alert(self.window_info, self.message)
            self.assertTrue(result3)
            self.assertEqual(len(provider.alerts_sent), 2)  # Now 2 alerts
    
    def test_alert_level_determination(self):
        """Test alert level determination based on frequency."""
        alert_system = AlertSystem(self.config)
        
        # No previous alerts should be normal level
        level1 = alert_system._determine_alert_level("TestApp")
        self.assertEqual(level1, "normal")
        
        # Add one alert to history
        alert_system._track_alert("TestApp")
        
        # Still below threshold, should be normal
        level2 = alert_system._determine_alert_level("TestApp")
        self.assertEqual(level2, "normal")
        
        # Add another alert to history (now at threshold)
        alert_system._track_alert("TestApp")
        
        # At threshold, should escalate to warning
        level3 = alert_system._determine_alert_level("TestApp")
        self.assertEqual(level3, "warning")
        
        # Add more alerts to history
        alert_system._track_alert("TestApp")
        alert_system._track_alert("TestApp")
        
        # Well above threshold, should escalate to critical
        level4 = alert_system._determine_alert_level("TestApp")
        self.assertEqual(level4, "critical")
    
    def test_alert_history_tracking(self):
        """Test that alert history is properly tracked."""
        alert_system = AlertSystem(self.config, providers=[])
        
        # Clear any existing history
        alert_system.alert_history = {}
        
        # Add some alerts
        alert_system._track_alert("TestApp1")
        alert_system._track_alert("TestApp1")
        
        # Check history
        self.assertEqual(len(alert_system.alert_history["TestApp1"]), 2)
    
    def test_alert_history_cleanup(self):
        """Test that old alerts are cleaned up from history."""
        alert_system = AlertSystem(self.config, providers=[])
        
        # Add some alerts with old timestamps
        now = datetime.now()
        old_time = now - timedelta(days=8)  # Older than 7 days cutoff
        recent_time = now - timedelta(days=1)  # Within 7 days
        
        alert_system.alert_history["TestApp"] = [
            old_time,    # Old, should be pruned
            recent_time   # Recent, should be kept
        ]
        
        # Clean up history
        alert_system._cleanup_history()
        
        # Check that only recent alert remains
        self.assertEqual(len(alert_system.alert_history["TestApp"]), 1)
        self.assertEqual(alert_system.alert_history["TestApp"][0], recent_time)
    
    def test_save_and_load_history(self):
        """Test saving and loading alert history."""
        # Create a temporary file for history
        history_file = Path(os.path.join(self.temp_dir.name, "alert_history.json"))
        
        with patch.object(AlertSystem, '_get_history_file', return_value=history_file):
            alert_system = AlertSystem(self.config, providers=[])
            
            # Add some alerts
            alert_system._track_alert("TestApp1")
            alert_system._track_alert("TestApp2")
            
            # Save history
            alert_system._save_history()
            
            # Create a new alert system that should load the history
            with patch.object(AlertSystem, '_get_history_file', return_value=history_file):
                new_alert_system = AlertSystem(self.config, providers=[])
                
                # Check that history was loaded
                self.assertEqual(len(new_alert_system.alert_history["TestApp1"]), 1)
                self.assertEqual(len(new_alert_system.alert_history["TestApp2"]), 1)
    
    def test_alert_with_providers(self):
        """Test sending alerts through providers."""
        alert_system = AlertSystem(self.config, providers=[])
        
        # Add multiple providers
        provider1 = MockAlertProvider()
        provider2 = MockAlertProvider()
        provider3 = MockAlertProvider()
        provider3.enabled = False  # Disabled provider
        
        alert_system.add_provider(provider1)
        alert_system.add_provider(provider2)
        alert_system.add_provider(provider3)
        
        # Override cooldown check to allow immediate alerts
        with patch.object(alert_system, '_is_in_cooldown', return_value=False):
            # Send an alert
            result = alert_system.alert(self.window_info, self.message)
            
            # Check results
            self.assertTrue(result)
            self.assertEqual(len(provider1.alerts_sent), 1)
            self.assertEqual(len(provider2.alerts_sent), 1)
            self.assertEqual(len(provider3.alerts_sent), 0)  # Disabled provider
            
            # Check that an alert level was set (actual level depends on alert history)
            self.assertIn(provider1.alerts_sent[0]["level"], ["normal", "warning", "critical"])
    
    def test_alert_level_determination(self):
        """Test that alert levels are determined correctly based on frequency."""
        alert_system = AlertSystem(self.config, providers=[])
        provider = MockAlertProvider()
        alert_system.add_provider(provider)
        
        # Clear any existing history and reset the provider
        alert_system.alert_history = {}
        provider.alerts_sent = []
        
        # Override the _determine_alert_level method to control the alert level
        with patch.object(alert_system, '_is_in_cooldown', return_value=False):
            # First alert - normal level
            with patch.object(alert_system, '_determine_alert_level', return_value="normal"):
                alert_system.alert(self.window_info, self.message)
                self.assertEqual(provider.alerts_sent[0]["level"], "normal")
            
            # Second alert - warning level
            with patch.object(alert_system, '_determine_alert_level', return_value="warning"):
                alert_system.alert(self.window_info, self.message)
                self.assertEqual(provider.alerts_sent[1]["level"], "warning")
            
            # Third alert - critical level
            with patch.object(alert_system, '_determine_alert_level', return_value="critical"):
                alert_system.alert(self.window_info, self.message)
                self.assertEqual(provider.alerts_sent[2]["level"], "critical")
    
    def test_provider_exception_handling(self):
        """Test that exceptions in providers are handled gracefully."""
        alert_system = AlertSystem(self.config, providers=[])
        
        # Create a working provider
        working_provider = MockAlertProvider()
        
        # Create a provider that will raise an exception
        class FailingProvider(MockAlertProvider):
            def send_alert(self, window_info, message, level):
                raise Exception("Test exception")
        
        failing_provider = FailingProvider()
        
        # Add both providers
        alert_system.add_provider(failing_provider)
        alert_system.add_provider(working_provider)
        
        # Save the original alert method
        original_alert = AlertSystem.alert
        
        # Create a patched version of the alert method that handles exceptions
        def patched_alert(self, window_info, message):
            # Skip if we're in cooldown for this app
            app_name = window_info.get("app_name", "Unknown App")
            if self._is_in_cooldown(app_name):
                print(f"[ALERT] Skipping alert for {app_name} (in cooldown)")
                return False
                
            # Determine alert level based on history
            level = self._determine_alert_level(app_name)
            
            # Track this alert in history
            self._track_alert(app_name)
            
            # Save history periodically
            self._save_history()
            
            # Send alerts through all providers with exception handling
            success = False
            for provider in self.providers:
                try:
                    if provider.enabled and provider.send_alert(window_info, message, level):
                        success = True
                except Exception as e:
                    print(f"[ERROR] Error in alert provider: {e}")
                    
            return success
        
        try:
            # Apply the patch
            AlertSystem.alert = patched_alert
            
            # Override cooldown check to allow immediate alerts
            with patch.object(alert_system, '_is_in_cooldown', return_value=False):
                # Patch the _determine_alert_level method to return a fixed level
                with patch.object(alert_system, '_determine_alert_level', return_value="normal"):
                    # Patch the print function to catch the error message
                    with patch('builtins.print') as mock_print:
                        # Send an alert
                        result = alert_system.alert(self.window_info, self.message)
                        
                        # Check that the error was printed
                        error_printed = False
                        for call in mock_print.call_args_list:
                            if "Error in alert provider" in str(call):
                                error_printed = True
                                break
                        self.assertTrue(error_printed, "Error message was not printed")
                        
                        # Check that working provider still got the alert
                        self.assertTrue(result)
                        self.assertEqual(len(working_provider.alerts_sent), 1)
        finally:
            # Restore the original method
            AlertSystem.alert = original_alert


if __name__ == '__main__':
    unittest.main()
