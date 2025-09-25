"""
Blocking-related events.

This module defines the event types and data structures used for communication
between the activity monitoring and blocking modules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Union

from focus_guard.core.domain.models import Domain


class EventType(str, Enum):
    """Types of blocking-related events."""
    # Resource access events
    RESOURCE_ACCESS_ATTEMPT = "resource_access_attempt"
    RESOURCE_ACCESS_BLOCKED = "resource_access_blocked"
    RESOURCE_ACCESS_ALLOWED = "resource_access_allowed"
    
    # Policy events
    POLICY_ADDED = "policy_added"
    POLICY_REMOVED = "policy_removed"
    POLICY_UPDATED = "policy_updated"
    
    # User interaction events
    OVERRIDE_REQUESTED = "override_requested"
    OVERRIDE_GRANTED = "override_granted"
    OVERRIDE_DENIED = "override_denied"
    
    # System events
    BLOCKING_ENABLED = "blocking_enabled"
    BLOCKING_DISABLED = "blocking_disabled"
    
    # Browser-specific events
    TAB_NAVIGATION = "tab_navigation"
    TAB_CLOSED = "tab_closed"
    
    # Application-specific events
    APPLICATION_LAUNCH = "application_launch"
    APPLICATION_TERMINATED = "application_terminated"


@dataclass
class BlockingEvent:
    """Base class for all blocking-related events."""
    event_type: EventType
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    source: str = "blocking_system"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlockingEvent':
        """Create an event from a dictionary."""
        return cls(
            event_type=EventType(data["event_type"]),
            timestamp=data["timestamp"],
            source=data.get("source", "blocking_system"),
            metadata=data.get("metadata", {})
        )


@dataclass(init=False)
class ResourceAccessEvent(BlockingEvent):
    """Event for resource access attempts and decisions."""
    # Required fields (no default values)
    resource_type: str  # 'domain', 'application', 'url', etc.
    resource_id: str    # The actual domain, app name, URL, etc.
    action: str         # 'block', 'allow', 'warn', etc.
    
    # Optional fields (with default values)
    reason: str         # Human-readable reason for the action
    
    def __init__(self, resource_type: str, resource_id: str, action: str, 
                 reason: str = "", source: str = "blocking_system",
                 metadata: Optional[Dict[str, Any]] = None):
        """Initialize the event with the given parameters."""
        # Initialize required fields
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.action = action
        self.reason = reason
        
        # Initialize the base class
        super().__init__(
            event_type=EventType.RESOURCE_ACCESS_ATTEMPT,  # Will be updated in __post_init__
            source=source,
            metadata=metadata or {}
        )
        
        # Set the correct event type based on action
        if self.action == "block":
            self.event_type = EventType.RESOURCE_ACCESS_BLOCKED
        elif self.action == "allow":
            self.event_type = EventType.RESOURCE_ACCESS_ALLOWED
        else:
            self.event_type = EventType.RESOURCE_ACCESS_ATTEMPT
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary."""
        data = super().to_dict()
        data.update({
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "reason": self.reason
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceAccessEvent':
        """Create an event from a dictionary."""
        # First create the base BlockingEvent
        base_event = BlockingEvent.from_dict(data)
        
        # Then create the ResourceAccessEvent with the base event's attributes
        event = cls(
            resource_type=data["resource_type"],
            resource_id=data["resource_id"],
            action=data["action"],
            reason=data.get("reason", "")
        )
        
        # Copy the base event attributes
        event.event_type = base_event.event_type
        event.timestamp = base_event.timestamp
        event.source = base_event.source
        event.metadata = base_event.metadata
        
        return event


@dataclass(init=False)
class PolicyEvent(BlockingEvent):
    """Event for policy changes."""
    policy_name: str
    policy_type: str
    
    def __init__(self, policy_name: str, policy_type: str, 
                 event_type: EventType, source: str = "blocking_system",
                 metadata: Optional[Dict[str, Any]] = None):
        """Initialize the policy event."""
        self.policy_name = policy_name
        self.policy_type = policy_type
        super().__init__(
            event_type=event_type,
            source=source,
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary."""
        data = super().to_dict()
        data.update({
            "policy_name": self.policy_name,
            "policy_type": self.policy_type
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PolicyEvent':
        """Create an event from a dictionary."""
        return cls(
            policy_name=data["policy_name"],
            policy_type=data["policy_type"],
            event_type=EventType(data["event_type"]),
            source=data.get("source", "blocking_system"),
            metadata=data.get("metadata", {})
        )


@dataclass(init=False)
class OverrideEvent(BlockingEvent):
    """Event for override requests and decisions."""
    resource_type: str
    resource_id: str
    duration_seconds: Optional[int]
    reason: str
    
    def __init__(self, resource_type: str, resource_id: str, 
                 duration_seconds: Optional[int] = None, reason: str = "",
                 event_type: Optional[EventType] = None, 
                 source: str = "blocking_system",
                 metadata: Optional[Dict[str, Any]] = None):
        """Initialize the override event."""
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.duration_seconds = duration_seconds
        self.reason = reason
        
        # Set default event type if not provided
        if event_type is None:
            event_type = EventType.OVERRIDE_REQUESTED
            
        super().__init__(
            event_type=event_type,
            source=source,
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary."""
        data = super().to_dict()
        data.update({
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "duration_seconds": self.duration_seconds,
            "reason": self.reason
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OverrideEvent':
        """Create an event from a dictionary."""
        return cls(
            resource_type=data["resource_type"],
            resource_id=data["resource_id"],
            duration_seconds=data.get("duration_seconds"),
            reason=data.get("reason", ""),
            event_type=EventType(data["event_type"]),
            source=data.get("source", "blocking_system"),
            metadata=data.get("metadata", {})
        )


def create_event(data: Dict[str, Any]) -> BlockingEvent:
    """
    Create an event from a dictionary based on its type.
    
    Args:
        data: The dictionary containing the event data.
        
    Returns:
        BlockingEvent: The created event object.
        
    Raises:
        ValueError: If the event type is unknown or invalid.
    """
    event_type = EventType(data["event_type"])
    
    if event_type in {
        EventType.RESOURCE_ACCESS_ATTEMPT,
        EventType.RESOURCE_ACCESS_BLOCKED,
        EventType.RESOURCE_ACCESS_ALLOWED
    }:
        return ResourceAccessEvent.from_dict(data)
    
    elif event_type in {
        EventType.POLICY_ADDED,
        EventType.POLICY_REMOVED,
        EventType.POLICY_UPDATED
    }:
        return PolicyEvent.from_dict(data)
    
    elif event_type in {
        EventType.OVERRIDE_REQUESTED,
        EventType.OVERRIDE_GRANTED,
        EventType.OVERRIDE_DENIED
    }:
        return OverrideEvent.from_dict(data)
    
    # Default to base BlockingEvent for other types
    return BlockingEvent.from_dict(data)
