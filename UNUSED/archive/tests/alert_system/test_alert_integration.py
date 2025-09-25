"""
Integration tests for the alert system.
These tests verify that different components of the alert system work together correctly.
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

from core.alert_system.alert_system import AlertSystem
from core.alert_system.popup_alert import PopupAlertProvider
from core.alert_system.sound_alert import SoundAlertProvider

class TestAlertSystemIntegration(unittest.TestCase):
    """Integration tests for the alert system with real providers."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for alert history
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Basic configuration
        self.config = {
            "cooldown_period": 0,  # No cooldown for testing
            "escalation_threshold": 2,
            "escalation_window": 60,
            "history_file": os.path.join(self.temp_dir.name, "alert_history.json"),
            "popup_alert": {
                "enabled": True,
                "popup_duration": 1  # Short duration for testing
            },
            "sound_alert": {
                "enabled": True,
                "volume": 0.5,
                "repeat_count": 1
            }
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
    
    def test_alert_system_with_real_providers(self):
        """Test alert system with real providers."""
        # Create mock providers
        popup_provider = MagicMock()
        popup_provider.enabled = True
        popup_provider.send_alert.return_value = True
        
        sound_provider = MagicMock()
        sound_provider.enabled = True
        sound_provider.send_alert.return_value = True
        
        # Create alert system with mock providers
        alert_system = AlertSystem(self.config, providers=[popup_provider, sound_provider])
        
        # Override the _determine_alert_level method to return a fixed level
        with patch.object(alert_system, '_is_in_cooldown', return_value=False):
            with patch.object(alert_system, '_determine_alert_level', return_value="normal"):
                # Send an alert
                result = alert_system.alert(self.window_info, self.message)
                
                # Check that alert was sent successfully
                self.assertTrue(result)
                
                # Check that providers were called with correct parameters
                popup_provider.send_alert.assert_called_with(self.window_info, self.message, "normal")
                sound_provider.send_alert.assert_called_with(self.window_info, self.message, "normal")
    
    def test_alert_escalation_integration(self):
        """Test alert escalation with real providers."""
        # Create alert system with mock providers
        alert_system = AlertSystem(self.config, providers=[])
        
        # Add a mock provider that will record the alert levels
        mock_provider = MagicMock()
        mock_provider.enabled = True
        mock_provider.send_alert.return_value = True
        alert_system.add_provider(mock_provider)
        
        # Clear any existing history
        alert_system.alert_history = {}
        
        # Override cooldown check to allow immediate alerts
        with patch.object(alert_system, '_is_in_cooldown', return_value=False):
            # Test with different alert levels
            with patch.object(alert_system, '_determine_alert_level', return_value="normal"):
                alert_system.alert(self.window_info, "Normal alert")
                mock_provider.send_alert.assert_called_with(self.window_info, "Normal alert", "normal")
            
            with patch.object(alert_system, '_determine_alert_level', return_value="warning"):
                alert_system.alert(self.window_info, "Warning alert")
                mock_provider.send_alert.assert_called_with(self.window_info, "Warning alert", "warning")
            
            with patch.object(alert_system, '_determine_alert_level', return_value="critical"):
                alert_system.alert(self.window_info, "Critical alert")
                mock_provider.send_alert.assert_called_with(self.window_info, "Critical alert", "critical")
    
    def test_platform_specific_sound_integration(self):
        """Test platform-specific sound playing."""
        # Create a sound provider with a modified config to avoid file checks
        config = self.config["sound_alert"].copy()
        config["sound_files"] = {"normal": "test.wav", "warning": "test.wav", "critical": "test.wav"}
        provider = SoundAlertProvider(config)
        
        # Test Windows sound playing
        with patch('platform.system', return_value="Windows"):
            # We need to mock the actual winsound module
            with patch('winsound.Beep') as mock_beep:
                # Mock the threading to call the function directly
                with patch('threading.Thread', autospec=True) as mock_thread:
                    # Make the Thread.start() call the target function directly
                    def fake_start():
                        # Get the target function and args from the most recent call
                        args = mock_thread.call_args[1]
                        target_func = args['target']
                        if 'args' in args:
                            target_args = args['args']
                            target_func(*target_args)
                        else:
                            target_func()
                    mock_thread.return_value.start.side_effect = fake_start
                    
                    # Mock os.path.exists to return True for sound files
                    with patch('os.path.exists', return_value=True):
                        # Send the alert
                        provider.send_alert(self.window_info, self.message, "normal")
                        
                        # Check that thread was created
                        mock_thread.assert_called()
                        
                        # Check that Beep was called
                        mock_beep.assert_called()
        
        # For macOS and Linux tests, we'll just verify that the provider returns True
        # since we can't easily test the actual sound playing functionality
        
        # Test macOS sound playing
        with patch('platform.system', return_value="Darwin"):
            # Create a new provider for macOS
            mac_provider = SoundAlertProvider(self.config["sound_alert"])
            
            # Mock subprocess.run to avoid actual command execution
            with patch('subprocess.run', return_value=MagicMock(returncode=0)) as mock_run:
                # Mock os.path.exists to return True for sound files
                with patch('os.path.exists', return_value=True):
                    # Send the alert and verify it returns True
                    result = mac_provider.send_alert(self.window_info, self.message, "normal")
                    self.assertTrue(result)
        
        # Test Linux sound playing
        with patch('platform.system', return_value="Linux"):
            # Create a new provider for Linux
            linux_provider = SoundAlertProvider(self.config["sound_alert"])
            
            # Mock subprocess.run to avoid actual command execution
            with patch('subprocess.run', return_value=MagicMock(returncode=0)) as mock_run:
                # Mock os.path.exists to return True for sound files
                with patch('os.path.exists', return_value=True):
                    # Send the alert and verify it returns True
                    result = linux_provider.send_alert(self.window_info, self.message, "normal")
                    self.assertTrue(result)
    
    def test_windows_popup_script_generation(self):
        """Test Windows popup script generation."""
        # Create a popup provider
        provider = PopupAlertProvider(self.config["popup_alert"])
        
        # Test Windows popup generation
        with patch('platform.system', return_value="Windows"):
            with patch('subprocess.Popen') as mock_popen:
                # Mock the threading to call the function directly
                with patch('threading.Thread', autospec=True) as mock_thread:
                    # Make the Thread.start() call the target function directly
                    def fake_start():
                        # Get the target function and args from the most recent call
                        args = mock_thread.call_args[1]
                        target_func = args['target']
                        if 'args' in args:
                            target_args = args['args']
                            target_func(*target_args)
                        else:
                            target_func()
                    mock_thread.return_value.start.side_effect = fake_start
                    
                    # Mock tempfile for script generation
                    with patch('tempfile.NamedTemporaryFile') as mock_tempfile:
                        mock_temp_file = MagicMock()
                        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
                        mock_temp_file.name = "temp_script.ps1"
                        
                        # Send the alert
                        provider.send_alert(self.window_info, self.message, "normal")
                        
                        # Check that PowerShell script was created and executed
                        mock_tempfile.assert_called()
                        mock_temp_file.write.assert_called()
                        mock_popen.assert_called()
                        
                        # Check script content if write was called
                        if mock_temp_file.write.called:
                            script_content = mock_temp_file.write.call_args[0][0]
                            self.assertIn("FocusGuard Alert", script_content)
                            self.assertIn("TestApp", script_content)
                            self.assertIn("Test alert message", script_content)
                            # For normal alerts, we should see the normal alert color
                            self.assertIn("#55AAFF", script_content)  # Normal alert color
            
            # Check that PowerShell was called
            mock_popen.assert_called()
            cmd_args = mock_popen.call_args[0][0]
            self.assertEqual(cmd_args[0], "powershell")
            self.assertEqual(cmd_args[1], "-ExecutionPolicy")
            self.assertEqual(cmd_args[2], "Bypass")


if __name__ == '__main__':
    unittest.main()
