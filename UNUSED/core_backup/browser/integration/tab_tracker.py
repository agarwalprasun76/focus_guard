"""
Tab tracker integration module.

This module provides the concrete implementation of the tab tracking functionality,
integrating with browser extensions to monitor tabs.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from core_v2.browser.interfaces import TabTrackerInterface
from core_v2.browser.models.tab import Tab, TabEvent

logger = logging.getLogger(__name__)


class BrowserTabTracker(TabTrackerInterface):
    """Browser tab tracker implementation that integrates with browser extensions."""
    
    def __init__(self, tab_server_url: str = "http://localhost:5000"):
        """Initialize the browser tab tracker.
        
        Args:
            tab_server_url: URL of the tab server
        """
        self._tab_server_url = tab_server_url
        self._tabs: Dict[str, Tab] = {}  # Changed to use string IDs
        self._event_handlers = {event_type: [] for event_type in TabEvent}
        self._last_update_time = 0
        self._cache_ttl = 1.0  # 1 second cache TTL
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._browser_integration = None
    
    def start(self) -> bool:
        """Start tracking tabs."""
        if self._running:
            return True
        
        self._running = True
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()
        logger.info("Tab tracker started")
        return True
    
    def stop(self) -> None:
        """Stop tracking tabs."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        logger.info("Tab tracker stopped")
    
    def get_all_tabs(self) -> List[Tab]:
        """Get all open tabs across all browsers."""
        self._update_tab_data()
        with self._lock:
            return list(self._tabs.values())
    
    def get_active_tab(self) -> Optional[Tab]:
        """Get the currently active tab."""
        self._update_tab_data()
        with self._lock:
            active_tabs = [tab for tab in self._tabs.values() if tab.is_active]
            if active_tabs:
                return active_tabs[0]
        return None
    
    def register_tab_event_handler(self, event_type: TabEvent, handler: Callable[[Tab], None]) -> None:
        """Register a handler for tab events."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)
            logger.debug(f"Registered handler for {event_type} events")
    
    def get_tabs_by_domain(self, domain: str) -> List[Tab]:
        """Get all tabs for a specific domain."""
        if not domain:
            return []
            
        self._update_tab_data()
        with self._lock:
            return [tab for tab in self._tabs.values() 
                    if tab.domain and domain.lower() in tab.domain.lower()]
    
    def get_tabs_by_browser(self, browser_id: str) -> List[Tab]:
        """Get all tabs for a specific browser.
        
        Args:
            browser_id: ID of the browser
            
        Returns:
            List[Tab]: List of tabs for the browser
        """
        if not browser_id:
            return []
            
        self._update_tab_data()
        with self._lock:
            return [tab for tab in self._tabs.values() if tab.browser_id.lower() == browser_id.lower()]
    
    @property
    def browser_integration(self):
        """Get the browser integration component.
        
        Returns:
            BrowserIntegration: The browser integration component.
        """
        if self._browser_integration is None:
            try:
                from core_v2.browser.integration.browser_integration import BrowserIntegration
                self._browser_integration = BrowserIntegration(self._tab_server_url)
                logger.info("Browser integration initialized")
            except ImportError as e:
                logger.warning(f"Browser integration not available: {e}")
                self._browser_integration = None
        return self._browser_integration
    
    def _update_tab_data(self) -> None:
        """Update tab data if cache is expired."""
        current_time = time.time()
        if current_time - self._last_update_time < self._cache_ttl:
            return
        
        if not self.browser_integration:
            logger.warning("Browser integration not available, cannot update tab data")
            return
            
        try:
            # Get tab data from browser integration
            tab_data = self.browser_integration.get_all_tabs()
            
            with self._lock:
                # Process tab data
                new_tabs = {}
                for data in tab_data:
                    tab = Tab.from_dict(data)
                    if tab:
                        new_tabs[tab.id] = tab
                
                # Update tabs
                self._tabs = new_tabs
        except Exception as e:
            logger.error(f"Error updating tab data: {e}")
        
        self._last_update_time = current_time
    
    def _tracking_loop(self) -> None:
        """Background thread for tracking tabs."""
        while self._running:
            try:
                # Get current tabs
                current_tabs = {}
                
                try:
                    if self.browser_integration:
                        # Get tab data from browser integration
                        tab_data = self.browser_integration.get_all_tabs()
                        
                        # Process tab data
                        for data in tab_data:
                            tab = Tab.from_dict(data)
                            if tab:
                                current_tabs[tab.id] = tab
                    else:
                        logger.warning("Browser integration not available, cannot get tab data")
                except Exception as e:
                    logger.error(f"Error getting tab data: {e}")
                
                # Detect tab events
                with self._lock:
                    # Find removed tabs
                    for tab_id, tab in list(self._tabs.items()):
                        if tab_id not in current_tabs:
                            # Tab was removed
                            for handler in self._event_handlers.get(TabEvent.REMOVED, []):
                                try:
                                    handler(tab)
                                except Exception as e:
                                    logger.error(f"Error in tab event handler: {e}")
                    
                    # Find new and updated tabs
                    for tab_id, tab in current_tabs.items():
                        if tab_id not in self._tabs:
                            # New tab
                            for handler in self._event_handlers.get(TabEvent.CREATED, []):
                                try:
                                    handler(tab)
                                except Exception as e:
                                    logger.error(f"Error in tab event handler: {e}")
                        elif tab.url != self._tabs[tab_id].url:
                            # Updated tab
                            for handler in self._event_handlers.get(TabEvent.UPDATED, []):
                                try:
                                    handler(tab)
                                except Exception as e:
                                    logger.error(f"Error in tab event handler: {e}")
                        elif tab.is_active and not self._tabs[tab_id].is_active:
                            # Tab was activated
                            for handler in self._event_handlers.get(TabEvent.ACTIVATED, []):
                                try:
                                    handler(tab)
                                except Exception as e:
                                    logger.error(f"Error in tab event handler: {e}")
                    
                    # Update tabs
                    self._tabs = current_tabs
            except Exception as e:
                logger.error(f"Error in tab tracking loop: {e}")
            
            # Sleep before next update
            time.sleep(1.0)
