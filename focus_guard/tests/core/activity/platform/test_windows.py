"""
Unit tests for the Windows-specific activity monitoring implementation.

This module contains unit tests for the WindowsActivityMonitor class defined in
focus_guard.core.activity.platform.windows.
"""

import unittest
from unittest.mock import patch, MagicMock, call

import sys
from datetime import datetime

from focus_guard.core.activity.platform.windows import WindowsActivityMonitor


class TestWindowsActivityMonitor(unittest.TestCase):
    """Tests for the WindowsActivityMonitor class."""
    
    @patch("focus_guard.core.activity.platform.windows.sys")
    def test_is_supported_windows_platform(self, mock_sys):
        """Test is_supported when on Windows platform with required modules."""
        mock_sys.platform = "win32"
        
        with patch.dict("sys.modules", {
            "win32gui": MagicMock(),
            "win32process": MagicMock(),
            "psutil": MagicMock()
        }):
            result = WindowsActivityMonitor.is_supported()
            self.assertTrue(result)
    
    @patch("focus_guard.core.activity.platform.windows.sys")
    def test_is_supported_non_windows_platform(self, mock_sys):
        """Test is_supported when not on Windows platform."""
        mock_sys.platform = "linux"
        
        result = WindowsActivityMonitor.is_supported()
        self.assertFalse(result)
    
    @patch("focus_guard.core.activity.platform.windows.sys")
    def test_is_supported_missing_modules(self, mock_sys):
        """Test is_supported when required modules are missing."""
        mock_sys.platform = "win32"
        
        with patch.dict("sys.modules", {
            "win32gui": None,
            "win32process": MagicMock(),
            "psutil": MagicMock()
        }):
            result = WindowsActivityMonitor.is_supported()
            self.assertFalse(result)
    
    @patch("win32gui.GetForegroundWindow")
    @patch("win32gui.GetWindowText")
    @patch("win32gui.GetClassName")
    @patch("win32process.GetWindowThreadProcessId")
    @patch("psutil.Process")
    @patch("win32gui.GetWindowRect")
    def test_get_active_window(self, mock_get_rect, mock_process, 
                              mock_get_thread_pid, mock_get_class_name, 
                              mock_get_window_text, mock_get_foreground):
        """Test get_active_window with valid window."""
        # Set up mocks
        mock_get_foreground.return_value = 12345
        mock_get_window_text.return_value = "Test Window"
        mock_get_class_name.return_value = "TestClass"
        mock_get_thread_pid.return_value = (1, 67890)
        
        mock_process_instance = MagicMock()
        mock_process_instance.name.return_value = "test_app.exe"
        mock_process.return_value = mock_process_instance
        
        mock_get_rect.return_value = (0, 0, 100, 100)
        
        # Create monitor and call the method
        monitor = WindowsActivityMonitor()
        result = monitor.get_active_window()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result["app_name"], "test_app.exe")
        self.assertEqual(result["window_title"], "Test Window")
        self.assertEqual(result["pid"], "67890")
        self.assertIn("timestamp", result)  # timestamp is dynamic
        self.assertEqual(result["hwnd"], 12345)
        self.assertEqual(result["rect"], (0, 0, 100, 100))
        self.assertEqual(result["area"], 10000)
        
        # Verify mock calls
        mock_get_foreground.assert_called_once()
        mock_get_window_text.assert_called_once_with(12345)
        mock_get_class_name.assert_called_once_with(12345)
        mock_get_thread_pid.assert_called_once_with(12345)
        mock_process.assert_called_once_with(67890)
        mock_get_rect.assert_called_once_with(12345)
    
    @patch("win32gui.GetForegroundWindow")
    @patch("win32gui.GetWindowText")
    @patch("win32gui.GetClassName")
    def test_get_active_window_desktop(self, mock_get_class_name, 
                                      mock_get_window_text, mock_get_foreground):
        """Test get_active_window with desktop window."""
        # Set up mocks
        mock_get_foreground.return_value = 12345
        mock_get_window_text.return_value = ""
        mock_get_class_name.return_value = "Progman"
        
        # Create monitor and call the method
        monitor = WindowsActivityMonitor()
        result = monitor.get_active_window()
        
        # Verify the result
        self.assertIsNone(result)
        
        # Verify mock calls
        mock_get_foreground.assert_called_once()
        mock_get_window_text.assert_called_once_with(12345)
        mock_get_class_name.assert_called_once_with(12345)
    
    @patch("win32gui.GetForegroundWindow")
    @patch("win32gui.GetWindowText")
    @patch("win32gui.GetClassName")
    @patch("win32process.GetWindowThreadProcessId")
    @patch("psutil.Process")
    @patch("win32gui.GetWindowRect")
    def test_get_active_window_process_error(self, mock_get_rect, mock_process, mock_get_thread_pid,
                                           mock_get_class_name, mock_get_window_text,
                                           mock_get_foreground):
        """Test get_active_window with process error."""
        # Set up mocks
        mock_get_foreground.return_value = 12345
        mock_get_window_text.return_value = "Test Window"
        mock_get_class_name.return_value = "TestClass"
        mock_get_thread_pid.return_value = (1, 67890)
        mock_get_rect.return_value = (0, 0, 100, 100)
        
        import psutil
        mock_process.side_effect = psutil.NoSuchProcess(67890)
        
        # Create monitor and call the method
        monitor = WindowsActivityMonitor()
        result = monitor.get_active_window()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result["app_name"], "unknown")
        
        # Verify mock calls
        mock_get_foreground.assert_called_once()
        mock_get_window_text.assert_called_once_with(12345)
        mock_get_class_name.assert_called_once_with(12345)
        mock_get_thread_pid.assert_called_once_with(12345)
        mock_process.assert_called_once_with(67890)
    
    def test_get_top_windows(self):
        """Test get_top_windows."""
        monitor = WindowsActivityMonitor()
        monitor._get_window_info = MagicMock()
        monitor._get_screen_area = MagicMock()
        
        window_info_1 = {
            "app_name": "test_app_1",
            "window_title": "Test Window 1",
            "pid": "12345",
            "area": 10000
        }
        window_info_2 = {
            "app_name": "test_app_2",
            "window_title": "Test Window 2",
            "pid": "67890",
            "area": 20000
        }
        
        monitor._get_window_info.side_effect = [window_info_1, window_info_2]
        monitor._get_screen_area.return_value = 100000
        
        def fake_enum_windows(callback, extra):
            callback(12345, extra)
            callback(67890, extra)
        
        with patch("win32gui.EnumWindows", side_effect=fake_enum_windows), \
             patch("win32gui.IsWindowVisible", return_value=True), \
             patch("win32gui.GetWindowRect", return_value=(0, 0, 200, 200)), \
             patch("win32gui.GetClassName", return_value="TestClass"), \
             patch("win32gui.GetWindowText", return_value="Test"):
            result = monitor.get_top_windows(top_region=300)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["app_name"], "test_app_1")
        self.assertEqual(result[0]["percent"], 0.1)
        self.assertEqual(result[1]["app_name"], "test_app_2")
        self.assertEqual(result[1]["percent"], 0.2)
        monitor._get_window_info.assert_has_calls([call(12345), call(67890)])
        monitor._get_screen_area.assert_called()
    
    @patch("win32gui.IsWindowVisible")
    @patch("win32gui.GetWindowRect")
    @patch("win32gui.GetClassName")
    @patch("win32gui.GetWindowText")
    def test_get_top_windows_filtering(self, mock_get_window_text, mock_get_class_name,
                                     mock_get_rect, mock_is_visible):
        """Test get_top_windows with window filtering."""
        # Set up mocks to capture the callback function
        def fake_enum_windows(callback, extra):
            # Window 1: Not visible
            mock_is_visible.return_value = False
            callback(1, extra)
            
            # Window 2: Too small
            mock_is_visible.return_value = True
            mock_get_rect.return_value = (0, 0, 50, 30)
            callback(2, extra)
            
            # Window 3: Below top region
            mock_is_visible.return_value = True
            mock_get_rect.return_value = (0, 400, 100, 500)
            callback(3, extra)
            
            # Window 4: Desktop window
            mock_is_visible.return_value = True
            mock_get_rect.return_value = (0, 0, 100, 100)
            mock_get_class_name.return_value = "Progman"
            mock_get_window_text.return_value = ""
            callback(4, extra)
            
            # Window 5: Valid window
            mock_is_visible.return_value = True
            mock_get_rect.return_value = (0, 0, 100, 100)
            mock_get_class_name.return_value = "TestClass"
            mock_get_window_text.return_value = "Test Window"
            callback(5, extra)
        
        # Create monitor and set up mocks
        monitor = WindowsActivityMonitor()
        with patch("win32gui.EnumWindows", side_effect=fake_enum_windows):
            # Mock _get_window_info for the valid window
            monitor._get_window_info = MagicMock()
            window_info = {
                "app_name": "test_app",
                "window_title": "Test Window",
                "pid": "12345",
                "area": 10000
            }
            monitor._get_window_info.return_value = window_info
            
            # Mock _get_screen_area
            monitor._get_screen_area = MagicMock(return_value=100000)
            
            # Call the method
            result = monitor.get_top_windows(top_region=300)
            
            # Verify the result
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["app_name"], "test_app")
            
            # Verify _get_window_info was only called for the valid window
            monitor._get_window_info.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
