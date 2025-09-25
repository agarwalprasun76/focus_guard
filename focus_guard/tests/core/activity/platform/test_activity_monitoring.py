"""
Cross-platform tests for activity monitoring functionality.

These tests verify that the activity monitoring features work correctly
across different operating systems.
"""

import sys
import platform
import unittest
from unittest.mock import patch, MagicMock

# Skip if not running on the target OS
skip_if_not_windows = unittest.skipIf(
    not sys.platform.startswith('win'),
    "Test requires Windows"
)

skip_if_not_macos = unittest.skipIf(
    not sys.platform == 'darwin',
    "Test requires macOS"
)

skip_if_not_linux = unittest.skipIf(
    not sys.platform.startswith('linux'),
    "Test requires Linux"
)

class TestCrossPlatformActivityMonitoring(unittest.TestCase):
    """Test activity monitoring across different platforms."""
    
    def test_platform_implementation_detection(self):
        """Verify that the correct platform implementation is detected."""
        from focus_guard.core.activity.platform import get_platform_implementation
        
        try:
            monitor = get_platform_implementation()
            print(f"\nDetected platform: {platform.system()}")
            print(f"Using monitor: {monitor.__class__.__name__}")
            
            # Verify we got a valid monitor instance with required methods
            self.assertIsNotNone(monitor)
            self.assertTrue(hasattr(monitor, 'get_active_window'), 
                          "Platform monitor must implement get_active_window()")
            self.assertTrue(hasattr(monitor, 'get_top_windows'), 
                          "Platform monitor must implement get_top_windows()")
            
        except ImportError as e:
            if sys.platform in ['win32', 'darwin', 'linux']:
                self.fail(f"Platform implementation not found for {sys.platform}")
            else:
                self.skipTest(f"No implementation for platform: {sys.platform}")
    
    @skip_if_not_windows
    def test_windows_activity_monitoring(self):
        """Test Windows-specific activity monitoring."""
        from focus_guard.core.activity.platform.windows import WindowsActivityMonitor
        from focus_guard.core.activity.models import WindowInfo
        
        # Mock the Windows API calls
        with patch('win32gui.GetForegroundWindow') as mock_foreground, \
             patch('win32gui.GetWindowText') as mock_get_text, \
             patch('win32gui.GetClassName') as mock_get_class, \
             patch('win32gui.GetWindowRect') as mock_get_rect, \
             patch('win32process.GetWindowThreadProcessId') as mock_get_process_id:
            
            # Setup mock return values
            mock_foreground.return_value = 12345
            mock_get_text.return_value = 'Test Window'
            mock_get_class.return_value = 'Chrome_WidgetWin_1'  # A real window class
            mock_get_rect.return_value = (0, 0, 1024, 768)  # Mock window rectangle
            mock_get_process_id.return_value = (54321, 67890)
            
            # Mock process name lookup
            with patch('psutil.Process') as mock_process:
                mock_process.return_value.name.return_value = 'test_app.exe'
                
                monitor = WindowsActivityMonitor()
                window_info = monitor.get_active_window()
                
                # Verify the window info structure matches expected format
                self.assertIsNotNone(window_info)
                self.assertIn('window_title', window_info)
                self.assertIn('app_name', window_info)
                self.assertIn('pid', window_info)
                self.assertIn('timestamp', window_info)
                
                # Verify the mocked values
                self.assertEqual(window_info['window_title'], 'Test Window')
                self.assertEqual(window_info['app_name'], 'test_app.exe')
                self.assertEqual(str(window_info['pid']), '67890')
    
    @skip_if_not_macos
    def test_macos_activity_monitoring(self):
        """Test macOS-specific activity monitoring."""
        from focus_guard.core.activity.platform.macos import MacOSActivityMonitor
        
        # Mock the AppKit and other macOS-specific imports
        with patch('AppKit.NSWorkspace.sharedWorkspace') as mock_workspace, \
             patch('AppKit.NSRunningApplication') as mock_running_app:
            
            # Setup mock application
            mock_app = MagicMock()
            mock_app.localizedName.return_value = 'Test App'
            mock_app.bundleIdentifier.return_value = 'com.example.testapp'
            mock_app.processIdentifier.return_value = 12345
            
            mock_workspace.frontmostApplication.return_value = mock_app
            mock_workspace.activeApplication.return_value = {
                'NSApplicationName': 'Test App',
                'NSApplicationBundleIdentifier': 'com.example.testapp',
                'NSApplicationProcessIdentifier': 12345
            }
            
            monitor = MacOSActivityMonitor()
            window_info = monitor.get_active_window()
            
            # Verify the window info structure matches expected format
            self.assertIsNotNone(window_info)
            self.assertIn('app_name', window_info)
            self.assertIn('pid', window_info)
            self.assertIn('timestamp', window_info)
            
            # Verify the mocked values
            self.assertEqual(window_info['app_name'], 'Test App')
            self.assertEqual(window_info['pid'], 12345)
    
    @skip_if_not_linux
    def test_linux_activity_monitoring(self):
        """Test Linux-specific activity monitoring."""
        from focus_guard.core.activity.platform.linux import LinuxActivityMonitor
        
        # Mock subprocess and Xlib calls
        with patch('subprocess.check_output') as mock_check_output, \
             patch('Xlib.display.Display') as mock_display:
            
            # Mock xprop output
            mock_check_output.return_value = b'''WM_CLASS(STRING) = "test_app", "Test App"
_NET_WM_PID(CARDINAL) = 12345
WM_NAME(STRING) = "Test Window"
'''
            
            # Mock X11 display
            mock_screen = MagicMock()
            mock_screen.root.query_pointer.return_value = (0, 0, 0, 0, 1, 1, 0)
            
            mock_display.return_value.screen.return_value = mock_screen
            mock_display.return_value.get_input_focus.return_value = (MagicMock(), 0)
            
            monitor = LinuxActivityMonitor()
            window_info = monitor.get_active_window()
            
            # Verify the window info structure matches expected format
            self.assertIsNotNone(window_info)
            self.assertIn('window_title', window_info)
            self.assertIn('app_name', window_info)
            self.assertIn('pid', window_info)
            self.assertIn('timestamp', window_info)
            
            # Verify the mocked values
            self.assertEqual(window_info['window_title'], 'Test Window')
            self.assertEqual(window_info['app_name'], 'Test App')
            self.assertEqual(window_info['pid'], 12345)
    
    def test_cross_platform_monitor_initialization(self):
        """Test that the monitor initializes correctly on all platforms."""
        from focus_guard.core.activity.enhanced_monitor import EnhancedActivityMonitor
        from focus_guard.core.activity.idle_detector import IdleConfiguration
        
        # Mock the platform implementation to avoid actual system calls
        with patch('focus_guard.core.activity.platform.get_platform_implementation') as mock_impl:
            # Create a mock platform implementation
            mock_monitor = MagicMock()
            mock_monitor.get_active_window.return_value = None
            mock_impl.return_value = mock_monitor
            
            # This should work on all platforms
            monitor = EnhancedActivityMonitor(
                idle_config=IdleConfiguration(
                    short_idle_threshold=30,
                    medium_idle_threshold=300,
                    long_idle_threshold=1800
                ),
                session_timeout=300,
                polling_interval=1.0
            )
            
            # Basic functionality should work
            monitor.start_monitoring()
            try:
                idle_time = monitor.get_idle_time_seconds()
                self.assertGreaterEqual(idle_time, 0)
                
                # With our mock, we expect None for the session
                session = monitor.get_current_usage_session()
                self.assertIsNone(session)  # No activity to track with mock
                
            finally:
                monitor.stop_monitoring()

if __name__ == '__main__':
    unittest.main()
