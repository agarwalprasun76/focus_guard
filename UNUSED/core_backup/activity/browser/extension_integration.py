"""
Browser extension integration for activity monitoring.

This module provides functionality for integrating with browser extensions
to gather detailed information about browser tabs.
"""

from typing import Optional, Dict, Any, List
import logging
import json
import time

logger = logging.getLogger(__name__)


class BrowserExtensionIntegration:
    """
    Integration with browser extensions for tab monitoring.
    
    This class provides methods for communicating with browser extensions
    to retrieve information about browser tabs.
    """
    
    def __init__(self, tab_server_url: str = "http://localhost:5000"):
        """
        Initialize the BrowserExtensionIntegration.
        
        Args:
            tab_server_url: URL of the tab server
        
        This constructor sets up any necessary resources for browser extension integration.
        """
        self._browser_integration = None
        self._last_tab_data = {}
        self._last_update_time = 0
        self._cache_ttl = 1.0  # 1 second cache TTL
        self._tab_server_url = tab_server_url
        
    @property
    def browser_integration(self):
        """
        Get the browser integration component.
        
        Returns:
            BrowserIntegration: The browser integration component.
        """
        if self._browser_integration is None:
            try:
                # Import the browser integration component from the browser integration module
                from core_v2.browser.integration import BrowserIntegration
                self._browser_integration = BrowserIntegration(tab_server_url="http://localhost:5000")
                logger.info("Browser integration initialized for extension integration")
            except ImportError as e:
                logger.warning(f"Browser integration not available: {e}")
                self._browser_integration = None
        return self._browser_integration
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently active browser tab.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the
                                     active tab, or None if no tab is active or
                                     information cannot be retrieved.
        """
        tabs = self.get_all_tabs()
        active_tabs = [tab for tab in tabs if tab.get('active', False)]
        
        if active_tabs:
            # Return the first active tab found
            return active_tabs[0]
        return None
    
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """
        Get information about all open browser tabs.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about
                                 all open tabs.
        """
        # Check if we have a recent cache
        current_time = time.time()
        if current_time - self._last_update_time < self._cache_ttl and self._last_tab_data:
            return list(self._last_tab_data.values())
            
        # No recent cache, fetch new data
        if self.browser_integration:
            try:
                # Get tab data from browser integration
                tabs_data = self.browser_integration.get_all_tabs()
                
                # Process and cache the data
                self._last_tab_data = {}
                for tab in tabs_data:
                    tab_id = tab.get('tab_id')
                    if tab_id:
                        self._last_tab_data[tab_id] = tab
                
                self._last_update_time = current_time
                return list(self._last_tab_data.values())
            except Exception as e:
                logger.error(f"Error getting tabs from browser integration: {e}")
                # Fall back to cached data if available
                if self._last_tab_data:
                    return list(self._last_tab_data.values())
        
        # If browser integration is not available or failed, try to use a fallback method
        return self._get_tabs_fallback()
    
    def _get_tabs_fallback(self) -> List[Dict[str, Any]]:
        """
        Fallback method to get browser tabs when browser integration is not available.
        
        This method attempts to use alternative approaches to get tab information,
        such as reading from a local file or using a different API.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about
                                 browser tabs, or an empty list if no information
                                 can be retrieved.
        """
        try:
            # Try to use direct HTTP request to the tab server as a fallback
            import requests
            response = requests.get(f"{self._tab_server_url}/api/tabs")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Fallback tab retrieval failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Error in fallback tab retrieval: {e}")
        
        # If all fallback methods fail, return an empty list
        logger.warning("All fallback methods failed, returning empty tab list")
        return []
    
    def close_tab(self, tab_id: str, window_id: str = None, browser_name: str = None) -> bool:
        """
        Close a browser tab.
        
        Args:
            tab_id: ID of the tab to close.
            window_id: ID of the browser window containing the tab (optional).
            browser_name: Name of the browser (optional).
            
        Returns:
            bool: True if the tab was closed successfully, False otherwise.
        """
        if self.browser_integration:
            try:
                return self.browser_integration.close_tab(tab_id, window_id, browser_name)
            except Exception as e:
                logger.error(f"Error closing tab: {e}")
                
        # Try fallback method if browser integration is not available
        try:
            import requests
            command_data = {
                'action': 'close_tab',
                'data': {
                    'tabId': tab_id
                }
            }
            
            if window_id:
                command_data['data']['windowId'] = window_id
                
            url = f"{self._tab_server_url}/api/command"
            if browser_name:
                from urllib.parse import quote
                url += f"?browser={quote(browser_name)}"
                
            response = requests.post(url, json=command_data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
        except Exception as e:
            logger.error(f"Error in fallback tab closing: {e}")
            
        return False
