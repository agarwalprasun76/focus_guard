"""
Tab Tracker Integration V2

This module integrates the browser extension tab server v2 with the BrowserTabTracker.
"""

from typing import Dict, List, Optional, Any
import threading
import time
import logging

from core.browser_detection.browser_integration.tab_server_v2 import get_tab_server
from core.browser_detection.browser_integration.process_manager_v2 import ProcessManager
from core.domain_classifier.domain_utils import extract_domain_from_url

logger = logging.getLogger(__name__)

class TabTrackerIntegration:
    """Integrates the browser extension tab server with BrowserTabTracker."""
    
    def __init__(self, browser_tracker=None):
        """Initialize the integration.
        
        Args:
            browser_tracker: The browser tracker instance to integrate with
        """
        self.browser_tracker = browser_tracker
        self.tab_server = get_tab_server()
        self.sync_thread: Optional[threading.Thread] = None
        self.running = threading.Event()
        self.sync_interval = 1.0  # seconds
        
        # Register cleanup with the process manager
        ProcessManager.register_cleanup(self.stop)
    
    def start(self) -> bool:
        """Start the tab server and sync thread.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.running.is_set():
            logger.warning("Tab tracker integration already running")
            return True
        
        # Start the tab server
        if not self.tab_server.start():
            logger.error("Failed to start tab server")
            return False
        
        # Start the sync thread
        self.running.set()
        self.sync_thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name="TabTrackerSyncThread"
        )
        self.sync_thread.start()
        
        logger.info("Tab tracker integration started")
        return True
    
    def stop(self) -> None:
        """Stop the tab server and sync thread."""
        if not self.running.is_set():
            return
        
        # Stop the sync thread
        logger.info("Stopping tab tracker integration...")
        self.running.clear()
        
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=2.0)
            if self.sync_thread.is_alive():
                logger.warning("Sync thread did not shut down cleanly")
        
        # Stop the tab server
        self.tab_server.stop()
        
        logger.info("Tab tracker integration stopped")
    
    def _sync_loop(self) -> None:
        """Continuously sync tab data from the tab server to the browser tracker."""
        logger.info("Tab sync thread started")
        while self.running.is_set():
            try:
                if self.browser_tracker:
                    self._sync_tabs()
                time.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Error in tab sync loop: {e}")
        logger.info("Tab sync thread stopped")
    
    def _sync_tabs(self) -> None:
        """Sync tab data from the tab server to the browser tracker."""
        if not self.tab_server.is_extension_connected():
            return
        
        tab_data = self.tab_server.get_tabs()
        tabs = tab_data.get("tabs", [])
        if not tabs:
            return
        
        # Process each tab
        for tab in tabs:
            url = tab.get("url")
            title = tab.get("title")
            
            if not url or not title:
                continue
            
            # Extract domain from URL
            domain = extract_domain_from_url(url)
            
            # Create a synthetic window title that includes both title and domain
            # This helps the browser tracker correctly classify the tab
            synthetic_title = f"{title} - {domain}" if domain else title
            
            # Update the browser tracker with this tab
            if self.browser_tracker:
                self.browser_tracker._process_tab(synthetic_title)
                
                # If this is the active tab, also update it as the current tab
                if tab.get("active"):
                    self.browser_tracker.update_tabs(synthetic_title)
        
        logger.debug(f"Synced {len(tabs)} tabs from browser extension")
    
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """Get all tabs from the tab server.
        
        Returns:
            List[Dict[str, Any]]: List of tab data dictionaries
        """
        tab_data = self.tab_server.get_tabs()
        return tab_data.get("tabs", [])
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """Get the active tab from the tab server.
        
        Returns:
            Optional[Dict[str, Any]]: Active tab data or None if no active tab
        """
        return self.tab_server.get_active_tab()
    
    def is_extension_connected(self) -> bool:
        """Check if the browser extension is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.tab_server.is_extension_connected()
    
    def get_browser_info(self) -> Dict[str, Any]:
        """Get information about the connected browser.
        
        Returns:
            Dict[str, Any]: Browser information
        """
        tab_data = self.tab_server.get_tabs()
        return tab_data.get("browser", {})


# Singleton instance
_integration_instance = None

def get_tab_tracker_integration(browser_tracker=None) -> TabTrackerIntegration:
    """Get the singleton tab tracker integration instance.
    
    Args:
        browser_tracker: The browser tracker instance to integrate with
        
    Returns:
        TabTrackerIntegration: The singleton instance
    """
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = TabTrackerIntegration(browser_tracker)
    elif browser_tracker and _integration_instance.browser_tracker is None:
        _integration_instance.browser_tracker = browser_tracker
    return _integration_instance

def start_integration(browser_tracker=None) -> bool:
    """Start the tab tracker integration.
    
    Args:
        browser_tracker: The browser tracker instance to integrate with
        
    Returns:
        bool: True if started successfully, False otherwise
    """
    integration = get_tab_tracker_integration(browser_tracker)
    return integration.start()

def stop_integration() -> None:
    """Stop the tab tracker integration."""
    if _integration_instance:
        _integration_instance.stop()
