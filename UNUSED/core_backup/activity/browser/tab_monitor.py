"""
Browser tab monitoring functionality.

This module provides functionality for monitoring browser tabs and integrating
with browser extensions to gather more detailed activity information.
"""

from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class BrowserTabMonitor:
    """
    Monitor browser tabs across different browsers.
    
    This class provides methods for retrieving information about active browser
    tabs by integrating with browser extensions or other browser monitoring mechanisms.
    """
    
    def __init__(self):
        """
        Initialize the BrowserTabMonitor.
        
        This constructor sets up any necessary resources for browser tab monitoring.
        """
        self._extension_integration = None
        
    @property
    def extension_integration(self):
        """
        Get the browser extension integration.
        
        Returns:
            BrowserExtensionIntegration: The browser extension integration.
        """
        if self._extension_integration is None:
            try:
                from core_v2.activity.browser.extension_integration import BrowserExtensionIntegration
                self._extension_integration = BrowserExtensionIntegration()
            except ImportError:
                logger.warning("Browser extension integration not available")
                self._extension_integration = None
        return self._extension_integration
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently active browser tab.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the
                                     active tab, or None if no tab is active or
                                     information cannot be retrieved.
                                     
                                     The dictionary contains the following keys:
                                     - url: URL of the tab
                                     - title: Title of the tab
                                     - browser: Name of the browser
                                     - tab_id: ID of the tab
                                     - window_id: ID of the browser window
        """
        if self.extension_integration:
            try:
                return self.extension_integration.get_active_tab()
            except Exception as e:
                logger.error(f"Error getting active tab: {e}")
        return None
    
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """
        Get information about all open browser tabs.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about
                                 all open tabs. Each dictionary has the same format
                                 as returned by get_active_tab().
        """
        if self.extension_integration:
            try:
                return self.extension_integration.get_all_tabs()
            except Exception as e:
                logger.error(f"Error getting all tabs: {e}")
        return []
    
    def get_tabs_by_browser(self, browser_name: str) -> List[Dict[str, Any]]:
        """
        Get information about all open tabs in a specific browser.
        
        Args:
            browser_name: Name of the browser (e.g., "chrome", "firefox").
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about
                                 all open tabs in the specified browser.
        """
        all_tabs = self.get_all_tabs()
        return [tab for tab in all_tabs if tab.get('browser', '').lower() == browser_name.lower()]
    
    def get_tabs_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get information about all open tabs with a specific domain.
        
        Args:
            domain: Domain to filter by.
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about
                                 all open tabs with the specified domain.
        """
        all_tabs = self.get_all_tabs()
        return [tab for tab in all_tabs if domain.lower() in tab.get('url', '').lower()]
