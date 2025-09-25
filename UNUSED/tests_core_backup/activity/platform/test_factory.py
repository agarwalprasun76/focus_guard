"""
Unit tests for the platform factory.

This module contains unit tests for the platform factory defined in
core_v2.activity.platform.__init__.
"""

import unittest
from unittest.mock import patch, MagicMock

from core_v2.activity.platform import get_platform_implementation


class TestPlatformFactory(unittest.TestCase):
    """Tests for the platform factory."""
    
    @patch("importlib.import_module")
    def test_get_platform_implementation_windows(self, mock_import_module):
        """Test get_platform_implementation when Windows is supported."""
        # Set up mocks
        mock_windows_module = MagicMock()
        mock_windows_monitor = MagicMock()
        mock_windows_module.WindowsActivityMonitor = mock_windows_monitor
        mock_windows_monitor.is_supported.return_value = True
        
        mock_import_module.side_effect = lambda module_name: {
            "core_v2.activity.platform.windows": mock_windows_module,
        }[module_name]
        
        # Call the function
        result = get_platform_implementation()
        
        # Verify the result
        self.assertEqual(result, mock_windows_monitor.return_value)
        mock_windows_monitor.is_supported.assert_called_once()
        mock_windows_monitor.assert_called_once()
        
        # Verify import order
        mock_import_module.assert_called_once_with("core_v2.activity.platform.windows")
    
    @patch("importlib.import_module")
    def test_get_platform_implementation_linux(self, mock_import_module):
        """Test get_platform_implementation when Windows is not supported but Linux is."""
        # Set up mocks
        mock_windows_module = MagicMock()
        mock_windows_monitor = MagicMock()
        mock_windows_module.WindowsActivityMonitor = mock_windows_monitor
        mock_windows_monitor.is_supported.return_value = False
        
        mock_linux_module = MagicMock()
        mock_linux_monitor = MagicMock()
        mock_linux_module.LinuxActivityMonitor = mock_linux_monitor
        mock_linux_monitor.is_supported.return_value = True
        
        mock_import_module.side_effect = lambda module_name: {
            "core_v2.activity.platform.windows": mock_windows_module,
            "core_v2.activity.platform.linux": mock_linux_module,
        }[module_name]
        
        # Call the function
        result = get_platform_implementation()
        
        # Verify the result
        self.assertEqual(result, mock_linux_monitor.return_value)
        mock_windows_monitor.is_supported.assert_called_once()
        mock_linux_monitor.is_supported.assert_called_once()
        mock_linux_monitor.assert_called_once()
        
        # Verify import order
        mock_import_module.assert_any_call("core_v2.activity.platform.windows")
        mock_import_module.assert_any_call("core_v2.activity.platform.linux")
    
    @patch("importlib.import_module")
    def test_get_platform_implementation_macos(self, mock_import_module):
        """Test get_platform_implementation when only macOS is supported."""
        # Set up mocks
        mock_windows_module = MagicMock()
        mock_windows_monitor = MagicMock()
        mock_windows_module.WindowsActivityMonitor = mock_windows_monitor
        mock_windows_monitor.is_supported.return_value = False
        
        mock_linux_module = MagicMock()
        mock_linux_monitor = MagicMock()
        mock_linux_module.LinuxActivityMonitor = mock_linux_monitor
        mock_linux_monitor.is_supported.return_value = False
        
        mock_macos_module = MagicMock()
        mock_macos_monitor = MagicMock()
        mock_macos_module.MacOSActivityMonitor = mock_macos_monitor
        mock_macos_monitor.is_supported.return_value = True
        
        mock_import_module.side_effect = lambda module_name: {
            "core_v2.activity.platform.windows": mock_windows_module,
            "core_v2.activity.platform.linux": mock_linux_module,
            "core_v2.activity.platform.macos": mock_macos_module,
        }[module_name]
        
        # Call the function
        result = get_platform_implementation()
        
        # Verify the result
        self.assertEqual(result, mock_macos_monitor.return_value)
        mock_windows_monitor.is_supported.assert_called_once()
        mock_linux_monitor.is_supported.assert_called_once()
        mock_macos_monitor.is_supported.assert_called_once()
        mock_macos_monitor.assert_called_once()
        
        # Verify import order
        mock_import_module.assert_any_call("core_v2.activity.platform.windows")
        mock_import_module.assert_any_call("core_v2.activity.platform.linux")
        mock_import_module.assert_any_call("core_v2.activity.platform.macos")
    
    @patch("importlib.import_module")
    def test_get_platform_implementation_none_supported(self, mock_import_module):
        """Test get_platform_implementation when no platform is supported."""
        # Set up mocks
        mock_windows_module = MagicMock()
        mock_windows_monitor = MagicMock()
        mock_windows_module.WindowsActivityMonitor = mock_windows_monitor
        mock_windows_monitor.is_supported.return_value = False
        
        mock_linux_module = MagicMock()
        mock_linux_monitor = MagicMock()
        mock_linux_module.LinuxActivityMonitor = mock_linux_monitor
        mock_linux_monitor.is_supported.return_value = False
        
        mock_macos_module = MagicMock()
        mock_macos_monitor = MagicMock()
        mock_macos_module.MacOSActivityMonitor = mock_macos_monitor
        mock_macos_monitor.is_supported.return_value = False
        
        mock_import_module.side_effect = lambda module_name: {
            "core_v2.activity.platform.windows": mock_windows_module,
            "core_v2.activity.platform.linux": mock_linux_module,
            "core_v2.activity.platform.macos": mock_macos_module,
        }[module_name]
        
        # Call the function and verify exception
        with self.assertRaises(RuntimeError):
            get_platform_implementation()
        
        # Verify all platforms were checked
        mock_windows_monitor.is_supported.assert_called_once()
        mock_linux_monitor.is_supported.assert_called_once()
        mock_macos_monitor.is_supported.assert_called_once()
    
    @patch("importlib.import_module")
    def test_get_platform_implementation_import_error(self, mock_import_module):
        """Test get_platform_implementation when an import error occurs."""
        # Set up mocks to raise ImportError for Linux
        mock_windows_module = MagicMock()
        mock_windows_monitor = MagicMock()
        mock_windows_module.WindowsActivityMonitor = mock_windows_monitor
        mock_windows_monitor.is_supported.return_value = False
        
        mock_import_module.side_effect = lambda module_name: {
            "core_v2.activity.platform.windows": mock_windows_module,
            "core_v2.activity.platform.linux": ImportError("Module not found"),
        }[module_name] if module_name == "core_v2.activity.platform.windows" else ImportError("Module not found")
        
        # Call the function and verify exception
        with self.assertRaises(RuntimeError):
            get_platform_implementation()
        
        # Verify Windows was checked
        mock_windows_monitor.is_supported.assert_called_once()


if __name__ == "__main__":
    unittest.main()
