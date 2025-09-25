"""
Browser extension integration module.

This module provides a unified interface for integrating all browser extension
components, including tab server, process manager, and extension management.
"""

import logging
import time
from typing import Optional, Dict, Any, List

from core_v2.browser.models.browser import BrowserType
from core_v2.browser.extension.tab_server import get_tab_server, start_tab_server, stop_tab_server
from core_v2.browser.extension.process_manager import (
    get_tab_server_process_manager,
    start_tab_server_process,
    stop_tab_server_process
)
from core_v2.browser.extension.manager import BrowserExtensionManager
from core_v2.browser.integration.browser_integration import BrowserIntegration

logger = logging.getLogger(__name__)


class ExtensionIntegration:
    """Integration class for browser extension components."""
    
    def __init__(self, 
                 tab_server_url: str = "http://localhost:5000",
                 auto_start_tab_server: bool = True):
        """Initialize the extension integration.
        
        Args:
            tab_server_url: URL of the tab server
            auto_start_tab_server: Whether to automatically start the tab server
        """
        self._tab_server_url = tab_server_url
        self._auto_start = auto_start_tab_server
        
        # Initialize components
        self._process_manager = get_tab_server_process_manager()
        self._tab_server = get_tab_server()
        self._extension_manager = BrowserExtensionManager(tab_server_url=tab_server_url)
        self._browser_integration = BrowserIntegration(tab_server_url=tab_server_url, auto_start=auto_start_tab_server)
        
        # Start the tab server if requested
        if auto_start_tab_server:
            self.ensure_tab_server_running()
    
    def ensure_tab_server_running(self) -> bool:
        """Ensure that the tab server is running.
        
        Returns:
            bool: True if the tab server is running or was started successfully
        """
        # Check if the tab server is already running via the process manager
        if self._process_manager.is_running():
            logger.debug("Tab server process is already running")
            return True
            
        # Start the tab server process
        logger.info("Starting tab server process...")
        if start_tab_server_process():
            # Wait for the tab server to become available
            for _ in range(10):  # Wait up to 5 seconds
                if self._tab_server and self._tab_server.is_server_running():
                    logger.info("Tab server started successfully")
                    return True
                time.sleep(0.5)
                
            logger.warning("Tab server process started but server is not responding")
            return False
        else:
            logger.error("Failed to start tab server process")
            return False
    
    def stop_tab_server(self) -> None:
        """Stop the tab server."""
        logger.info("Stopping tab server...")
        stop_tab_server_process()
    
    def install_extension(self, browser_type: BrowserType) -> bool:
        """Install the extension for a browser type.
        
        Args:
            browser_type: Type of browser to install for
            
        Returns:
            bool: True if the extension was installed successfully
        """
        # Ensure the tab server is running
        if not self.ensure_tab_server_running():
            logger.error("Cannot install extension: tab server is not running")
            return False
            
        # Install the extension
        return self._extension_manager.install_extension(browser_type)
    
    def verify_extension_connection(self, browser_type: BrowserType, timeout_seconds: int = 30) -> bool:
        """Verify that the extension is properly connected to the tab server.
        
        Args:
            browser_type: Type of browser to verify
            timeout_seconds: Timeout for verification
            
        Returns:
            bool: True if connection is verified, False otherwise
        """
        # Ensure the tab server is running
        if not self.ensure_tab_server_running():
            logger.error("Cannot verify extension connection: tab server is not running")
            return False
            
        # Verify the extension connection
        return self._extension_manager.verify_extension_connection(browser_type, timeout_seconds)
    
    def is_extension_installed(self, browser_type: BrowserType) -> bool:
        """Check if the extension is installed for a browser type.
        
        Args:
            browser_type: Type of browser to check
            
        Returns:
            bool: True if the extension is installed
        """
        return self._extension_manager.is_extension_installed(browser_type)
    
    def update_extension(self, browser_type: BrowserType) -> bool:
        """Update the extension for a browser type.
        
        Args:
            browser_type: Type of browser to update
            
        Returns:
            bool: True if the extension was updated successfully
        """
        return self._extension_manager.update_extension(browser_type)
    
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """Get all open tabs across all browsers.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about all open tabs
        """
        return self._browser_integration.get_all_tabs()
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """Get the currently active tab.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the active tab,
                                     or None if no tab is active
        """
        return self._browser_integration.get_active_tab()
    
    def is_extension_connected(self, browser_name: str = None) -> bool:
        """Check if the browser extension is connected.
        
        Args:
            browser_name: Name of the browser to check (optional)
            
        Returns:
            bool: True if the extension is connected, False otherwise
        """
        return self._browser_integration.is_extension_connected(browser_name)
    
    def close_tab(self, tab_id: str, window_id: str = None, browser_name: str = None) -> bool:
        """Close a browser tab.
        
        Args:
            tab_id: ID of the tab to close
            window_id: ID of the window containing the tab (optional)
            browser_name: Name of the browser (optional)
            
        Returns:
            bool: True if the tab was closed successfully, False otherwise
        """
        return self._browser_integration.close_tab(tab_id, window_id, browser_name)
    
    def send_command(self, command: str, data: Dict[str, Any], browser_name: str = None) -> bool:
        """Send a command to the browser extension.
        
        Args:
            command: Command to send
            data: Data to send with the command
            browser_name: Name of the browser (optional)
            
        Returns:
            bool: True if the command was sent successfully, False otherwise
        """
        return self._browser_integration.send_command(command, data, browser_name)
    
    def get_tab_server_status(self) -> Dict[str, Any]:
        """Get the status of the tab server.
        
        Returns:
            Dict[str, Any]: Status information
        """
        return self._process_manager.get_status()
    
    def restart_tab_server(self) -> bool:
        """Restart the tab server.
        
        Returns:
            bool: True if the tab server was restarted successfully
        """
        return self._process_manager.restart()


# Singleton instance
_integration_instance = None

def get_extension_integration(**kwargs) -> ExtensionIntegration:
    """Get the singleton extension integration instance.
    
    Args:
        **kwargs: Arguments to pass to the ExtensionIntegration constructor
        
    Returns:
        ExtensionIntegration: The singleton instance
    """
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = ExtensionIntegration(**kwargs)
    return _integration_instance

def install_browser_extension(browser_type: BrowserType) -> bool:
    """Install the browser extension for a browser type.
    
    Args:
        browser_type: Type of browser to install for
        
    Returns:
        bool: True if the extension was installed successfully
    """
    integration = get_extension_integration()
    return integration.install_extension(browser_type)

def verify_extension_connection(browser_type: BrowserType, timeout_seconds: int = 30) -> bool:
    """Verify that the extension is properly connected to the tab server.
    
    Args:
        browser_type: Type of browser to verify
        timeout_seconds: Timeout for verification
        
    Returns:
        bool: True if connection is verified, False otherwise
    """
    integration = get_extension_integration()
    return integration.verify_extension_connection(browser_type, timeout_seconds)

def close_browser_tab(tab_id: str, window_id: str = None, browser_name: str = None) -> bool:
    """Close a browser tab.
    
    Args:
        tab_id: ID of the tab to close
        window_id: ID of the window containing the tab (optional)
        browser_name: Name of the browser (optional)
        
    Returns:
        bool: True if the tab was closed successfully, False otherwise
    """
    integration = get_extension_integration()
    return integration.close_tab(tab_id, window_id, browser_name)

def get_active_browser_tab() -> Optional[Dict[str, Any]]:
    """Get the currently active browser tab.
    
    Returns:
        Optional[Dict[str, Any]]: Dictionary containing information about the active tab,
                                 or None if no tab is active
    """
    integration = get_extension_integration()
    return integration.get_active_tab()

def get_all_browser_tabs() -> List[Dict[str, Any]]:
    """Get all open browser tabs.
    
    Returns:
        List[Dict[str, Any]]: List of dictionaries containing information about all open tabs
    """
    integration = get_extension_integration()
    return integration.get_all_tabs()
