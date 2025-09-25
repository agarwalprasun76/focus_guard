"""
Browser integration module.

This module provides the concrete implementation of browser integration functionality,
connecting to the tab server to monitor and control browser tabs.
"""

import logging
import requests
import json
import time
from typing import Dict, List, Optional, Any
from urllib.parse import quote

from core_v2.browser.interfaces import BrowserIntegrationInterface
from core_v2.browser.models.tab import Tab
from core_v2.browser.extension.tab_server import get_tab_server, start_tab_server, stop_tab_server
from core_v2.browser.extension.process_manager import get_tab_server_process_manager, start_tab_server_process

logger = logging.getLogger(__name__)


class BrowserIntegration(BrowserIntegrationInterface):
    """Browser integration implementation that connects to the tab server."""
    
    def __init__(self, tab_server_url: str = "http://localhost:5000", auto_start: bool = True):
        """Initialize the browser integration.
        
        Args:
            tab_server_url: URL of the tab server
            auto_start: Whether to automatically start the tab server if it's not running
        """
        self._tab_server_url = tab_server_url
        self._last_update_time = 0
        self._cache_ttl = 1.0  # 1 second cache TTL
        self._tab_cache: List[Dict[str, Any]] = []
        self._tab_server = get_tab_server()
        self._process_manager = get_tab_server_process_manager()
        
        # Auto-start the tab server if requested
        if auto_start:
            self._ensure_tab_server_running()
    
    def _ensure_tab_server_running(self) -> bool:
        """Ensure that the tab server is running.
        
        Returns:
            bool: True if the tab server is running or was started successfully, False otherwise
        """
        # Check if the tab server is already running
        try:
            response = requests.get(f"{self._tab_server_url}/api/status", timeout=1)
            if response.status_code == 200:
                logger.debug("Tab server is already running")
                return True
        except Exception:
            # Tab server is not running or not responding
            pass
            
        # Try to start the tab server using the process manager
        logger.info("Starting tab server process...")
        if self._process_manager.start():
            # Wait for the tab server to become available
            for _ in range(10):  # Wait up to 5 seconds
                try:
                    response = requests.get(f"{self._tab_server_url}/api/status", timeout=0.5)
                    if response.status_code == 200:
                        logger.info("Tab server started successfully")
                        return True
                except Exception:
                    pass
                time.sleep(0.5)
                
            logger.warning("Tab server process started but server is not responding")
            return False
        else:
            logger.error("Failed to start tab server process")
            return False
    
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """Get all open tabs across all browsers.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about all open tabs
        """
        # Ensure the tab server is running
        if not self._ensure_tab_server_running():
            return self._tab_cache if self._tab_cache else []
            
        current_time = time.time()
        if current_time - self._last_update_time < self._cache_ttl and self._tab_cache:
            return self._tab_cache
            
        try:
            # Try to get tabs directly from the tab server object first
            if self._tab_server:
                tabs_data = self._tab_server.get_tabs()
                if tabs_data:
                    # Process tab data to ensure consistent format
                    processed_tabs = []
                    for tab in tabs_data:
                        processed_tab = {
                            'tab_id': tab.get('id', ''),
                            'window_id': tab.get('windowId', ''),
                            'url': tab.get('url', ''),
                            'title': tab.get('title', ''),
                            'browser': tab.get('browser', ''),
                            'active': tab.get('active', False),
                            'domain': self._extract_domain(tab.get('url', '')),
                            'timestamp': tab.get('timestamp', current_time)
                        }
                        processed_tabs.append(processed_tab)
                    
                    self._tab_cache = processed_tabs
                    self._last_update_time = current_time
                    return processed_tabs
            
            # Fall back to HTTP API if direct access fails
            response = requests.get(f"{self._tab_server_url}/api/tabs")
            if response.status_code == 200:
                tabs_data = response.json()
                
                # Process tab data to ensure consistent format
                processed_tabs = []
                for tab in tabs_data:
                    processed_tab = {
                        'tab_id': tab.get('id', ''),
                        'window_id': tab.get('windowId', ''),
                        'url': tab.get('url', ''),
                        'title': tab.get('title', ''),
                        'browser': tab.get('browser', ''),
                        'active': tab.get('active', False),
                        'domain': self._extract_domain(tab.get('url', '')),
                        'timestamp': tab.get('timestamp', current_time)
                    }
                    processed_tabs.append(processed_tab)
                
                self._tab_cache = processed_tabs
                self._last_update_time = current_time
                return processed_tabs
            else:
                logger.warning(f"Failed to get tab data: {response.status_code}")
                return self._tab_cache if self._tab_cache else []
        except Exception as e:
            logger.error(f"Error getting tabs from tab server: {e}")
            return self._tab_cache if self._tab_cache else []
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """Get the currently active tab.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the active tab,
                                     or None if no tab is active
        """
        # Ensure the tab server is running
        if not self._ensure_tab_server_running():
            return None
            
        # Try to get the active tab directly from the tab server object first
        if self._tab_server:
            try:
                active_tab = self._tab_server.get_active_tab()
                if active_tab:
                    # Process tab data to ensure consistent format
                    current_time = time.time()
                    processed_tab = {
                        'tab_id': active_tab.get('id', ''),
                        'window_id': active_tab.get('windowId', ''),
                        'url': active_tab.get('url', ''),
                        'title': active_tab.get('title', ''),
                        'browser': active_tab.get('browser', ''),
                        'active': True,
                        'domain': self._extract_domain(active_tab.get('url', '')),
                        'timestamp': active_tab.get('timestamp', current_time)
                    }
                    return processed_tab
            except Exception as e:
                logger.warning(f"Failed to get active tab directly from tab server: {e}, falling back to HTTP API")
                # Fall through to HTTP API
        
        # Fall back to filtering all tabs
        tabs = self.get_all_tabs()
        active_tabs = [tab for tab in tabs if tab.get('active', False)]
        
        if active_tabs:
            return active_tabs[0]
        return None
    
    def is_extension_connected(self, browser_name: str = None) -> bool:
        """Check if the browser extension is connected.
        
        Args:
            browser_name: Name of the browser to check (optional)
            
        Returns:
            bool: True if the extension is connected, False otherwise
        """
        # Ensure the tab server is running
        if not self._ensure_tab_server_running():
            return False
            
        try:
            # Try to check connection status directly from the tab server object first
            if self._tab_server:
                return self._tab_server.is_extension_connected(browser_name)
                
            # Fall back to HTTP API if direct access fails
            response = requests.get(f"{self._tab_server_url}/api/status")
            if response.status_code == 200:
                status_data = response.json()
                
                if browser_name:
                    # Check specific browser connection status
                    browser_statuses = status_data.get('browser_statuses', {})
                    return browser_statuses.get(browser_name, {}).get('connected', False)
                else:
                    # Check overall extension connection status
                    return status_data.get('extension_connected', False)
            else:
                logger.warning(f"Failed to get extension status: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error checking extension connection: {e}")
            return False
    
    def close_tab(self, tab_id: str, window_id: str = None, browser_name: str = None) -> bool:
        """Close a browser tab.
        
        Args:
            tab_id: ID of the tab to close
            window_id: ID of the window containing the tab (optional)
            browser_name: Name of the browser (optional)
            
        Returns:
            bool: True if the tab was closed successfully, False otherwise
        """
        # Ensure the tab server is running
        if not self._ensure_tab_server_running():
            return False
            
        try:
            command_data = {
                'action': 'close_tab',
                'data': {
                    'tabId': tab_id
                }
            }
            
            if window_id:
                command_data['data']['windowId'] = window_id
            
            # Try to add the command directly to the tab server object first
            if self._tab_server:
                try:
                    self._tab_server.add_command(command_data)
                    logger.info(f"Tab close command queued for tab {tab_id}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to add command directly to tab server: {e}, falling back to HTTP API")
                    # Fall through to HTTP API
                
            # Fall back to HTTP API if direct access fails
            if browser_name:
                # Add browser parameter to URL
                browser_param = f"?browser={quote(browser_name)}"
                url = f"{self._tab_server_url}/api/command{browser_param}"
            else:
                url = f"{self._tab_server_url}/api/command"
                
            response = requests.post(url, json=command_data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            else:
                logger.warning(f"Failed to close tab: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error closing tab: {e}")
            return False
    
    def send_command(self, command: str, data: Dict[str, Any], browser_name: str = None) -> bool:
        """Send a command to the browser extension.
        
        Args:
            command: Command to send
            data: Data to send with the command
            browser_name: Name of the browser (optional)
            
        Returns:
            bool: True if the command was sent successfully, False otherwise
        """
        # Ensure the tab server is running
        if not self._ensure_tab_server_running():
            return False
            
        try:
            command_data = {
                'action': command,
                'data': data
            }
            
            # Try to add the command directly to the tab server object first
            if self._tab_server:
                try:
                    self._tab_server.add_command(command_data)
                    logger.info(f"Command '{command}' queued successfully")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to add command directly to tab server: {e}, falling back to HTTP API")
                    # Fall through to HTTP API
            
            # Fall back to HTTP API if direct access fails
            if browser_name:
                # Add browser parameter to URL
                browser_param = f"?browser={quote(browser_name)}"
                url = f"{self._tab_server_url}/api/command{browser_param}"
            else:
                url = f"{self._tab_server_url}/api/command"
                
            response = requests.post(url, json=command_data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            else:
                logger.warning(f"Failed to send command: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            str: Domain name
        """
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
                
            return domain
        except Exception:
            return ''
