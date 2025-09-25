"""
Event system for the Focus Guard coordinator.

This module provides an implementation of the EventBus interface for
inter-component communication using an event-driven architecture.
"""

import logging
import asyncio
from typing import Dict, List, Any, Set
import weakref

from core_v2.coordinator.interfaces import EventBus, EventListener


class DefaultEventBus(EventBus):
    """
    Default implementation of the EventBus interface.
    
    This class provides a simple publish-subscribe mechanism for
    inter-component communication. Components can subscribe to event
    types and be notified when those events occur.
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self.subscribers: Dict[str, Set[weakref.ReferenceType]] = {}
        self.logger = logging.getLogger("focus_guard.coordinator.events")
    
    async def publish(self, event_type: str, event_data: Any) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type (str): The type of event.
            event_data (Any): The event data.
        """
        if event_type not in self.subscribers:
            self.logger.debug(f"No subscribers for event type: {event_type}")
            return
        
        # Create a copy of the subscribers to avoid modification during iteration
        subscribers = list(self.subscribers[event_type])
        
        # Clean up dead references
        self.subscribers[event_type] = {ref for ref in self.subscribers[event_type] if ref() is not None}
        
        self.logger.debug(f"Publishing event {event_type} to {len(subscribers)} subscribers")
        
        # Notify all subscribers
        tasks = []
        for ref in subscribers:
            listener = ref()
            if listener is not None:
                try:
                    # Handle both function callbacks and component listeners
                    if hasattr(listener, 'on_event') and callable(listener.on_event):
                        task = asyncio.create_task(listener.on_event(event_type, event_data))
                    elif callable(listener):
                        # Direct function callback
                        task = asyncio.create_task(listener(event_type, event_data))
                    else:
                        self.logger.error(f"Invalid listener type: {type(listener)}")
                        continue
                    tasks.append(task)
                except Exception as e:
                    self.logger.exception(f"Error notifying listener for event {event_type}: {e}")
        
        # Wait for all notifications to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def subscribe(self, event_type: str, listener: EventListener) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type (str): The type of event to subscribe to.
            listener (EventListener): The listener to notify when the event occurs.
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = set()
        
        # Use weak references to avoid memory leaks
        self.subscribers[event_type].add(weakref.ref(listener))
        self.logger.debug(f"Subscribed to event type: {event_type}")
    
    def unsubscribe(self, event_type: str, listener: EventListener) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type (str): The type of event to unsubscribe from.
            listener (EventListener): The listener to remove.
        """
        if event_type not in self.subscribers:
            return
        
        # Find and remove the listener
        to_remove = None
        for ref in self.subscribers[event_type]:
            if ref() is listener:
                to_remove = ref
                break
        
        if to_remove is not None:
            self.subscribers[event_type].remove(to_remove)
            self.logger.debug(f"Unsubscribed from event type: {event_type}")
        
        # Clean up empty sets
        if not self.subscribers[event_type]:
            del self.subscribers[event_type]


class EventTypes:
    """
    Constants for common event types used in the Focus Guard application.
    
    This class defines the standard event types that components can
    publish and subscribe to.
    """
    
    # Component lifecycle events
    COMPONENT_INITIALIZED = "component.initialized"
    COMPONENT_STARTED = "component.started"
    COMPONENT_STOPPED = "component.stopped"
    COMPONENT_SHUTDOWN = "component.shutdown"
    COMPONENT_ERROR = "component.error"
    
    # Configuration events
    CONFIG_CHANGED = "config.changed"
    CONFIG_RELOADED = "config.reloaded"
    
    # Activity events
    ACTIVITY_CHANGED = "activity.changed"
    IDLE_DETECTED = "activity.idle_detected"
    IDLE_ENDED = "activity.idle_ended"
    IDLE_STATE_CHANGED = "activity.idle_state_changed"
    
    # Browser events
    TAB_OPENED = "browser.tab_opened"
    TAB_CLOSED = "browser.tab_closed"
    TAB_UPDATED = "browser.tab_updated"
    TAB_ACTIVATED = "browser.tab_activated"
    
    # Classification events
    DOMAIN_CLASSIFIED = "classification.domain_classified"
    
    # Distraction events
    DISTRACTION_DETECTED = "distraction.detected"
    DISTRACTION_RESOLVED = "distraction.resolved"
    FOCUS_MODE_CHANGED = "distraction.focus_mode_changed"
    
    # Activity events
    WINDOW_CHANGED = "activity.window_changed"
    IDLE_STATE_CHANGED = "activity.idle_state_changed"
    
    # Alert events
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_DISMISSED = "alert.dismissed"
    
    # Health events
    HEALTH_CHECK_FAILED = "health.check_failed"
    HEALTH_CHECK_RECOVERED = "health.check_recovered"


class EventData:
    """
    Base class for event data objects.
    
    This class provides a common base for all event data objects,
    ensuring they have a consistent interface.
    """
    
    def __init__(self, source: str):
        """
        Initialize the event data.
        
        Args:
            source (str): The source of the event (typically a component name).
        """
        self.source = source
        try:
            # Try to get the current event loop's time
            self.timestamp = asyncio.get_event_loop().time()
        except RuntimeError:
            # Fallback for testing environments where no event loop exists
            import time
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        return {
            "source": self.source,
            "timestamp": self.timestamp
        }


class ComponentEventData(EventData):
    """Event data for component lifecycle events."""
    
    def __init__(self, source: str, component_name: str):
        """
        Initialize the component event data.
        
        Args:
            source (str): The source of the event.
            component_name (str): The name of the component.
        """
        super().__init__(source)
        self.component_name = component_name
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["component_name"] = self.component_name
        return data


class ComponentErrorEventData(ComponentEventData):
    """Event data for component error events."""
    
    def __init__(self, source: str, component_name: str, error: Exception, message: str = None):
        """
        Initialize the component error event data.
        
        Args:
            source (str): The source of the event.
            component_name (str): The name of the component.
            error (Exception): The error that occurred.
            message (str, optional): A message describing the error. Defaults to None.
        """
        super().__init__(source, component_name)
        self.error = error
        self.message = message or str(error)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["error"] = str(self.error)
        data["message"] = self.message
        return data


class ConfigChangedEventData(EventData):
    """Event data for configuration change events."""
    
    def __init__(self, source: str, path: str, old_value: Any, new_value: Any):
        """
        Initialize the configuration changed event data.
        
        Args:
            source (str): The source of the event.
            path (str): The path to the configuration value that changed.
            old_value (Any): The old value.
            new_value (Any): The new value.
        """
        super().__init__(source)
        self.path = path
        self.old_value = old_value
        self.new_value = new_value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["path"] = self.path
        data["old_value"] = self.old_value
        data["new_value"] = self.new_value
        return data
