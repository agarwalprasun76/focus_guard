#!/usr/bin/env python
"""
Chrome DevTools Protocol Client

This module provides a client for interacting with Chrome/Edge browsers via the Chrome DevTools Protocol (CDP).
It allows for programmatic control of browser tabs, including listing and closing tabs.

References:
- Chrome DevTools Protocol: https://chromedevtools.github.io/devtools-protocol/
"""

import json
import logging
import requests
import time
import websocket
from typing import Dict, List, Optional, Any, Union, Tuple
from urllib.parse import urljoin

# Setup logging
logger = logging.getLogger("chrome_devtools_client")


class ChromeDevToolsClient:
    """
    Client for interacting with Chrome/Edge browsers via the Chrome DevTools Protocol.
    
    This class provides methods to:
    1. Connect to Chrome's debugging interface
    2. List all open tabs
    3. Close specific tabs
    4. Execute other CDP commands
    """
    
    def __init__(self, host: str = "localhost", port: int = 9222):
        """
        Initialize the Chrome DevTools Protocol client.
        
        Args:
            host: The hostname where Chrome is running with remote debugging enabled
            port: The remote debugging port (default is 9222)
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_connections = {}  # Store WebSocket connections by tab id
        
        logger.info(f"Initialized Chrome DevTools client for {self.base_url}")
    
    def get_tabs(self) -> List[Dict[str, Any]]:
        """
        Get a list of all open tabs in the browser.
        
        Returns:
            List of tab information dictionaries
        
        Raises:
            ConnectionError: If unable to connect to the debugging interface
        """
        try:
            response = requests.get(urljoin(self.base_url, "/json/list"))
            response.raise_for_status()
            tabs = response.json()
            logger.debug(f"Found {len(tabs)} tabs")
            return tabs
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get tabs: {e}")
            raise ConnectionError(f"Failed to connect to Chrome debugging interface: {e}")
    
    def find_tab_by_url(self, url_pattern: str) -> Optional[Dict[str, Any]]:
        """
        Find a tab by matching its URL against a pattern.
        
        Args:
            url_pattern: String pattern to match against tab URLs
            
        Returns:
            Tab information dictionary or None if not found
        """
        try:
            tabs = self.get_tabs()
            for tab in tabs:
                if url_pattern in tab.get("url", ""):
                    logger.debug(f"Found tab matching '{url_pattern}': {tab.get('title', 'Unknown')}")
                    return tab
            logger.debug(f"No tab found matching '{url_pattern}'")
            return None
        except ConnectionError:
            logger.error("Could not find tab - connection to debugging interface failed")
            return None
    
    def find_tab_by_title(self, title_pattern: str) -> Optional[Dict[str, Any]]:
        """
        Find a tab by matching its title against a pattern.
        
        Args:
            title_pattern: String pattern to match against tab titles
            
        Returns:
            Tab information dictionary or None if not found
        """
        try:
            tabs = self.get_tabs()
            for tab in tabs:
                if title_pattern in tab.get("title", ""):
                    logger.debug(f"Found tab matching title '{title_pattern}': {tab.get('url', 'Unknown')}")
                    return tab
            logger.debug(f"No tab found matching title '{title_pattern}'")
            return None
        except ConnectionError:
            logger.error("Could not find tab - connection to debugging interface failed")
            return None
    
    def close_tab(self, tab_id: str) -> bool:
        """
        Close a specific tab by its ID.
        
        Args:
            tab_id: The ID of the tab to close
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = requests.get(urljoin(self.base_url, f"/json/close/{tab_id}"))
            response.raise_for_status()
            logger.info(f"Successfully closed tab {tab_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to close tab {tab_id}: {e}")
            return False
    
    def close_tab_by_url(self, url_pattern: str) -> bool:
        """
        Close a tab that matches the given URL pattern.
        
        Args:
            url_pattern: String pattern to match against tab URLs
            
        Returns:
            bool: True if a tab was found and closed, False otherwise
        """
        tab = self.find_tab_by_url(url_pattern)
        if tab and "id" in tab:
            return self.close_tab(tab["id"])
        return False
    
    def close_tab_by_title(self, title_pattern: str) -> bool:
        """
        Close a tab that matches the given title pattern.
        
        Args:
            title_pattern: String pattern to match against tab titles
            
        Returns:
            bool: True if a tab was found and closed, False otherwise
        """
        tab = self.find_tab_by_title(title_pattern)
        if tab and "id" in tab:
            return self.close_tab(tab["id"])
        return False
    
    def _connect_websocket(self, tab_id: str, websocket_url: str) -> Optional[websocket.WebSocket]:
        """
        Connect to a tab's WebSocket for sending CDP commands.
        
        Args:
            tab_id: The ID of the tab
            websocket_url: The WebSocket URL for the tab
            
        Returns:
            WebSocket connection or None if connection failed
        """
        try:
            ws = websocket.create_connection(websocket_url)
            self.ws_connections[tab_id] = ws
            logger.debug(f"Connected to WebSocket for tab {tab_id}")
            return ws
        except (websocket.WebSocketException, ConnectionError) as e:
            logger.error(f"Failed to connect to WebSocket for tab {tab_id}: {e}")
            return None
    
    def send_command(self, tab_id: str, method: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Send a CDP command to a specific tab.
        
        Args:
            tab_id: The ID of the tab
            method: The CDP method to call
            params: Parameters for the method (optional)
            
        Returns:
            Response from the CDP command or None if failed
        """
        # Find the tab to get its WebSocket URL
        try:
            tabs = self.get_tabs()
            tab = next((t for t in tabs if t.get("id") == tab_id), None)
            if not tab or "webSocketDebuggerUrl" not in tab:
                logger.error(f"Tab {tab_id} not found or doesn't have WebSocket URL")
                return None
            
            # Connect to WebSocket if not already connected
            ws = self.ws_connections.get(tab_id)
            if not ws:
                ws = self._connect_websocket(tab_id, tab["webSocketDebuggerUrl"])
                if not ws:
                    return None
            
            # Send command
            command = {
                "id": int(time.time() * 1000),  # Use timestamp as ID
                "method": method,
                "params": params or {}
            }
            
            ws.send(json.dumps(command))
            response = json.loads(ws.recv())
            
            if "error" in response:
                logger.error(f"CDP command error: {response['error']}")
                return None
                
            return response.get("result")
            
        except Exception as e:
            logger.error(f"Error sending CDP command: {e}")
            return None
    
    def navigate_to_url(self, tab_id: str, url: str) -> bool:
        """
        Navigate a tab to a specific URL.
        
        Args:
            tab_id: The ID of the tab
            url: The URL to navigate to
            
        Returns:
            bool: True if successful, False otherwise
        """
        result = self.send_command(tab_id, "Page.navigate", {"url": url})
        return result is not None
    
    def is_chrome_available(self) -> bool:
        """
        Check if Chrome with remote debugging is available.
        
        Returns:
            bool: True if Chrome debugging interface is accessible
        """
        try:
            self.get_tabs()
            return True
        except ConnectionError:
            return False
    
    def close_all_connections(self):
        """
        Close all WebSocket connections.
        """
        for tab_id, ws in self.ws_connections.items():
            try:
                ws.close()
                logger.debug(f"Closed WebSocket connection for tab {tab_id}")
            except Exception as e:
                logger.error(f"Error closing WebSocket for tab {tab_id}: {e}")
        
        self.ws_connections = {}


# Simple test function
def test_chrome_devtools():
    """
    Test the Chrome DevTools client functionality.
    """
    client = ChromeDevToolsClient()
    
    if not client.is_chrome_available():
        print("Chrome with remote debugging is not available.")
        print("Please start Chrome with: chrome.exe --remote-debugging-port=9222")
        return
    
    # List all tabs
    tabs = client.get_tabs()
    print(f"Found {len(tabs)} tabs:")
    for i, tab in enumerate(tabs):
        print(f"{i+1}. {tab.get('title', 'Unknown')} - {tab.get('url', 'No URL')}")
    
    # Close a tab by URL pattern (if any tabs exist)
    if tabs:
        url_pattern = input("Enter URL pattern to close (or press Enter to skip): ")
        if url_pattern:
            success = client.close_tab_by_url(url_pattern)
            print(f"Tab close {'succeeded' if success else 'failed'}")
    
    # Clean up
    client.close_all_connections()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    test_chrome_devtools()
