"""
Unit tests for Windows alert platform.

This module contains tests for the Windows platform implementation.
"""

import unittest
import sys
from unittest.mock import patch, MagicMock

from focus_guard.core.alert.platform.windows import WindowsAlertPlatform


@unittest.skipIf(sys.platform != 'win32', "Windows-only tests")
class TestWindowsPlatform(unittest.TestCase):
    """Tests for the Windows platform implementation."""
    
    def setUp(self):
        """Set up test environment."""
        # Skip actual instantiation if not on Windows
        if sys.platform == 'win32':
            # Mock is_supported to avoid actual system checks
            with patch.object(WindowsAlertPlatform, 'is_supported', return_value=True):
                self.platform = WindowsAlertPlatform()
    
    @patch('subprocess.run')
    def test_is_supported(self, mock_run):
        """Test Windows platform support detection."""
        # Skip test if not on Windows
        if not hasattr(self, 'platform'):
            self.skipTest("Not running on Windows")
            
        # Mock subprocess.run to simulate PowerShell availability
        mock_run.return_value = MagicMock(returncode=0)
        
        # Save original platform
        original_platform = sys.platform
        
        try:
            # Test Windows platform
            sys.platform = 'win32'
            self.assertTrue(WindowsAlertPlatform.is_supported())
            
            # Test non-Windows platform
            sys.platform = 'linux'
            self.assertFalse(WindowsAlertPlatform.is_supported())
            
            # Test PowerShell not available
            mock_run.side_effect = FileNotFoundError("PowerShell not found")
            sys.platform = 'win32'
            self.assertFalse(WindowsAlertPlatform.is_supported())
        finally:
            # Restore original platform
            sys.platform = original_platform
    
    @patch('threading.Thread')
    def test_show_notification(self, mock_thread):
        """Test showing a notification."""
        if not hasattr(self, 'platform'):
            self.skipTest("Not running on Windows")
        
        # Mock thread to avoid actual execution
        mock_thread.return_value = MagicMock()
        
        result = self.platform.show_notification(
            title="Test Title",
            message="Test Message",
            level="normal",
            options={"app_name": "TestApp"}
        )
        
        self.assertTrue(result)
        mock_thread.assert_called_once()
    
    @patch('threading.Thread')
    def test_play_sound(self, mock_thread):
        """Test playing a sound."""
        if not hasattr(self, 'platform'):
            self.skipTest("Not running on Windows")
        
        # Mock thread to avoid actual execution
        mock_thread.return_value = MagicMock()
        
        result = self.platform.play_sound(
            sound_type="normal",
            options={"repeat_count": 2}
        )
        
        self.assertTrue(result)
        mock_thread.assert_called_once()
    
    @patch('subprocess.run')
    def test_show_blocking_alert(self, mock_run):
        """Test showing a blocking alert."""
        if not hasattr(self, 'platform'):
            self.skipTest("Not running on Windows")
        
        # Mock subprocess.run to simulate MessageBox
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.platform.show_blocking_alert(
            title="Test Title",
            message="Test Message",
            level="warning",
            options={"app_name": "TestApp"}
        )
        
        self.assertTrue(result)
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_show_blocking_alert_timeout(self, mock_run):
        """Test showing a blocking alert with timeout."""
        if not hasattr(self, 'platform'):
            self.skipTest("Not running on Windows")
        
        # Mock subprocess.run to simulate timeout
        mock_run.side_effect = TimeoutError("Timed out")
        
        result = self.platform.show_blocking_alert(
            title="Test Title",
            message="Test Message",
            level="warning",
            options={"timeout": 1}
        )
        
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
