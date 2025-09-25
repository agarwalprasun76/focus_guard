"""
Unit tests for the IdleDetector class.

This module contains unit tests for the IdleDetector class defined in
core.activity.idle_detector.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import time
from datetime import datetime, timedelta

from focus_guard.core.activity.idle_detector import (
    IdleDetector, IdleState, IdleConfiguration, IdleEvent, PlatformIdleDetector
)


class MockPlatformDetector(PlatformIdleDetector):
    """Mock platform detector for testing."""
    
    def __init__(self):
        self._idle_time = 0.0
        
    def get_idle_time_seconds(self) -> float:
        return self._idle_time
    
    def is_supported(self) -> bool:
        return True
    
    def set_idle_time(self, seconds: float):
        """Set the idle time for testing."""
        self._idle_time = seconds


class TestIdleDetector(unittest.TestCase):
    """Tests for the IdleDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = IdleConfiguration(
            short_idle_threshold=60.0,    # 1 minute
            medium_idle_threshold=300.0,  # 5 minutes
            long_idle_threshold=900.0,    # 15 minutes
            polling_interval=1.0
        )
        
        # Create a mock platform detector
        self.platform_detector = MockPlatformDetector()
        
        # Patch the _get_platform_detector method to return our mock
        self.patcher = patch(
            'focus_guard.core.activity.idle_detector.IdleDetector._get_platform_detector',
            return_value=self.platform_detector
        )
        self.mock_get_platform = self.patcher.start()
        
        # Create the detector
        self.detector = IdleDetector(self.config)
        
        # Mock callbacks
        self.callback1 = MagicMock()
        self.callback2 = MagicMock()
        
        # Add callbacks
        self.detector.add_state_change_callback(self.callback1)
        self.detector.add_state_change_callback(self.callback2)
    
    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()
        if hasattr(self, 'detector') and hasattr(self.detector, 'stop_monitoring'):
            self.detector.stop_monitoring()
    
    def test_initial_state(self):
        """Test the initial state of the detector."""
        self.assertEqual(self.detector.get_current_state(), IdleState.ACTIVE)
        self.assertIsNone(self.detector.idle_start_time)
        self.assertGreaterEqual(self.detector.last_activity_time, datetime.now() - timedelta(seconds=1))
    
    def test_is_idle(self):
        """Test the is_idle method."""
        # Not idle initially
        self.assertFalse(self.detector.is_idle())
        
        # Set idle time to 30 seconds (below short idle threshold)
        self.platform_detector.set_idle_time(30.0)
        self.assertFalse(self.detector.is_idle())
        
        # Set idle time to 90 seconds (above short idle threshold)
        self.platform_detector.set_idle_time(90.0)
        self.assertTrue(self.detector.is_idle())
        
        # Test with custom threshold
        self.assertTrue(self.detector.is_idle(threshold_seconds=30.0))
        self.assertFalse(self.detector.is_idle(threshold_seconds=120.0))
    
    def test_state_transitions(self):
        """Test state transitions based on idle time."""
        # Initial state should be ACTIVE
        self.assertEqual(self.detector.get_current_state(), IdleState.ACTIVE)
        
        # Simulate idle time just below short idle threshold
        self.platform_detector.set_idle_time(59.0)
        self.detector._update_idle_state()
        self.assertEqual(self.detector.get_current_state(), IdleState.ACTIVE)
        
        # Simulate short idle
        self.platform_detector.set_idle_time(61.0)
        self.detector._update_idle_state()
        self.assertEqual(self.detector.get_current_state(), IdleState.SHORT_IDLE)
        
        # Simulate medium idle
        self.platform_detector.set_idle_time(301.0)
        self.detector._update_idle_state()
        self.assertEqual(self.detector.get_current_state(), IdleState.MEDIUM_IDLE)
        
        # Simulate long idle
        self.platform_detector.set_idle_time(901.0)
        self.detector._update_idle_state()
        self.assertEqual(self.detector.get_current_state(), IdleState.LONG_IDLE)
        
        # Simulate returning to active
        self.platform_detector.set_idle_time(0.0)
        self.detector._update_idle_state()
        self.assertEqual(self.detector.get_current_state(), IdleState.ACTIVE)
    
    def test_state_change_callbacks(self):
        """Test that state change callbacks are called correctly."""
        # Reset call counts
        self.callback1.reset_mock()
        self.callback2.reset_mock()
        
        # Initial state is ACTIVE, so no callbacks should be called yet
        self.callback1.assert_not_called()
        self.callback2.assert_not_called()
        
        # Simulate short idle
        self.platform_detector.set_idle_time(61.0)
        self.detector._update_idle_state()
        
        # Both callbacks should be called with the state change
        self.assertEqual(self.callback1.call_count, 1)
        self.assertEqual(self.callback2.call_count, 1)
        
        # Get the event passed to the callback
        event = self.callback1.call_args[0][0]
        self.assertIsInstance(event, IdleEvent)
        self.assertEqual(event.previous_state, IdleState.ACTIVE)
        self.assertEqual(event.current_state, IdleState.SHORT_IDLE)
        self.assertGreaterEqual(event.idle_duration, 61.0)
        self.assertGreaterEqual(event.active_duration, 0.0)
    
    def test_monitoring_loop(self):
        """Test the monitoring loop functionality."""
        # Start monitoring
        self.detector.start_monitoring()
        
        # Simulate some idle time
        self.platform_detector.set_idle_time(30.0)
        time.sleep(1.1)  # Slightly more than polling_interval
        
        # Should still be active (below threshold)
        self.assertEqual(self.detector.get_current_state(), IdleState.ACTIVE)
        
        # Simulate idle time above threshold
        self.platform_detector.set_idle_time(61.0)
        time.sleep(1.1)  # Slightly more than polling_interval
        
        # Should detect short idle
        self.assertEqual(self.detector.get_current_state(), IdleState.SHORT_IDLE)
        
        # Stop monitoring
        self.detector.stop_monitoring()
        
        # Change state while not monitoring
        self.platform_detector.set_idle_time(0.0)
        time.sleep(1.1)
        
        # State should not change because monitoring is stopped
        self.assertEqual(self.detector.get_current_state(), IdleState.SHORT_IDLE)
    
    def test_statistics(self):
        """Test idle statistics collection."""
        # Start monitoring
        self.detector.start_monitoring()
        
        # Simulate some activity
        self.platform_detector.set_idle_time(0.0)
        time.sleep(0.5)
        
        # Simulate short idle
        self.platform_detector.set_idle_time(61.0)
        time.sleep(1.1)
        
        # Simulate active again
        self.platform_detector.set_idle_time(0.0)
        time.sleep(1.1)
        
        # Get statistics
        stats = self.detector.get_statistics()
        
        # Verify statistics
        self.assertGreaterEqual(stats['total_active_time'], 0.5)
        self.assertGreaterEqual(stats['total_idle_time'], 1.0)
        self.assertGreaterEqual(stats['idle_periods_count'], 1)
        
        # Test getting recent idle periods
        recent_periods = self.detector.get_recent_idle_periods(hours=1)
        self.assertGreaterEqual(len(recent_periods), 1)
        
        # Test resetting statistics
        self.detector.reset_statistics()
        stats = self.detector.get_statistics()
        self.assertEqual(stats['total_active_time'], 0.0)
        self.assertEqual(stats['total_idle_time'], 0.0)
        self.assertEqual(stats['idle_periods_count'], 0)
    
    def test_unsupported_platform(self):
        """Test behavior when platform is not supported."""
        # Create a mock platform detector that's not supported
        mock_platform = MagicMock()
        mock_platform.is_supported.return_value = False
        mock_platform.get_idle_time_seconds.return_value = 0.0
        
        # Patch the platform detector
        with patch('focus_guard.core.activity.idle_detector.IdleDetector._get_platform_detector', 
                  return_value=mock_platform):
            # Create a new detector with unsupported platform
            detector = IdleDetector(self.config)
            
            # Should always report as active on unsupported platforms
            self.assertEqual(detector.get_current_state(), IdleState.ACTIVE)
            self.assertFalse(detector.is_idle())
            
            # Monitoring should still work but not change state
            detector.start_monitoring()
            time.sleep(0.1)
            detector.stop_monitoring()
            self.assertEqual(detector.get_current_state(), IdleState.ACTIVE)


if __name__ == "__main__":
    unittest.main()
