#!/usr/bin/env python
"""
Unit tests for the BrowserIntegration V2 class
"""

import unittest
from unittest.mock import patch, MagicMock

# Add project root to Python path to import modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.browser_integration.browser_integration_v2 import (
    BrowserIntegration, get_browser_integration, start_browser_integration,
    stop_browser_integration, is_extension_connected, get_active_tab, get_all_tabs
)

class TestBrowserIntegrationV2(unittest.TestCase):
    """Test cases for the BrowserIntegration V2 class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Reset singleton instances before patching
        import core.browser_integration.browser_integration_v2 as biv2
        import core.browser_integration.tab_tracker_integration_v2 as ttiv2
        biv2._integration_instance = None
        ttiv2._integration_instance = None
        # Create mocks
        self.mock_browser_tracker = MagicMock()
        self.mock_tab_server = MagicMock()
        self.mock_tab_tracker_integration = MagicMock()
        
        # Sample tab data
        self.sample_active_tab = {
            "id": 1,
            "url": "https://example.com",
            "title": "Example Domain",
            "active": True
        }
        
        self.sample_tabs = [
            self.sample_active_tab,
            {
                "id": 2,
                "url": "https://test.com",
                "title": "Test Website",
                "active": False
            }
        ]
        
        self.sample_browser_info = {
            "name": "Microsoft Edge",
            "version": "100.0.0.0"
        }
        
        # Patch the dependencies
        self.tab_server_patcher = patch('core.browser_integration.browser_integration_v2.get_tab_server')
        self.mock_get_tab_server = self.tab_server_patcher.start()
        self.mock_get_tab_server.return_value = self.mock_tab_server
        
        self.tab_tracker_patcher = patch('core.browser_integration.browser_integration_v2.get_tab_tracker_integration')
        self.mock_get_tab_tracker = self.tab_tracker_patcher.start()
        self.mock_get_tab_tracker.return_value = self.mock_tab_tracker_integration
        
        self.process_manager_patcher = patch('core.browser_integration.browser_integration_v2.ProcessManager')
        self.mock_process_manager = self.process_manager_patcher.start()
        
        # Configure the mock tab tracker integration
        self.mock_tab_tracker_integration.get_all_tabs.return_value = self.sample_tabs
        self.mock_tab_tracker_integration.get_active_tab.return_value = self.sample_active_tab
        self.mock_tab_tracker_integration.is_extension_connected.return_value = True
        self.mock_tab_tracker_integration.get_browser_info.return_value = self.sample_browser_info
        
        # Create the integration instance
        self.integration = BrowserIntegration(self.mock_browser_tracker)
    
    def tearDown(self):
        """Clean up after tests"""
        # Stop all patches
        self.tab_server_patcher.stop()
        self.tab_tracker_patcher.stop()
        self.process_manager_patcher.stop()
        
        # Reset the singleton instance
        import core.browser_integration.browser_integration_v2
        core.browser_integration.browser_integration_v2._integration_instance = None
    
    def test_singleton_pattern(self):
        """Test that get_browser_integration returns a singleton instance"""
        # Reset the singleton instance
        import core.browser_integration.browser_integration_v2
        core.browser_integration.browser_integration_v2._integration_instance = None
        
        # Get two instances
        integration1 = get_browser_integration(self.mock_browser_tracker)
        integration2 = get_browser_integration()
        
        # Check that both references point to the same instance
        self.assertIs(integration1, integration2)
        
        # Check that the browser tracker was passed to the tab tracker integration
        self.mock_get_tab_tracker.assert_called_with(self.mock_browser_tracker)
    
    def test_start_stop(self):
        """Test starting and stopping the integration"""
        # Patch BrowserIntegration so all new instances are mocks
        import core.browser_integration.browser_integration_v2 as biv2
        biv2._integration_instance = None
        with patch('core.browser_integration.browser_integration_v2.BrowserIntegration') as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            mock_instance.start.return_value = True

            # Start the integration
            result = start_browser_integration(self.mock_browser_tracker)
            mock_cls.assert_called_with(self.mock_browser_tracker)
            mock_instance.start.assert_called_once()
            self.assertTrue(result)

    
    def test_start_failure(self):
        """Test handling of start failure"""
        import core.browser_integration.browser_integration_v2 as biv2
        biv2._integration_instance = None
        with patch('core.browser_integration.browser_integration_v2.BrowserIntegration') as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            mock_instance.start.return_value = False

            # Start the integration
            result = start_browser_integration(self.mock_browser_tracker)
            mock_cls.assert_called_with(self.mock_browser_tracker)
            mock_instance.start.assert_called_once()
            self.assertFalse(result)

        
        # Start the integration
        result = start_browser_integration(self.mock_browser_tracker)
        
        # Check that the result is False
        self.assertFalse(result)
    
    def test_get_all_tabs(self):
        """Test getting all tabs"""
        # Get all tabs
        tabs = self.integration.get_all_tabs()
        
        # Check that the tab tracker integration was called
        self.mock_tab_tracker_integration.get_all_tabs.assert_called_once()
        
        # Check that the tabs were returned
        self.assertEqual(tabs, self.sample_tabs)
    
    def test_get_active_tab(self):
        """Test getting the active tab"""
        # Get the active tab
        tab = self.integration.get_active_tab()
        
        # Check that the tab tracker integration was called
        self.mock_tab_tracker_integration.get_active_tab.assert_called_once()
        
        # Check that the active tab was returned
        self.assertEqual(tab, self.sample_active_tab)
    
    def test_is_extension_connected(self):
        """Test checking if the extension is connected"""
        # Check if the extension is connected
        connected = self.integration.is_extension_connected()
        
        # Check that the tab tracker integration was called
        self.mock_tab_tracker_integration.is_extension_connected.assert_called_once()
        
        # Check that the result was returned
        self.assertTrue(connected)
    
    def test_get_browser_info(self):
        """Test getting browser information"""
        # Get browser info
        browser_info = self.integration.get_browser_info()
        
        # Check that the tab tracker integration was called
        self.mock_tab_tracker_integration.get_browser_info.assert_called_once()
        
        # Check that the browser info was returned
        self.assertEqual(browser_info, self.sample_browser_info)
    
    def test_module_functions(self):
        """Test the module-level convenience functions"""
        # Reset the singleton instance before patching
        import core.browser_integration.browser_integration_v2 as biv2
        biv2._integration_instance = None
        # Patch BrowserIntegration constructor so all new instances are mocks
        with patch('core.browser_integration.browser_integration_v2.BrowserIntegration') as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance

            # Test start_browser_integration
            mock_instance.start.return_value = True
            result = start_browser_integration(self.mock_browser_tracker)
            mock_cls.assert_called_with(self.mock_browser_tracker)
            mock_instance.start.assert_called_once()
            self.assertTrue(result)

            # Test stop_browser_integration
            stop_browser_integration()
            mock_instance.stop.assert_called_once()
            
            # Test is_extension_connected
            mock_instance.is_extension_connected.return_value = True
            result = is_extension_connected()
            mock_instance.is_extension_connected.assert_called_once()
            self.assertTrue(result)

            # Test get_active_tab
            mock_instance.get_active_tab.return_value = self.sample_active_tab
            tab = get_active_tab()
            mock_instance.get_active_tab.assert_called_once()
            self.assertEqual(tab, self.sample_active_tab)

            # Test get_all_tabs
            mock_instance.get_all_tabs.return_value = self.sample_tabs
            tabs = get_all_tabs()
            mock_instance.get_all_tabs.assert_called_once()
            self.assertEqual(tabs, self.sample_tabs)
    
    def test_module_functions_no_instance(self):
        """Test the module-level functions when no instance exists"""
        # Reset the singleton instance
        import core.browser_integration.browser_integration_v2
        core.browser_integration.browser_integration_v2._integration_instance = None
        
        # Test the functions with no instance
        self.assertFalse(is_extension_connected())
        self.assertIsNone(get_active_tab())
        self.assertEqual(get_all_tabs(), [])

if __name__ == '__main__':
    unittest.main()
