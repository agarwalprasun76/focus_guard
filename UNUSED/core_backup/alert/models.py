"""
Core data models for the alert system.

This module defines the data models used by the alert system, including
alert levels, alert information, and alert history entries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto, IntEnum
from typing import Dict, Any, List, Optional, Union


class AlertLevel(Enum):
    """
    Alert level enum.
    
    Defines the severity levels for alerts, which determine how they are
    displayed and how aggressively they interrupt the user.
    """
    
    NORMAL = auto()    # Standard alert, minimal interruption
    WARNING = auto()   # Warning alert, moderate interruption
    CRITICAL = auto()  # Critical alert, significant interruption
    
    @classmethod
    def from_string(cls, level_str: str) -> "AlertLevel":
        """
        Convert a string to an AlertLevel.
        
        Args:
            level_str: String representation of the alert level
            
        Returns:
            The corresponding AlertLevel enum value
            
        Raises:
            ValueError: If the string doesn't match any alert level
        """
        level_map = {
            "normal": cls.NORMAL,
            "warning": cls.WARNING,
            "critical": cls.CRITICAL
        }
        
        if level_str.lower() in level_map:
            return level_map[level_str.lower()]
        
        raise ValueError(f"Invalid alert level: {level_str}")
    
    def to_string(self) -> str:
        """
        Convert the AlertLevel to a string.
        
        Returns:
            String representation of the alert level
        """
        return self.name.lower()


@dataclass
class AlertInfo:
    """
    Information about an alert.
    
    Contains metadata about an alert, including its source, level,
    and any additional context.
    """
    
    # Required fields
    app_name: str                      # Name of the application causing the distraction
    message: str                       # Alert message to display
    level: AlertLevel = AlertLevel.NORMAL  # Alert severity level
    
    # Optional fields
    window_title: Optional[str] = None  # Title of the window causing the distraction
    window_url: Optional[str] = None    # URL of the browser window (for browser alerts)
    window_rect: Optional[Dict[str, int]] = None  # Position and size of the window
    pid: Optional[int] = None           # Process ID of the application
    timestamp: datetime = field(default_factory=datetime.now)  # When the alert was created
    
    # Additional context
    context: Dict[str, Any] = field(default_factory=dict)  # Any additional context for the alert
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the AlertInfo to a dictionary.
        
        Returns:
            Dictionary representation of the alert info
        """
        return {
            "app_name": self.app_name,
            "message": self.message,
            "level": self.level.to_string(),
            "window_title": self.window_title,
            "window_url": self.window_url,
            "window_rect": self.window_rect,
            "pid": self.pid,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertInfo":
        """
        Create an AlertInfo from a dictionary.
        
        Args:
            data: Dictionary representation of the alert info
            
        Returns:
            AlertInfo instance
        """
        # Handle timestamp conversion
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data = data.copy()  # Don't modify the original
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
            
        # Handle level conversion
        if "level" in data and isinstance(data["level"], str):
            data = data.copy()  # Don't modify the original
            data["level"] = AlertLevel.from_string(data["level"])
            
        return cls(**data)


@dataclass
class AlertHistoryEntry:
    """
    Entry in the alert history.
    
    Records an alert that was sent, along with metadata about when
    it was sent and how the user responded.
    """
    
    alert_info: AlertInfo                # Information about the alert
    timestamp: datetime = field(default_factory=datetime.now)  # When the alert was sent
    providers_used: List[str] = field(default_factory=list)  # Which providers sent the alert
    acknowledged: bool = False           # Whether the user acknowledged the alert
    acknowledged_time: Optional[datetime] = None  # When the user acknowledged the alert
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the AlertHistoryEntry to a dictionary.
        
        Returns:
            Dictionary representation of the history entry
        """
        return {
            "alert_info": self.alert_info.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "providers_used": self.providers_used,
            "acknowledged": self.acknowledged,
            "acknowledged_time": self.acknowledged_time.isoformat() if self.acknowledged_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertHistoryEntry":
        """
        Create an AlertHistoryEntry from a dictionary.
        
        Args:
            data: Dictionary representation of the history entry
            
        Returns:
            AlertHistoryEntry instance
        """
        # Handle nested AlertInfo
        if "alert_info" in data and isinstance(data["alert_info"], dict):
            data = data.copy()  # Don't modify the original
            data["alert_info"] = AlertInfo.from_dict(data["alert_info"])
            
        # Handle timestamp conversion
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data = data.copy()  # Don't modify the original
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
            
        # Handle acknowledged_time conversion
        if "acknowledged_time" in data and isinstance(data["acknowledged_time"], str):
            data = data.copy()  # Don't modify the original
            data["acknowledged_time"] = datetime.fromisoformat(data["acknowledged_time"])
            
        return cls(**data)


class AlertType(IntEnum):
    """
    Types of alerts that can be sent by the system.
    
    These types determine the nature and purpose of the alert.
    """
    DISTRACTION = 1     # Alert for a distraction event
    NOTIFICATION = 2    # General notification
    WARNING = 3         # Warning about potential issues
    ERROR = 4           # Error notification
    SYSTEM = 5          # System-level alert
    
    @classmethod
    def from_string(cls, type_str: str) -> "AlertType":
        """
        Convert a string to an AlertType.
        
        Args:
            type_str: String representation of the alert type
            
        Returns:
            The corresponding AlertType enum value
            
        Raises:
            ValueError: If the string doesn't match any alert type
        """
        type_map = {
            "distraction": cls.DISTRACTION,
            "notification": cls.NOTIFICATION,
            "warning": cls.WARNING,
            "error": cls.ERROR,
            "system": cls.SYSTEM
        }
        
        if type_str.lower() in type_map:
            return type_map[type_str.lower()]
        
        raise ValueError(f"Invalid alert type: {type_str}")
    
    def to_string(self) -> str:
        """
        Convert the AlertType to a string.
        
        Returns:
            String representation of the alert type
        """
        return self.name.lower()


class AlertPriority(IntEnum):
    """
    Priority levels for alerts.
    
    These priorities determine the urgency and visibility of alerts.
    """
    LOW = 1         # Low priority alert
    MEDIUM = 2      # Medium priority alert
    HIGH = 3        # High priority alert
    CRITICAL = 4    # Critical priority alert
    
    @classmethod
    def from_string(cls, priority_str: str) -> "AlertPriority":
        """
        Convert a string to an AlertPriority.
        
        Args:
            priority_str: String representation of the alert priority
            
        Returns:
            The corresponding AlertPriority enum value
            
        Raises:
            ValueError: If the string doesn't match any alert priority
        """
        priority_map = {
            "low": cls.LOW,
            "medium": cls.MEDIUM,
            "high": cls.HIGH,
            "critical": cls.CRITICAL
        }
        
        if priority_str.lower() in priority_map:
            return priority_map[priority_str.lower()]
        
        raise ValueError(f"Invalid alert priority: {priority_str}")
    
    def to_string(self) -> str:
        """
        Convert the AlertPriority to a string.
        
        Returns:
            String representation of the alert priority
        """
        return self.name.lower()


class AlertAction(IntEnum):
    """
    Actions that can be taken in response to an alert.
    
    These actions determine how the system should respond to the alert.
    """
    NONE = 0            # No action required
    ACKNOWLEDGE = 1     # User acknowledges the alert
    DISMISS = 2         # User dismisses the alert
    SNOOZE = 3          # User snoozes the alert
    BLOCK = 4           # Block the source of the alert
    ALLOW = 5           # Allow the source of the alert
    CUSTOM = 6          # Custom action defined by the alert provider
    
    @classmethod
    def from_string(cls, action_str: str) -> "AlertAction":
        """
        Convert a string to an AlertAction.
        
        Args:
            action_str: String representation of the alert action
            
        Returns:
            The corresponding AlertAction enum value
            
        Raises:
            ValueError: If the string doesn't match any alert action
        """
        action_map = {
            "none": cls.NONE,
            "acknowledge": cls.ACKNOWLEDGE,
            "dismiss": cls.DISMISS,
            "snooze": cls.SNOOZE,
            "block": cls.BLOCK,
            "allow": cls.ALLOW,
            "custom": cls.CUSTOM
        }
        
        if action_str.lower() in action_map:
            return action_map[action_str.lower()]
        
        raise ValueError(f"Invalid alert action: {action_str}")
    
    def to_string(self) -> str:
        """
        Convert the AlertAction to a string.
        
        Returns:
            String representation of the alert action
        """
        return self.name.lower()


@dataclass
class Alert:
    """
    Alert model for the coordinator components.
    
    This is a higher-level alert model used by the coordinator components,
    which wraps the AlertInfo model with additional metadata.
    
    Attributes:
        id: Unique identifier for the alert
        type: Type of alert
        source: Source component that generated the alert
        message: Alert message
        level: Alert severity level
        timestamp: When the alert was created
        actions: Available actions for this alert
        metadata: Additional context for the alert
    """
    id: str
    type: AlertType
    source: str
    message: str
    level: AlertLevel = AlertLevel.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    actions: List[AlertAction] = field(default_factory=lambda: [AlertAction.ACKNOWLEDGE])
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Alert to a dictionary.
        
        Returns:
            Dictionary representation of the alert
        """
        return {
            "id": self.id,
            "type": self.type.to_string(),
            "source": self.source,
            "message": self.message,
            "level": self.level.to_string(),
            "timestamp": self.timestamp.isoformat(),
            "actions": [action.to_string() for action in self.actions],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """
        Create an Alert from a dictionary.
        
        Args:
            data: Dictionary representation of the alert
            
        Returns:
            Alert instance
        """
        # Make a copy to avoid modifying the original
        data_copy = data.copy()
        
        # Handle timestamp conversion
        if "timestamp" in data_copy and isinstance(data_copy["timestamp"], str):
            data_copy["timestamp"] = datetime.fromisoformat(data_copy["timestamp"])
            
        # Handle type conversion
        if "type" in data_copy and isinstance(data_copy["type"], str):
            data_copy["type"] = AlertType.from_string(data_copy["type"])
            
        # Handle level conversion
        if "level" in data_copy and isinstance(data_copy["level"], str):
            data_copy["level"] = AlertLevel.from_string(data_copy["level"])
            
        # Handle actions conversion
        if "actions" in data_copy and isinstance(data_copy["actions"], list):
            data_copy["actions"] = [
                AlertAction.from_string(action) if isinstance(action, str) else action
                for action in data_copy["actions"]
            ]
            
        return cls(**data_copy)
    
    @classmethod
    def from_alert_info(cls, alert_id: str, alert_type: AlertType, source: str, 
                       alert_info: AlertInfo) -> "Alert":
        """
        Create an Alert from an AlertInfo object.
        
        Args:
            alert_id: Unique identifier for the alert
            alert_type: Type of alert
            source: Source component that generated the alert
            alert_info: AlertInfo instance
            
        Returns:
            Alert instance
        """
        return cls(
            id=alert_id,
            type=alert_type,
            source=source,
            message=alert_info.message,
            level=alert_info.level,
            timestamp=alert_info.timestamp,
            metadata={
                "app_name": alert_info.app_name,
                "window_title": alert_info.window_title,
                "window_url": alert_info.window_url,
                "window_rect": alert_info.window_rect,
                "pid": alert_info.pid,
                **alert_info.context
            }
        )
