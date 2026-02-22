"""
Browser extension integration for activity monitoring.

This module provides functionality for integrating with browser extensions
to gather detailed information about browser tabs.
"""

from typing import Optional, Dict, Any, List
import logging
import json
import time

from focus_guard.core.tab_server_endpoint import resolve_tab_server_base_url

logger = logging.getLogger(__name__)


class BrowserExtensionIntegration:
    """
    Integration with browser extensions for tab monitoring.
    
    This class provides methods for communicating with browser extensions
    to retrieve information about browser tabs.
    """
    
    def __init__(self, tab_server_url: Optional[str] = None):
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
        self._tab_server_url = tab_server_url or resolve_tab_server_base_url()
        
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently active browser tab.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the
                                     active tab, or None if no tab is active or
                                     information cannot be retrieved.
        """
        tabs = self.get_all_tabs()
        for tab in tabs:
            if isinstance(tab, dict) and tab.get('active', False):
                return tab
        return None
    
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """
        Get information about all open browser tabs via the local tab server.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about
                                 all open tabs.
        """
        current_time = time.time()
        if current_time - self._last_update_time < self._cache_ttl and self._last_tab_data:
            return list(self._last_tab_data.values())

        try:
            import requests
            response = requests.get(
                f"{self._tab_server_url}/api/tabs", timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                # The /api/tabs endpoint returns {"tabs": [...], "browsers": [...]}
                tabs_list = data.get("tabs", data) if isinstance(data, dict) else data
                if not isinstance(tabs_list, list):
                    tabs_list = []

                self._last_tab_data = {}
                for tab in tabs_list:
                    if not isinstance(tab, dict):
                        continue
                    tab_id = tab.get('id') or tab.get('tab_id')
                    if tab_id:
                        self._last_tab_data[str(tab_id)] = tab

                self._last_update_time = current_time
                return list(self._last_tab_data.values())
        except Exception as e:
            logger.debug("Tab server query failed: %s", e)

        # Return cached data if available
        if self._last_tab_data:
            return list(self._last_tab_data.values())
        return []
    
    def close_tab(self, tab_id: str, window_id: str = None, browser_name: str = None) -> bool:
        """
        Close a browser tab via the tab server command API.
        
        Args:
            tab_id: ID of the tab to close.
            window_id: ID of the browser window containing the tab (optional).
            browser_name: Name of the browser (optional).
            
        Returns:
            bool: True if the tab was closed successfully, False otherwise.
        """
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
                
            response = requests.post(url, json=command_data, timeout=2)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
        except Exception as e:
            logger.error(f"Error closing tab: {e}")
            
        return False
