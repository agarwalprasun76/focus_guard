"""
Core interfaces for the distraction detection module.

This module defines the interfaces for distraction rules, alert handlers,
and the distraction detector itself.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

# Import shared types
from focus_guard.core.distraction.types import AlertLevel, DistractionAlert

# Use string type hints to avoid circular imports
if TYPE_CHECKING:
    from focus_guard.core.distraction.models import DistractionState


class DistractionRule(ABC):
    """
    Interface for distraction detection rules.
    
    Rules are responsible for detecting specific types of distractions
    based on the current state and activity.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the rule."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the description of the rule."""
        pass
    
    @abstractmethod
    def should_apply(self, state: 'DistractionState') -> bool:
        """
        Determine if the rule should be applied to the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            True if the rule should be applied, False otherwise.
        """
        pass
    
    @abstractmethod
    def check(self, state: 'DistractionState') -> List['DistractionAlert']:
        """
        Check for distractions based on the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            A list of distraction alerts, or an empty list if no distractions are detected.
        """
        pass


class AlertHandler(ABC):
    """
    Interface for handling distraction alerts.
    
    Alert handlers are responsible for responding to distraction alerts,
    such as displaying notifications, blocking content, or logging.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the handler."""
        pass
    
    @abstractmethod
    def handle(self, alert: 'DistractionAlert') -> None:
        """
        Handle a distraction alert.
        
        Args:
            alert: The distraction alert to handle.
        """
        pass
    
    @abstractmethod
    def can_handle(self, alert: 'DistractionAlert') -> bool:
        """
        Determine if the handler can handle the given alert.
        
        Args:
            alert: The distraction alert to check.
            
        Returns:
            True if the handler can handle the alert, False otherwise.
        """
        pass


class DistractionDetector(ABC):
    """
    Interface for distraction detection.
    
    The distraction detector is responsible for coordinating rule evaluation
    and alert handling based on the current state and activity.
    """
    
    @abstractmethod
    def add_rule(self, rule: DistractionRule) -> None:
        """
        Add a distraction rule.
        
        Args:
            rule: The rule to add.
        """
        pass
    
    @abstractmethod
    def add_alert_handler(self, handler: AlertHandler) -> None:
        """
        Add an alert handler.
        
        Args:
            handler: The handler to add.
        """
        pass
    
    @abstractmethod
    def update(self, active_window: Dict[str, Any], top_windows: List[Dict[str, Any]]) -> None:
        """
        Update the distraction detector with the current window state.
        
        Args:
            active_window: Information about the active window.
            top_windows: List of top windows.
        """
        pass
    
    @property
    @abstractmethod
    def is_distracted(self) -> bool:
        """
        Check if the user is currently distracted.
        
        Returns:
            True if the user is distracted, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_distraction_state(self) -> 'DistractionState':
        """
        Get the current distraction state.
        
        Returns:
            The current distraction state.
        """
        pass


class BrowserActivityTracker(ABC):
    """
    Interface for tracking browser activity.
    
    Browser activity trackers are responsible for monitoring browser tabs
    and providing information about the active tab and its productivity status.
    """
    
    @abstractmethod
    def update(self, browser_data: Dict[str, Any]) -> None:
        """
        Update the tracker with new browser data.
        
        Args:
            browser_data: Information about browser tabs and windows.
        """
        pass
    
    @property
    @abstractmethod
    def active_tab(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the active tab.
        
        Returns:
            A dictionary with information about the active tab, or None if no active tab.
        """
        pass
    
    @abstractmethod
    def is_tab_productive(self, tab_id: str) -> bool:
        """
        Check if a tab is productive.
        
        Args:
            tab_id: The ID of the tab to check.
            
        Returns:
            True if the tab is productive, False otherwise.
        """
        pass
