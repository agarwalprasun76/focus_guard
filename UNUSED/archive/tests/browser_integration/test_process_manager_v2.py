#!/usr/bin/env python
"""
Unit tests for the ProcessManager V2 class
"""

import unittest
import signal
import logging
from unittest.mock import patch, MagicMock, call

# Add project root to Python path to import modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.browser_integration.process_manager_v2 import ProcessManager

class TestProcessManagerV2(unittest.TestCase):
    """Test cases for the ProcessManager V2 class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Reset the ProcessManager for each test
        ProcessManager._instance = None
        ProcessManager._cleanup_handlers = []
        ProcessManager._initialized = False
    
    def test_singleton_pattern(self):
        """Test that ProcessManager follows the singleton pattern"""
        # Initialize the process manager
        ProcessManager.init()
        
        # Check that instance is created
        self.assertIsNotNone(ProcessManager._instance)
        self.assertTrue(ProcessManager._initialized)
        
        # Store the instance
        instance1 = ProcessManager._instance
        
        # Initialize again
        ProcessManager.init()
        
        # Check that the instance is the same
        self.assertIs(ProcessManager._instance, instance1)
    
    def test_register_cleanup(self):
        """Test registering cleanup handlers"""
        # Create mock handlers
        handler1 = MagicMock()
        handler2 = MagicMock()
        
        # Register handlers
        ProcessManager.register_cleanup(handler1)
        ProcessManager.register_cleanup(handler2)
        
        # Check that handlers were registered
        self.assertEqual(len(ProcessManager._cleanup_handlers), 2)
        self.assertIn(handler1, ProcessManager._cleanup_handlers)
        self.assertIn(handler2, ProcessManager._cleanup_handlers)
        
        # Register the same handler again
        ProcessManager.register_cleanup(handler1)
        
        # Check that it wasn't added again
        self.assertEqual(len(ProcessManager._cleanup_handlers), 2)
    
    def test_unregister_cleanup(self):
        """Test unregistering cleanup handlers"""
        # Create mock handlers
        handler1 = MagicMock()
        handler2 = MagicMock()
        
        # Register handlers
        ProcessManager.register_cleanup(handler1)
        ProcessManager.register_cleanup(handler2)
        
        # Unregister one handler
        ProcessManager.unregister_cleanup(handler1)
        
        # Check that only one handler remains
        self.assertEqual(len(ProcessManager._cleanup_handlers), 1)
        self.assertNotIn(handler1, ProcessManager._cleanup_handlers)
        self.assertIn(handler2, ProcessManager._cleanup_handlers)
        
        # Unregister non-existent handler
        handler3 = MagicMock()
        ProcessManager.unregister_cleanup(handler3)
        
        # Check that it doesn't affect existing handlers
        self.assertEqual(len(ProcessManager._cleanup_handlers), 1)
    
    def test_cleanup(self):
        """Test that cleanup calls all registered handlers"""
        # Create mock handlers
        handler1 = MagicMock()
        handler2 = MagicMock()
        
        # Register handlers
        ProcessManager.register_cleanup(handler1)
        ProcessManager.register_cleanup(handler2)
        
        # Call cleanup
        ProcessManager.cleanup()
        
        # Check that handlers were called in reverse order
        handler2.assert_called_once()
        handler1.assert_called_once()
    
    def test_cleanup_with_exception(self):
        """Test that cleanup continues even if a handler raises an exception"""
        # Create mock handlers
        handler1 = MagicMock()
        handler2 = MagicMock(side_effect=Exception("Test exception"))
        handler3 = MagicMock()
        
        # Register handlers
        ProcessManager.register_cleanup(handler1)
        ProcessManager.register_cleanup(handler2)
        ProcessManager.register_cleanup(handler3)
        
        # Call cleanup
        with self.assertLogs(level=logging.ERROR) as log:
            ProcessManager.cleanup()
        
        # Check that all handlers were called despite the exception
        handler3.assert_called_once()
        handler2.assert_called_once()
        handler1.assert_called_once()
        
        # Check that the exception was logged
        self.assertTrue(any("Test exception" in msg for msg in log.output))
    
    @patch('signal.signal')
    @patch('atexit.register')
    def test_init(self, mock_atexit_register, mock_signal):
        """Test initialization of the process manager"""
        # Initialize the process manager
        ProcessManager.init()
        
        # Check that atexit.register was called
        mock_atexit_register.assert_called_once_with(ProcessManager.cleanup)
        
        # Check that signal handlers were registered
        self.assertEqual(mock_signal.call_count, 2)
        mock_signal.assert_has_calls([
            call(signal.SIGINT, ProcessManager._handle_signal),
            call(signal.SIGTERM, ProcessManager._handle_signal)
        ], any_order=True)
    
    @patch('signal.signal', side_effect=ValueError("Test signal error"))
    @patch('atexit.register')
    def test_init_signal_error(self, mock_atexit_register, mock_signal):
        """Test initialization when signal registration fails"""
        # Initialize the process manager
        with self.assertLogs(level=logging.WARNING) as log:
            ProcessManager.init()
        
        # Check that atexit.register was still called
        mock_atexit_register.assert_called_once_with(ProcessManager.cleanup)
        
        # Check that the error was logged
        self.assertTrue(any("Test signal error" in msg for msg in log.output))
    
    def test_handle_signal(self):
        """Test signal handler"""
        # Create a mock for cleanup
        with patch.object(ProcessManager, 'cleanup') as mock_cleanup:
            # Call the signal handler, which raises SystemExit
            with self.assertRaises(SystemExit) as cm:
                ProcessManager._handle_signal(signal.SIGINT, None)
            
            # Check that cleanup was called
            mock_cleanup.assert_called_once()
            
            # Check that the exit code is 0
            self.assertEqual(cm.exception.code, 0)

if __name__ == '__main__':
    unittest.main()
