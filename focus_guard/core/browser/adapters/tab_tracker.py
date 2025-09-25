"""
Tab tracking adapter implementation.

This module provides the default implementation of the TabTrackerInterface.
"""

import logging
import time
import threading
from typing import List, Dict, Callable, Optional

from focus_guard.core.browser.interfaces import TabTrackerInterface
from focus_guard.core.browser.models.tab import Tab, TabEvent

logger = logging.getLogger(__name__)

class DefaultTabTracker(TabTrackerInterface):
    """Default implementation of the TabTrackerInterface.
    
    This implementation tracks browser tabs and their events.
    """
    
    def __init__(self, cache_ttl: float = 1.0):
        """Initialize the tab tracker.
        
        Args:
            cache_ttl: Time in seconds to cache tab data
        """
        self._tabs = {}
        self._event_handlers = {event_type: [] for event_type in TabEvent}
        self._last_update_time = 0
        self._cache_ttl = cache_ttl
        self._running = False
        self._thread = None
    
    def start(self) -> bool:
        """Start tracking tabs."""
        if self._running:
            return True
            
        self._running = True
        self._thread = threading.Thread(target=self._poll_tabs, daemon=True)
        self._thread.start()
        return True
    
    def stop(self) -> None:
        """Stop tracking tabs."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None  # Clear the thread reference after stopping
    
    def get_all_tabs(self) -> List[Tab]:
        """Get all open tabs across all browsers."""
        self._update_tab_data()
        return list(self._tabs.values())
    
    def get_active_tab(self) -> Optional[Tab]:
        """Get the currently active tab."""
        self._update_tab_data()
        for tab in self._tabs.values():
            if tab.is_active:
                return tab
        return None
    
    def register_tab_event_handler(self, event_type: TabEvent, handler: Callable[[Tab], None]) -> None:
        """Register a handler for tab events."""
        if event_type not in self._event_handlers:
            raise ValueError(f"Invalid event type: {event_type}")
        self._event_handlers[event_type].append(handler)
    
    def get_tabs_by_domain(self, domain: str) -> List[Tab]:
        """Get all tabs for a specific domain."""
        self._update_tab_data()
        return [tab for tab in self._tabs.values() if tab.domain == domain]
    
    def _update_tab_data(self) -> None:
        """Update tab data if cache is expired."""
        current_time = time.time()
        if current_time - self._last_update_time < self._cache_ttl:
            return
            
        # In a real implementation, this would query the browser for tab information
        # For now, we'll just update the last update time
        self._last_update_time = current_time
    
    def _poll_tabs(self) -> None:
        """Background thread for polling tab changes."""
        while self._running:
            try:
                self._update_tab_data()
                time.sleep(self._cache_ttl)
            except Exception as e:
                logger.error(f"Error in tab polling thread: {e}")
                time.sleep(1)  # Prevent tight loop on error
    
    def _notify_event_handlers(self, event_type: TabEvent, tab: Tab) -> None:
        """Notify all registered event handlers."""
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(tab)
            except Exception as e:
                logger.error(f"Error in tab event handler: {e}")
