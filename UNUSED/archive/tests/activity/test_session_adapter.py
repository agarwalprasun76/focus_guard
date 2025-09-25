"""
Unit tests for the activity session adapter.

This module contains tests for the activity session adapter
defined in core_v2.activity.session_adapter.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import logging

from core_v2.activity.platform.session_monitor import SessionEvent
from core_v2.activity.session_adapter import (
    ActivitySessionAdapter,
    get_activity_session_adapter,
    start_session_monitoring,
    stop_session_monitoring
)


class TestActivitySessionAdapter(unittest.TestCase):
    """Tests for the ActivitySessionAdapter class."""
    
    @patch('core_v2.activity.session_adapter.create_session_monitor')
    def test_init_with_monitor(self, mock_create_monitor):
        """Test initialization with a session monitor."""
        # Create a mock session monitor
        mock_monitor = Mock()
        mock_create_monitor.return_value = mock_monitor
        
        # Create the adapter
        adapter = ActivitySessionAdapter()
        
        # Verify the monitor was created and the adapter was added as a listener
        self.assertEqual(adapter.session_monitor, mock_monitor)
        mock_monitor.add_listener.assert_called_once_with(adapter)
    
    @patch('core_v2.activity.session_adapter.create_session_monitor')
    def test_init_without_monitor(self, mock_create_monitor):
        """Test initialization without a session monitor."""
        # Return None for the session monitor
        mock_create_monitor.return_value = None
        
        # Create the adapter
        with self.assertLogs(level='WARNING') as cm:
            adapter = ActivitySessionAdapter()
        
        # Verify the warning was logged
        self.assertIn("No supported session monitor available", cm.output[0])
        self.assertIsNone(adapter.session_monitor)
    
    @patch('core_v2.activity.session_adapter.pause_activity_logging')
    @patch('core_v2.activity.session_adapter.resume_activity_logging')
    def test_on_session_event_logout(self, mock_resume, mock_pause):
        """Test handling logout events."""
        adapter = ActivitySessionAdapter()
        adapter.session_monitor = Mock()
        
        # Create a logout event
        event_data = {"timestamp": "2025-07-26T12:00:00"}
        
        # Handle the event
        with self.assertLogs(level='INFO') as cm:
            adapter.on_session_event(SessionEvent.LOGOUT, event_data)
        
        # Verify the logging was paused
        mock_pause.assert_called_once()
        mock_resume.assert_not_called()
        self.assertIn("User logout detected", cm.output[0])
    
    @patch('core_v2.activity.session_adapter.pause_activity_logging')
    @patch('core_v2.activity.session_adapter.resume_activity_logging')
    def test_on_session_event_login(self, mock_resume, mock_pause):
        """Test handling login events."""
        adapter = ActivitySessionAdapter()
        adapter.session_monitor = Mock()
        
        # Create a login event
        event_data = {"timestamp": "2025-07-26T12:00:00"}
        
        # Handle the event
        with self.assertLogs(level='INFO') as cm:
            adapter.on_session_event(SessionEvent.LOGIN, event_data)
        
        # Verify the logging was resumed
        mock_resume.assert_called_once()
        mock_pause.assert_not_called()
        self.assertIn("User login detected", cm.output[0])
    
    @patch('core_v2.activity.session_adapter.pause_activity_logging')
    @patch('core_v2.activity.session_adapter.resume_activity_logging')
    def test_on_session_event_lock(self, mock_resume, mock_pause):
        """Test handling lock events."""
        adapter = ActivitySessionAdapter()
        adapter.session_monitor = Mock()
        
        # Create a lock event
        event_data = {"timestamp": "2025-07-26T12:00:00"}
        
        # Handle the event
        with self.assertLogs(level='INFO') as cm:
            adapter.on_session_event(SessionEvent.LOCK, event_data)
        
        # Verify the logging was paused
        mock_pause.assert_called_once()
        mock_resume.assert_not_called()
        self.assertIn("Workstation lock detected", cm.output[0])
    
    @patch('core_v2.activity.session_adapter.pause_activity_logging')
    @patch('core_v2.activity.session_adapter.resume_activity_logging')
    def test_on_session_event_unlock(self, mock_resume, mock_pause):
        """Test handling unlock events."""
        adapter = ActivitySessionAdapter()
        adapter.session_monitor = Mock()
        
        # Create an unlock event
        event_data = {"timestamp": "2025-07-26T12:00:00"}
        
        # Handle the event
        with self.assertLogs(level='INFO') as cm:
            adapter.on_session_event(SessionEvent.UNLOCK, event_data)
        
        # Verify the logging was resumed
        mock_resume.assert_called_once()
        mock_pause.assert_not_called()
        self.assertIn("Workstation unlock detected", cm.output[0])
    
    def test_start(self):
        """Test starting the adapter."""
        adapter = ActivitySessionAdapter()
        adapter.session_monitor = Mock()
        
        # Start the adapter
        with self.assertLogs(level='INFO') as cm:
            adapter.start()
        
        # Verify the monitor was started
        adapter.session_monitor.start.assert_called_once()
        self.assertIn("Session monitoring started", cm.output[0])
    
    def test_start_without_monitor(self):
        """Test starting the adapter without a monitor."""
        adapter = ActivitySessionAdapter()
        adapter.session_monitor = None
        
        # Start the adapter
        with self.assertLogs(level='WARNING') as cm:
            adapter.start()
        
        # Verify the warning was logged
        self.assertIn("Cannot start session monitoring", cm.output[0])
    
    def test_stop(self):
        """Test stopping the adapter."""
        adapter = ActivitySessionAdapter()
        adapter.session_monitor = Mock()
        
        # Stop the adapter
        with self.assertLogs(level='INFO') as cm:
            adapter.stop()
        
        # Verify the monitor was stopped
        adapter.session_monitor.stop.assert_called_once()
        self.assertIn("Session monitoring stopped", cm.output[0])


class TestSessionAdapterSingletonFunctions(unittest.TestCase):
    """Tests for the session adapter singleton functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset the singleton instance
        import core_v2.activity.session_adapter
        core_v2.activity.session_adapter._adapter_instance = None
    
    @patch('core_v2.activity.session_adapter.ActivitySessionAdapter')
    def test_get_activity_session_adapter(self, mock_adapter_class):
        """Test getting the singleton adapter instance."""
        # Create a mock adapter
        mock_adapter = Mock()
        mock_adapter.session_monitor = Mock()
        mock_adapter_class.return_value = mock_adapter
        
        # Get the adapter
        adapter = get_activity_session_adapter()
        
        # Verify the adapter was created
        self.assertEqual(adapter, mock_adapter)
        mock_adapter_class.assert_called_once()
        
        # Getting the adapter again should return the same instance
        mock_adapter_class.reset_mock()
        adapter2 = get_activity_session_adapter()
        self.assertEqual(adapter2, adapter)
        mock_adapter_class.assert_not_called()
    
    @patch('core_v2.activity.session_adapter.ActivitySessionAdapter')
    def test_get_activity_session_adapter_without_monitor(self, mock_adapter_class):
        """Test getting the singleton adapter instance without a monitor."""
        # Create a mock adapter without a monitor
        mock_adapter = Mock()
        mock_adapter.session_monitor = None
        mock_adapter_class.return_value = mock_adapter
        
        # Get the adapter
        adapter = get_activity_session_adapter()
        
        # Verify no adapter was returned
        self.assertIsNone(adapter)
        mock_adapter_class.assert_called_once()
    
    @patch('core_v2.activity.session_adapter.get_activity_session_adapter')
    def test_start_session_monitoring(self, mock_get_adapter):
        """Test starting session monitoring."""
        # Create a mock adapter
        mock_adapter = Mock()
        mock_get_adapter.return_value = mock_adapter
        
        # Start monitoring
        result = start_session_monitoring()
        
        # Verify the adapter was started
        self.assertTrue(result)
        mock_adapter.start.assert_called_once()
    
    @patch('core_v2.activity.session_adapter.get_activity_session_adapter')
    def test_start_session_monitoring_without_adapter(self, mock_get_adapter):
        """Test starting session monitoring without an adapter."""
        # Return None for the adapter
        mock_get_adapter.return_value = None
        
        # Start monitoring
        result = start_session_monitoring()
        
        # Verify the result is False
        self.assertFalse(result)
    
    @patch('core_v2.activity.session_adapter._adapter_instance')
    def test_stop_session_monitoring(self, mock_adapter):
        """Test stopping session monitoring."""
        # Stop monitoring
        result = stop_session_monitoring()
        
        # Verify the adapter was stopped
        self.assertTrue(result)
        mock_adapter.stop.assert_called_once()
    
    def test_stop_session_monitoring_without_adapter(self):
        """Test stopping session monitoring without an adapter."""
        # Stop monitoring
        result = stop_session_monitoring()
        
        # Verify the result is False
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
