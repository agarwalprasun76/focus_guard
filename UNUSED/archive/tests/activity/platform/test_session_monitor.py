"""
Unit tests for the session monitoring base classes.

This module contains tests for the base session monitoring classes
defined in core_v2.activity.platform.session_monitor.
"""

import unittest
from unittest.mock import Mock, patch
import threading
import time

from core_v2.activity.platform.session_monitor import (
    SessionEvent, SessionListener, SessionMonitor
)


class TestSessionListener(unittest.TestCase):
    """Tests for the SessionListener class."""
    
    def test_abstract_methods(self):
        """Test that SessionListener is an abstract class with required methods."""
        # Attempting to instantiate the abstract class should raise TypeError
        with self.assertRaises(TypeError):
            SessionListener()
        
        # Create a concrete implementation
        class ConcreteListener(SessionListener):
            def on_session_event(self, event_type, event_data):
                pass
        
        # Should be able to instantiate the concrete implementation
        listener = ConcreteListener()
        self.assertIsInstance(listener, SessionListener)


class MockSessionMonitor(SessionMonitor):
    """Mock implementation of SessionMonitor for testing."""
    
    def __init__(self):
        super().__init__()
        self.monitoring_called = False
        self.is_supported_called = False
    
    def _monitoring_loop(self):
        """Mock implementation of the monitoring loop."""
        self.monitoring_called = True
        # Run a short loop to simulate monitoring
        count = 0
        while self.running and count < 3:
            time.sleep(0.1)
            count += 1
    
    @classmethod
    def is_supported(cls):
        """Mock implementation of is_supported."""
        cls.is_supported_called = True
        return True


class TestSessionMonitor(unittest.TestCase):
    """Tests for the SessionMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = MockSessionMonitor()
        
        # Create a mock listener
        self.listener = Mock(spec=SessionListener)
        
    def tearDown(self):
        """Tear down test fixtures."""
        if self.monitor.running:
            self.monitor.stop()
    
    def test_add_listener(self):
        """Test adding a listener to the monitor."""
        # Add the listener
        self.monitor.add_listener(self.listener)
        
        # Verify the listener was added
        self.assertIn(self.listener, self.monitor.listeners)
        
        # Adding the same listener again should not duplicate it
        self.monitor.add_listener(self.listener)
        self.assertEqual(len(self.monitor.listeners), 1)
    
    def test_remove_listener(self):
        """Test removing a listener from the monitor."""
        # Add the listener
        self.monitor.add_listener(self.listener)
        
        # Remove the listener
        self.monitor.remove_listener(self.listener)
        
        # Verify the listener was removed
        self.assertNotIn(self.listener, self.monitor.listeners)
        
        # Removing a non-existent listener should not raise an error
        self.monitor.remove_listener(Mock())
    
    def test_notify_listeners(self):
        """Test notifying listeners of events."""
        # Add the listener
        self.monitor.add_listener(self.listener)
        
        # Notify listeners of a login event
        event_data = {"timestamp": "2025-07-26T12:00:00"}
        self.monitor.notify_listeners(SessionEvent.LOGIN, event_data)
        
        # Verify the listener was notified with the correct arguments
        self.listener.on_session_event.assert_called_once_with(
            SessionEvent.LOGIN, event_data
        )
        
        # Test with a different event
        self.listener.reset_mock()
        self.monitor.notify_listeners(SessionEvent.LOGOUT)
        self.listener.on_session_event.assert_called_once_with(
            SessionEvent.LOGOUT, {}
        )
    
    def test_start_stop(self):
        """Test starting and stopping the monitor."""
        # Start the monitor
        self.monitor.start()
        
        # Verify the monitor is running
        self.assertTrue(self.monitor.running)
        self.assertIsNotNone(self.monitor.thread)
        self.assertTrue(self.monitor.thread.is_alive())
        
        # Starting again should not create a new thread
        original_thread = self.monitor.thread
        self.monitor.start()
        self.assertIs(self.monitor.thread, original_thread)
        
        # Stop the monitor
        self.monitor.stop()
        
        # Verify the monitor is stopped
        self.assertFalse(self.monitor.running)
        
        # Give the thread time to stop
        time.sleep(0.2)
        self.assertFalse(self.monitor.thread.is_alive())
        
        # Stopping again should not raise an error
        self.monitor.stop()
    
    def test_monitoring_loop_called(self):
        """Test that the monitoring loop is called when the monitor is started."""
        # Start the monitor
        self.monitor.start()
        
        # Give the monitoring loop time to run
        time.sleep(0.2)
        
        # Verify the monitoring loop was called
        self.assertTrue(self.monitor.monitoring_called)
        
        # Stop the monitor
        self.monitor.stop()
    
    def test_error_handling_in_listener_notification(self):
        """Test that errors in listeners are caught and don't affect other listeners."""
        # Create a listener that raises an exception
        error_listener = Mock(spec=SessionListener)
        error_listener.on_session_event.side_effect = Exception("Test exception")
        
        # Add both listeners
        self.monitor.add_listener(self.listener)
        self.monitor.add_listener(error_listener)
        
        # Notify listeners
        with self.assertLogs(self.monitor.logger, level='ERROR') as cm:
            self.monitor.notify_listeners(SessionEvent.LOGIN)
        
        # Verify the error was logged
        self.assertIn("Error notifying listener", cm.output[0])
        
        # Verify the good listener was still notified
        self.listener.on_session_event.assert_called_once()


if __name__ == '__main__':
    unittest.main()
