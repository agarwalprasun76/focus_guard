#!/usr/bin/env python
"""
Unit tests for the TabTrackerIntegration V2 class
"""

import unittest
import time
import threading
from unittest.mock import patch, MagicMock, PropertyMock
from core.logger.logger import get_logger

# --- DIAGNOSTIC: Print live threads/processes and thread stacks at interpreter shutdown ---
import atexit
import sys
import threading
import traceback

def print_live_threads_and_processes():
    print("[DEBUG][atexit] Live threads at process end:")
    for t in threading.enumerate():
        print(f" - {t.name} (daemon={t.daemon})")
    print("[DEBUG][atexit] End of live threads list.")
    try:
        import psutil
        current = psutil.Process()
        children = current.children(recursive=True)
        if children:
            print(f"[DEBUG][atexit] Found {len(children)} child processes:")
            for c in children:
                print(f"  - PID {c.pid}: {c.name()} (status={c.status()})")
        else:
            print("[DEBUG][atexit] No child processes found.")
    except ImportError:
        print("[DEBUG][atexit] psutil not installed, skipping child process check.")
    except Exception as e:
        print(f"[DEBUG][atexit] Error checking child processes: {e}")

    # Warn about non-daemon threads
    found_non_daemon = False
    for t in threading.enumerate():
        if t is not threading.current_thread() and not t.daemon:
            print(f"[DEBUG][atexit][WARNING] Thread {t.name} is still alive and is non-daemon.")
            found_non_daemon = True
    if not found_non_daemon:
        print("[DEBUG][atexit] No non-daemon threads remain except main.")

    # Print stack traces of all threads
    print("[DEBUG][atexit] Printing all thread stack traces:")
    for thread_id, frame in sys._current_frames().items():
        print(f"\n[DEBUG][atexit] Thread ID: {thread_id}")
        traceback.print_stack(frame)
    print("[DEBUG][atexit] End of all thread stack traces.")

    # Optionally, forcibly exit (for diagnostics only)
    # import os; os._exit(0)  # Uncomment if you want to guarantee process exit for CI

atexit.register(print_live_threads_and_processes)
# --- END DIAGNOSTIC ---

# logger = get_logger("browser_integration.test_tab_tracker_integration_v2")
# Use print instead of logger to avoid shutdown deadlocks

# Add project root to Python path to import modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.browser_integration.tab_tracker_integration_v2 import TabTrackerIntegration, get_tab_tracker_integration

class TestTabTrackerIntegrationV2(unittest.TestCase):
    """Test cases for the TabTrackerIntegration V2 class"""
    
    def setUp(self):
        """Set up test fixtures"""
        print("TestTabTrackerIntegrationV2.setUp: starting setup...")
        # Create mocks
        self.mock_browser_tracker = MagicMock()
        self.mock_tab_server = MagicMock()
        
        # Sample tab data
        self.sample_tabs = {
            "tabs": [
                {
                    "id": 1,
                    "url": "https://example.com",
                    "title": "Example Domain",
                    "active": True
                },
                {
                    "id": 2,
                    "url": "https://test.com",
                    "title": "Test Website",
                    "active": False
                }
            ],
            "browser": {
                "name": "Microsoft Edge",
                "version": "100.0.0.0"
            },
            "last_update": time.time()
        }
        
        print("TestTabTrackerIntegrationV2.setUp: patching get_tab_server...")
        # Patch the tab_server module
        self.tab_server_patcher = patch('core.browser_integration.tab_tracker_integration_v2.get_tab_server')
        self.mock_get_tab_server = self.tab_server_patcher.start()
        self.mock_get_tab_server.return_value = self.mock_tab_server
        
        print("TestTabTrackerIntegrationV2.setUp: patching ProcessManager...")
        # Patch the process manager
        self.process_manager_patcher = patch('core.browser_integration.tab_tracker_integration_v2.ProcessManager')
        self.mock_process_manager = self.process_manager_patcher.start()
        
        print("TestTabTrackerIntegrationV2.setUp: creating TabTrackerIntegration instance...")
        # Create the integration instance
        self.integration = TabTrackerIntegration(self.mock_browser_tracker)
        print("TestTabTrackerIntegrationV2.setUp: finished setup.")
    
    def force_threads_daemon(self):
        import threading
        for t in threading.enumerate():
            if t is not threading.current_thread():
                t.daemon = True

    def print_live_threads(self):
        import threading
        print("[DEBUG][tearDown] Live threads after test:")
        for t in threading.enumerate():
            print(f" - {t.name} (ident={t.ident}, daemon={t.daemon})")
        print("[DEBUG][tearDown] End of live threads list.")

    def tearDown(self):
        """Clean up after tests"""
        import time
        print(f"[DEBUG] {time.time()} - ENTERING TestTabTrackerIntegrationV2.tearDown")
        # Stop all patches
        self.tab_server_patcher.stop()
        self.process_manager_patcher.stop()
        # Try to stop sync thread if present
        if hasattr(self, 'integration') and hasattr(self.integration, 'sync_thread'):
            sync_thread = self.integration.sync_thread
            print(f"[DEBUG][tearDown] sync_thread alive before join: {sync_thread.is_alive() if sync_thread else None}")
            if sync_thread and sync_thread.is_alive():
                sync_thread.join(timeout=1.0)
                print(f"[DEBUG][tearDown] sync_thread alive after join: {sync_thread.is_alive()}")
                if sync_thread.is_alive():
                    print(f"[DEBUG][WARNING] {time.time()} - Sync thread STILL ALIVE after join!")
        # Reset the singleton instance
        import core.browser_integration.tab_tracker_integration_v2
        core.browser_integration.tab_tracker_integration_v2._integration_instance = None
        self.print_live_threads()
        self.force_threads_daemon()
        print(f"[DEBUG] {time.time()} - LEAVING TestTabTrackerIntegrationV2.tearDown")

    
    def test_singleton_pattern(self):
        """Test that get_tab_tracker_integration returns a singleton instance"""
        # Reset the singleton instance
        import core.browser_integration.tab_tracker_integration_v2
        core.browser_integration.tab_tracker_integration_v2._integration_instance = None
        
        # Get two instances
        integration1 = get_tab_tracker_integration(self.mock_browser_tracker)
        integration2 = get_tab_tracker_integration()
        
        # Check that both references point to the same instance
        self.assertIs(integration1, integration2)
        
        # Check that the browser tracker was set
        self.assertIs(integration1.browser_tracker, self.mock_browser_tracker)
    
    def test_start_stop(self):
        """Test starting and stopping the integration"""
        # Configure the mock tab server
        self.mock_tab_server.start.return_value = True
        
        # Start the integration
        result = self.integration.start()
        
        # Check that the tab server was started
        self.mock_tab_server.start.assert_called_once()
        self.assertTrue(result)
        self.assertTrue(self.integration.running.is_set())
        
        # Check that the sync thread was started
        self.assertIsNotNone(self.integration.sync_thread)
        self.assertTrue(self.integration.sync_thread.is_alive())
        
        # Stop the integration
        self.integration.stop()
        
        # Check that the tab server was stopped
        self.mock_tab_server.stop.assert_called_once()
        self.assertFalse(self.integration.running.is_set())
    
    def test_start_failure(self):
        """Test handling of tab server start failure"""
        # Configure the mock tab server to fail on start
        self.mock_tab_server.start.return_value = False
        
        # Start the integration
        result = self.integration.start()
        
        # Check that the result is False
        self.assertFalse(result)
        
        # Check that the sync thread was not started
        self.assertFalse(self.integration.running.is_set())
    
    def test_get_all_tabs(self):
        """Test getting all tabs"""
        # Configure the mock tab server
        self.mock_tab_server.get_tabs.return_value = self.sample_tabs
        
        # Get all tabs
        tabs = self.integration.get_all_tabs()
        
        # Check that the tab server was called
        self.mock_tab_server.get_tabs.assert_called_once()
        
        # Check that the tabs were returned
        self.assertEqual(tabs, self.sample_tabs["tabs"])
    
    def test_get_active_tab(self):
        """Test getting the active tab"""
        # Configure the mock tab server
        active_tab = self.sample_tabs["tabs"][0]
        self.mock_tab_server.get_active_tab.return_value = active_tab
        
        # Get the active tab
        tab = self.integration.get_active_tab()
        
        # Check that the tab server was called
        self.mock_tab_server.get_active_tab.assert_called_once()
        
        # Check that the active tab was returned
        self.assertEqual(tab, active_tab)
    
    def test_is_extension_connected(self):
        """Test checking if the extension is connected"""
        # Configure the mock tab server
        self.mock_tab_server.is_extension_connected.return_value = True
        
        # Check if the extension is connected
        connected = self.integration.is_extension_connected()
        
        # Check that the tab server was called
        self.mock_tab_server.is_extension_connected.assert_called_once()
        
        # Check that the result was returned
        self.assertTrue(connected)
    
    def test_get_browser_info(self):
        """Test getting browser information"""
        # Configure the mock tab server
        self.mock_tab_server.get_tabs.return_value = self.sample_tabs
        
        # Get browser info
        browser_info = self.integration.get_browser_info()
        
        # Check that the tab server was called
        self.mock_tab_server.get_tabs.assert_called_once()
        
        # Check that the browser info was returned
        self.assertEqual(browser_info, self.sample_tabs["browser"])
    
    def test_sync_tabs(self):
        """Test syncing tabs to the browser tracker"""
        # Configure the mock tab server
        self.mock_tab_server.is_extension_connected.return_value = True
        self.mock_tab_server.get_tabs.return_value = self.sample_tabs
        
        # Call _sync_tabs directly
        self.integration._sync_tabs()
        
        # Check that the browser tracker was updated for each tab
        self.assertEqual(self.mock_browser_tracker._process_tab.call_count, 2)
        
        # Check that the active tab was set as the current tab
        self.mock_browser_tracker.update_tabs.assert_called_once()
        
        # The call should include the synthetic title with domain
        call_args = self.mock_browser_tracker.update_tabs.call_args[0][0]
        self.assertIn("Example Domain", call_args)
        self.assertIn("example.com", call_args)
    
    def test_sync_tabs_no_extension(self):
        """Test syncing tabs when the extension is not connected"""
        # Configure the mock tab server
        self.mock_tab_server.is_extension_connected.return_value = False
        
        # Call _sync_tabs directly
        self.integration._sync_tabs()
        
        # Check that the browser tracker was not updated
        self.mock_browser_tracker._process_tab.assert_not_called()
        self.mock_browser_tracker.update_tabs.assert_not_called()
    
    def test_sync_tabs_no_tabs(self):
        """Test syncing tabs when there are no tabs"""
        # Configure the mock tab server
        self.mock_tab_server.is_extension_connected.return_value = True
        self.mock_tab_server.get_tabs.return_value = {"tabs": []}
        
        # Call _sync_tabs directly
        self.integration._sync_tabs()
        
        # Check that the browser tracker was not updated
        self.mock_browser_tracker._process_tab.assert_not_called()
        self.mock_browser_tracker.update_tabs.assert_not_called()
    
    @patch('time.sleep')
    def test_sync_loop(self, mock_sleep):
        """Test the sync loop"""
        # Configure the mock tab server
        self.mock_tab_server.is_extension_connected.return_value = True
        self.mock_tab_server.get_tabs.return_value = self.sample_tabs
        
        # Configure mock_sleep to stop the loop after a few iterations
        def stop_loop(*args):
            self.integration.running.clear()
        mock_sleep.side_effect = stop_loop
        
        # Start the sync loop
        self.integration.running.set()
        self.integration._sync_loop()
        
        # Check that _sync_tabs was called
        self.mock_tab_server.is_extension_connected.assert_called()
        self.mock_tab_server.get_tabs.assert_called()
        
        # Check that sleep was called with the sync interval
        mock_sleep.assert_called_once_with(self.integration.sync_interval)
    
    def test_sync_loop_exception(self):
        """Test exception handling in the sync loop"""
        from unittest.mock import patch
        with patch('core.browser_integration.tab_tracker_integration_v2.time.sleep') as mock_sleep:
            # Configure the mock tab server to raise an exception and clear running
            def raise_and_stop(*args, **kwargs):
                print("[DEBUG][test_sync_loop_exception] get_tabs.side_effect called, clearing running")
                self.integration.running.clear()
                raise Exception("Test sync error")
            self.mock_tab_server.get_tabs.side_effect = raise_and_stop
            
            # Start the sync loop
            self.integration.running.set()
            
            print("[DEBUG][test_sync_loop_exception] About to call _sync_loop()")
            # Run the sync loop and check that it logs the exception
            with self.assertLogs(level='ERROR') as log:
                self.integration._sync_loop()
            print("[DEBUG][test_sync_loop_exception] _sync_loop() returned")
            
            # Check that the exception was logged
            self.assertTrue(any("Test sync error" in msg for msg in log.output))

        # --- DIAGNOSTIC: Print live threads at end of test ---
        import threading
        print("[DEBUG][test_sync_loop_exception] Live threads at end of test:")
        for t in threading.enumerate():
            print(f" - {t.name} (ident={t.ident}, daemon={t.daemon})")
        print("[DEBUG][test_sync_loop_exception] End of live threads list.")

if __name__ == '__main__':
    unittest.main()
    import threading
    import time
    import sys
    print("[DEBUG] Sleeping 2s to allow for unittest cleanup...")
    time.sleep(2)
    print("[DEBUG] Live threads at process end:")
    for t in threading.enumerate():
        print(f" - {t.name} (daemon={t.daemon})")
    print("[DEBUG] End of live threads list.")
    # On Windows, check for child processes (requires psutil)
    try:
        import psutil
        current = psutil.Process()
        children = current.children(recursive=True)
        if children:
            print(f"[DEBUG] Found {len(children)} child processes:")
            for c in children:
                print(f"  - PID {c.pid}: {c.name()} (status={c.status()})")
        else:
            print("[DEBUG] No child processes found.")
    except ImportError:
        print("[DEBUG] psutil not installed, skipping child process check.")
    except Exception as e:
        print(f"[DEBUG] Error checking child processes: {e}")

