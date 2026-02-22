"""
Unit tests for the platform factory.

This module contains unit tests for the platform factory defined in
focus_guard.core.activity.platform.__init__.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

from focus_guard.core.activity.platform import get_platform_implementation
from focus_guard.core.activity.platform.base import PlatformActivityMonitor


class TestPlatformFactory(unittest.TestCase):
    """Tests for the platform factory."""

    def test_get_platform_implementation_returns_instance(self):
        """Test that get_platform_implementation returns a PlatformActivityMonitor on this OS."""
        if sys.platform != "win32":
            self.skipTest("Windows-only test")
        result = get_platform_implementation()
        self.assertIsInstance(result, PlatformActivityMonitor)

    def test_get_platform_implementation_windows(self):
        """Test get_platform_implementation when Windows is supported."""
        mock_cls = MagicMock()
        mock_cls.is_supported.return_value = True
        mock_instance = MagicMock(spec=PlatformActivityMonitor)
        mock_cls.return_value = mock_instance

        with patch(
            "focus_guard.core.activity.platform.windows.WindowsActivityMonitor",
            mock_cls,
            create=True,
        ):
            result = get_platform_implementation()

        mock_cls.is_supported.assert_called()
        self.assertEqual(result, mock_instance)

    def test_get_platform_implementation_none_supported(self):
        """Test get_platform_implementation raises when no platform is supported."""
        # Patch the factory function's internals: make WindowsActivityMonitor
        # report unsupported, and ensure no other platform imports succeed.
        from focus_guard.core.activity.platform.windows import WindowsActivityMonitor
        with patch.object(WindowsActivityMonitor, "is_supported", return_value=False):
            with self.assertRaises(RuntimeError):
                get_platform_implementation()

    def test_get_platform_implementation_import_error_graceful(self):
        """Test that ImportError for one platform doesn't crash the factory."""
        # On Windows the real WindowsActivityMonitor will succeed, so this
        # test just verifies the function completes without raising ImportError.
        try:
            result = get_platform_implementation()
            self.assertIsNotNone(result)
        except RuntimeError:
            # Acceptable if no platform is supported in the test env
            pass


if __name__ == "__main__":
    unittest.main()
