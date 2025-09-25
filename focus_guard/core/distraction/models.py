"""
Core models for the distraction detection module.

This module defines the data models used by the distraction detector,
including distraction alerts, states, and alert levels.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

# Import shared types
from focus_guard.core.distraction.types import AlertLevel, DistractionAlert, DistractionEvent


@dataclass
class FocusSession:
    """
    Represents a focus session.
    
    Attributes:
        id: The unique identifier for the session.
        start_time: The time the session started.
        end_time: The time the session ended, or None if still active.
        duration_seconds: The duration of the session in seconds.
        interruptions: The number of interruptions during the session.
        metadata: Additional metadata about the session.
    """
    id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: int = 0
    interruptions: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DistractionState:
    """
    Represents the current distraction state.
    
    Attributes:
        active_window: Information about the active window.
        top_windows: List of top windows.
        browser_tabs: Information about browser tabs.
        last_update: The time of the last update.
        distraction_history: History of distraction alerts.
    """
    active_window: Optional[Dict[str, Any]] = None
    top_windows: List[Dict[str, Any]] = field(default_factory=list)
    browser_tabs: Dict[str, Any] = field(default_factory=dict)
    last_update: Optional[datetime] = None
    distraction_history: List[DistractionAlert] = field(default_factory=list)
    
    def update(self, active_window: Dict[str, Any], top_windows: List[Dict[str, Any]]) -> None:
        """
        Update the state with new window information.
        
        Args:
            active_window: Information about the active window.
            top_windows: List of top windows.
        """
        self.active_window = active_window
        self.top_windows = top_windows
        self.last_update = datetime.now()
    
    def update_browser_tabs(self, browser_tabs: Dict[str, Any]) -> None:
        """
        Update the state with new browser tab information.
        
        Args:
            browser_tabs: Information about browser tabs.
        """
        self.browser_tabs = browser_tabs
        self.last_update = datetime.now()
    
    def add_distraction_alert(self, alert: DistractionAlert) -> None:
        """
        Add a distraction alert to the history.
        
        Args:
            alert: The distraction alert to add.
        """
        self.distraction_history.append(alert)
    
    @property
    def is_distracted(self) -> bool:
        """
        Check if the user is currently distracted based on recent alerts.
        
        Returns:
            True if there are recent distraction alerts, False otherwise.
        """
        if not self.distraction_history:
            return False
        
        # Get the most recent alert
        last_alert = self.distraction_history[-1]
        
        # Check if the alert is recent enough (within the last minute)
        now = datetime.now()
        alert_age = (now - last_alert.timestamp).total_seconds()
        
        return alert_age < 60  # Consider distracted if alert is less than 60 seconds old
