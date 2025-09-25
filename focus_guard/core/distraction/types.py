"""
Type definitions for the distraction detection system.

This module contains shared type definitions used across the distraction detection system.
It is designed to have minimal dependencies to avoid circular imports.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

# Forward declarations for type hints
if TYPE_CHECKING:
    from focus_guard.core.coordinator.events import EventData


class AlertLevel(Enum):
    """
    Enumeration of distraction alert levels.
    
    Levels indicate the severity of a distraction:
    - INFO: Informational alerts, low severity
    - WARNING: Warning alerts, medium severity
    - CRITICAL: Critical alerts, high severity
    """
    INFO = 0
    WARNING = 1
    CRITICAL = 2
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented
        
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented
        
    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented
        
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented


@dataclass
class DistractionAlert:
    """
    Represents a distraction alert.
    
    Attributes:
        rule_name: The name of the rule that generated the alert.
        level: The alert level.
        message: The alert message.
        metadata: Additional metadata about the alert.
        timestamp: The time the alert was generated.
    """
    rule_name: str
    level: AlertLevel
    message: str
    metadata: Dict[str, Any]
    timestamp: datetime


class DistractionEvent:
    """
    Event data for distraction events.
    
    Attributes:
        source: The source of the event.
        alert: The distraction alert that triggered the event.
        state: The current distraction state.
    """
    def __init__(self, source: str, alert: DistractionAlert, state=None):
        self.source = source
        self.alert = alert
        self.state = state
        
        # Initialize EventData functionality
        try:
            from focus_guard.core.coordinator.events import EventData
            self._event_data = EventData(source)
        except ImportError:
            self._event_data = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        if self._event_data:
            data = self._event_data.to_dict()
        else:
            data = {"source": self.source}
            
        data["alert"] = {
            "rule_name": self.alert.rule_name,
            "level": self.alert.level.name,
            "message": self.alert.message,
            "timestamp": self.alert.timestamp.isoformat()
        }
        
        if self.state:
            data["state"] = {
                "is_distracted": getattr(self.state, 'is_distracted', False)
            }
        return data
