"""
Browser activity tracker implementation.

This module provides an implementation of the browser activity tracker
interface for monitoring browser tabs and their content.
"""

from typing import Dict, Any, List, Optional, Callable
import logging
from datetime import datetime

from core_v2.distraction.interfaces import BrowserActivityTracker
from core_v2.distraction.models import DistractionState
from core_v2.browser.interfaces import BrowserIntegrationInterface
from core_v2.classification.base import ContextAwareClassifier
from core_v2.domain.models import Domain


class StandardBrowserTracker(BrowserActivityTracker):
    """
    Standard implementation of the browser activity tracker.
    
    This tracker monitors browser tabs and their content using
    the browser integration module and domain classifier.
    """
    
    def __init__(
        self,
        browser_integration: BrowserIntegrationInterface,
        domain_classifier: ContextAwareClassifier,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the browser activity tracker.
        
        Args:
            browser_integration: The browser integration to use.
            domain_classifier: The domain classifier to use.
            logger: Optional logger for logging.
        """
        self._browser_integration = browser_integration
        self._domain_classifier = domain_classifier
        self._logger = logger or logging.getLogger(__name__)
        self._state_update_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # Register for browser tab events
        self._browser_integration.register_tab_event_callback(self._on_tab_event)
    
    @property
    def name(self) -> str:
        """Get the name of the tracker."""
        return "Standard Browser Tracker"
        
    @property
    def active_tab(self) -> Optional[Dict[str, Any]]:
        """Get information about the active tab."""
        try:
            tabs = self._browser_integration.get_active_tabs()
            active_tab = tabs.get("active_tab")
            if active_tab:
                return self._classify_tab(active_tab)
            return None
        except Exception as e:
            self._logger.error(f"Error getting active tab: {e}")
            return None
            
    def update(self, browser_data: Dict[str, Any]) -> None:
        """Update the tracker with new browser data."""
        try:
            # Classify tabs
            classified_tabs = self._classify_tabs(browser_data)
            
            # Notify callbacks
            for callback in self._state_update_callbacks:
                try:
                    callback(classified_tabs)
                except Exception as e:
                    self._logger.error(f"Error in state update callback: {e}")
        except Exception as e:
            self._logger.error(f"Error updating browser tracker: {e}")
            
    def is_tab_productive(self, tab_id: str) -> bool:
        """Check if a tab is productive."""
        try:
            tabs = self._browser_integration.get_active_tabs()
            all_tabs = tabs.get("all_tabs", [])
            
            for tab in all_tabs:
                if tab.get("id") == tab_id:
                    classified_tab = self._classify_tab(tab)
                    classification = classified_tab.get("classification", {})
                    return classification.get("is_productive", False)
                    
            return False
        except Exception as e:
            self._logger.error(f"Error checking if tab is productive: {e}")
            return False
    
    def register_state_update_callback(
        self,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register a callback for state updates.
        
        Args:
            callback: The callback function to call when the state is updated.
        """
        self._state_update_callbacks.append(callback)
    
    def update_state(self, state: DistractionState) -> None:
        """
        Update the state with browser activity information.
        
        Args:
            state: The distraction state to update.
        """
        try:
            # Get current browser tabs
            tabs = self._browser_integration.get_active_tabs()
            
            # Classify tabs
            classified_tabs = self._classify_tabs(tabs)
            
            # Update state
            state.update_browser_tabs({
                "active_tab": classified_tabs.get("active_tab"),
                "all_tabs": classified_tabs.get("all_tabs", []),
                "last_update": datetime.now()
            })
            
            # Notify callbacks
            for callback in self._state_update_callbacks:
                try:
                    callback(classified_tabs)
                except Exception as e:
                    self._logger.error(f"Error in state update callback: {e}")
        except Exception as e:
            self._logger.error(f"Error updating browser state: {e}")
    
    def _classify_tabs(self, tabs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify browser tabs using the domain classifier.
        
        Args:
            tabs: Browser tabs information.
            
        Returns:
            Classified browser tabs information.
        """
        result = {
            "active_tab": None,
            "all_tabs": []
        }
        
        # Process active tab
        active_tab = tabs.get("active_tab")
        if active_tab:
            result["active_tab"] = self._classify_tab(active_tab)
        
        # Process all tabs
        all_tabs = tabs.get("all_tabs", [])
        result["all_tabs"] = [self._classify_tab(tab) for tab in all_tabs]
        
        return result
    
    def _classify_tab(self, tab: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a browser tab using the domain classifier.
        
        Args:
            tab: Browser tab information.
            
        Returns:
            Classified browser tab information.
        """
        result = tab.copy()
        
        # Extract domain from URL
        url = tab.get("url")
        if url:
            try:
                # Import here to avoid circular imports
                from core_v2.domain.utils import extract_domain_from_url
                domain_str = extract_domain_from_url(url)
                
                if domain_str:
                    # Classify domain
                    domain = Domain(domain_str)
                    classification = self._domain_classifier.classify(domain)
                    
                    # Add classification to result
                    result["domain"] = domain_str
                    result["category"] = classification.category.name if classification.category else None
                    result["classification"] = {
                        "category": classification.category.name if classification.category else None,
                        "confidence": classification.confidence,
                        "is_productive": classification.is_productive()
                    }
            except Exception as e:
                self._logger.error(f"Error classifying tab: {e}")
        
        return result
    
    def _on_tab_event(self, event: Dict[str, Any]) -> None:
        """
        Handle browser tab events.
        
        Args:
            event: The tab event.
        """
        event_type = event.get("type")
        
        if event_type == "tab_created":
            self._logger.debug(f"Tab created: {event.get('tab', {}).get('url')}")
        elif event_type == "tab_updated":
            self._logger.debug(f"Tab updated: {event.get('tab', {}).get('url')}")
        elif event_type == "tab_removed":
            self._logger.debug(f"Tab removed: {event.get('tab_id')}")
        elif event_type == "tab_activated":
            self._logger.debug(f"Tab activated: {event.get('tab', {}).get('url')}")
            
        # Notify callbacks about the event
        for callback in self._state_update_callbacks:
            try:
                callback(event)
            except Exception as e:
                self._logger.error(f"Error in state update callback: {e}")
