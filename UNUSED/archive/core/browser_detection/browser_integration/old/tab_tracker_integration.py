"""
Tab Tracker Integration

This module integrates the browser extension tab server with the BrowserTabTracker.
"""

from typing import Dict, List, Optional, Any
import threading
import time

from core.logger.logger import get_logger
from core.browser_integration.tab_server import get_tab_server
from core.domain_classifier.domain_utils import extract_domain_from_url

class TabTrackerIntegration:
    """Integrates the browser extension tab server with BrowserTabTracker."""
    
    def __init__(self, browser_tracker=None):
        """Initialize the integration."""
        self.logger = get_logger("tab_tracker_integration")
        self.browser_tracker = browser_tracker
        self.tab_server = get_tab_server()
        self.sync_thread = None
        self.running = False
        self.sync_interval = 1.0  # seconds
    
    def start(self):
        """Start the tab server and sync thread."""
        if self.running:
            return
        
        # Start the tab server
        self.tab_server.start()
        
        # Start the sync thread
        self.running = True
        self.sync_thread = threading.Thread(target=self._sync_loop)
        self.sync_thread.daemon = True
        self.sync_thread.start()
        
        self.logger.info("Tab tracker integration started")
    
    def stop(self):
        """Stop the tab server and sync thread."""
        if not self.running:
            return
        
        # Stop the sync thread
        self.running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=2.0)
        
        # Stop the tab server
        self.tab_server.stop()
        
        self.logger.info("Tab tracker integration stopped")
    
    def _sync_loop(self):
        """Continuously sync tab data from the tab server to the browser tracker."""
        while self.running:
            try:
                if self.browser_tracker:
                    self._sync_tabs()
                time.sleep(self.sync_interval)
            except Exception as e:
                self.logger.error(f"Error in tab sync loop: {e}")
    
    def _sync_tabs(self):
        """Sync tab data from the tab server to the browser tracker."""
        if not self.tab_server.is_extension_connected():
            return
        
        tabs = self.tab_server.get_tabs()
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
        
        self.logger.debug(f"Synced {len(tabs)} tabs from browser extension")
    
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """Get all tabs from the tab server."""
        return self.tab_server.get_tabs()
    
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """Get the active tab from the tab server."""
        return self.tab_server.get_active_tab()
    
    def is_extension_connected(self) -> bool:
        """Check if the browser extension is connected."""
        return self.tab_server.is_extension_connected()


# Singleton instance
_integration_instance = None

def get_tab_tracker_integration(browser_tracker=None) -> TabTrackerIntegration:
    """Get the singleton tab tracker integration instance."""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = TabTrackerIntegration(browser_tracker)
    elif browser_tracker and _integration_instance.browser_tracker is None:
        _integration_instance.browser_tracker = browser_tracker
    return _integration_instance
