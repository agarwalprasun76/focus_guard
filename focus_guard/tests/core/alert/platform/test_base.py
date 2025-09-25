"""
Unit tests for alert system platform base interface.

This module contains tests for the platform interface.
"""

import unittest
from focus_guard.core.alert.platform.base import PlatformAlertInterface


class TestPlatformInterface(unittest.TestCase):
    """Tests for the platform interface."""
    
    def test_abstract_methods(self):
        """Test that abstract methods are defined."""
        methods = [
            'show_notification',
            'play_sound',
            'show_blocking_alert',
            'is_supported'
        ]
        
        for method in methods:
            self.assertTrue(hasattr(PlatformAlertInterface, method))


if __name__ == "__main__":
    unittest.main()
