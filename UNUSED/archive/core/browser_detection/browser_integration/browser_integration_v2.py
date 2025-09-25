"""
Browser Integration V2

This module provides a unified interface for the browser integration functionality.
It initializes and manages the tab server, process manager, and tab tracker integration.
"""

import logging
import json
from typing import Dict, List, Any, Optional

from core.browser_detection.browser_integration.process_manager_v2 import ProcessManager
from core.browser_detection.browser_integration.tab_server_v2 import get_tab_server, start_tab_server, stop_tab_server
from core.browser_detection.browser_integration.tab_tracker_integration_v2 import get_tab_tracker_integration, start_integration, stop_integration

logger = logging.getLogger(__name__)

class BrowserIntegration:
    """Main class for browser integration functionality."""
    
    def __init__(self, browser_tracker=None):
        """Initialize the browser integration.
        
        Args:
            browser_tracker: The browser tracker instance to integrate with
        """
        self.tab_server = get_tab_server()
        self.tab_tracker_integration = get_tab_tracker_integration(browser_tracker)
        
        # Register cleanup with the process manager
        ProcessManager.register_cleanup(self.stop)
    
    def start(self) -> bool:
        """Start the browser integration.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        logger.info("Starting browser integration...")
        
        # Start the tab tracker integration (which also starts the tab server)
        if not start_integration():
            logger.error("Failed to start browser integration")
            return False
        
        logger.info("Browser integration started successfully")
        return True
    
    def stop(self) -> None:
        """Stop the browser integration."""
        logger.info("Stopping browser integration...")
        stop_integration()
        logger.info("Browser integration stopped")
    
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """Get all tabs from the browser.
        
        Returns:
            List[Dict[str, Any]]: List of tab data dictionaries
        """
        return self.tab_tracker_integration.get_all_tabs()
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """Get the active tab from the browser.
        
        Returns:
            Optional[Dict[str, Any]]: Active tab data or None if no active tab
        """
        return self.tab_tracker_integration.get_active_tab()
    
    def is_extension_connected(self) -> bool:
        """Check if the browser extension is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.tab_tracker_integration.is_extension_connected()
    
    def get_browser_info(self) -> Dict[str, Any]:
        """Get information about the connected browser.
        
        Returns:
            Dict[str, Any]: Browser information
        """
        return self.tab_tracker_integration.get_browser_info()
    
    def close_tab(self, tab_info: Dict[str, Any]) -> bool:
        """Close a browser tab using the browser extension.
        
        Args:
            tab_info: Dictionary containing tab information with at least tabId and windowId
                {"tabId": int, "windowId": int, "url": str (optional), "domain": str (optional), "reason": str (optional)}
        
        Returns:
            bool: True if the command was sent successfully, False otherwise
        """
        if not tab_info.get('tabId'):
            logger.error("Missing required tabId in tab_info for close_tab")
            return False
            
        # Create the close tab command
        command = {
            "action": "close_tab",
            "data": {
                "tabId": tab_info.get('tabId'),
                "windowId": tab_info.get('windowId'),
                "url": tab_info.get('url'),
                "domain": tab_info.get('domain'),
                "reason": tab_info.get('reason', 'manual_close')
            }
        }
        
        logger.debug(f"DEBUG: Created close_tab command: {json.dumps(command)}")
        logger.debug(f"DEBUG: Tab ID type: {type(tab_info.get('tabId')).__name__}")
        logger.debug(f"DEBUG: Window ID type: {type(tab_info.get('windowId')).__name__} if tab_info.get('windowId') else None")
        logger.debug(f"DEBUG: Tab info keys: {list(tab_info.keys())}")
        logger.debug(f"DEBUG: Tab info values: {list(tab_info.values())}")
        
        
        # Add the command to the tab server's command queue
        try:
            self.tab_server.add_command(command)
            logger.info(f"Tab close command queued for tab {tab_info.get('tabId')}")
            return True
        except Exception as e:
            logger.error(f"Error queueing tab close command: {e}")
            return False


# Singleton instance
_integration_instance = None

def get_browser_integration(browser_tracker=None) -> BrowserIntegration:
    """Get the singleton browser integration instance.
    
    Args:
        browser_tracker: The browser tracker instance to integrate with
        
    Returns:
        BrowserIntegration: The singleton instance
    """
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = BrowserIntegration(browser_tracker)
    elif browser_tracker and _integration_instance.tab_tracker_integration.browser_tracker is None:
        _integration_instance.tab_tracker_integration.browser_tracker = browser_tracker
    return _integration_instance

def start_browser_integration(browser_tracker=None) -> bool:
    """Start the browser integration.
    
    Args:
        browser_tracker: The browser tracker instance to integrate with
        
    Returns:
        bool: True if started successfully, False otherwise
    """
    integration = get_browser_integration(browser_tracker)
    return integration.start()

def stop_browser_integration() -> None:
    """Stop the browser integration."""
    global _integration_instance
    if _integration_instance is not None:
        _integration_instance.stop()

def is_extension_connected() -> bool:
    """Check if the browser extension is connected.
    
    Returns:
        bool: True if connected, False otherwise
    """
    if _integration_instance:
        return _integration_instance.is_extension_connected()
    return False

def get_active_tab() -> Optional[Dict[str, Any]]:
    """Get the active tab from the browser.
    
    Returns:
        Optional[Dict[str, Any]]: Active tab data or None if no active tab
    """
    if _integration_instance:
        return _integration_instance.get_active_tab()
    return None

def get_all_tabs() -> List[Dict[str, Any]]:
    """Get all tabs from the browser.
    
    Returns:
        List[Dict[str, Any]]: List of tab data dictionaries
    """
    if _integration_instance:
        return _integration_instance.get_all_tabs()
    return []

def close_tab(tab_info: Dict[str, Any]) -> bool:
    """Close a browser tab using the browser extension.
    
    Args:
        tab_info: Dictionary containing tab information with at least tabId and windowId
            {"tabId": int, "windowId": int, "url": str (optional), "domain": str (optional), "reason": str (optional)}
    
    Returns:
        bool: True if the command was sent successfully, False otherwise
    """
    if _integration_instance:
        return _integration_instance.close_tab(tab_info)
    return False
