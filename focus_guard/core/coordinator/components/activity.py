"""
Activity monitor component for the Focus Guard coordinator.

This module provides a wrapper for the activity monitor system, making it
available to the coordinator and other components.
"""

import asyncio
import logging
from typing import Dict, Any, TYPE_CHECKING

from focus_guard.core.coordinator.components.base import BaseComponent
from focus_guard.core.coordinator.interfaces import EventBus, Component
from focus_guard.core.coordinator.events import EventTypes, EventData
from focus_guard.core.config.interfaces import ConfigurationManager
from focus_guard.core.activity.monitor import ActivityMonitor
from focus_guard.core.activity.models import WindowInfo, ActivityEvent


def create_activity_component(event_bus: EventBus, config_manager: ConfigurationManager) -> Component:
    """
    Create and configure the activity monitor component.
    
    Args:
        event_bus: The event bus for component communication
        config_manager: The configuration manager
        
    Returns:
        Component: The configured activity monitor component
    """
    from focus_guard.core.activity.monitor import ActivityMonitor
    
    # Create the activity monitor
    activity_monitor = ActivityMonitor()
    
    # Create and return the component
    return ActivityMonitorComponent(
        activity_monitor=activity_monitor,
        event_bus=event_bus,
        config_manager=config_manager
    )


class ActivityEventData(EventData):
    """Event data for activity events."""
    
    def __init__(self, source: str, event: ActivityEvent):
        """
        Initialize the activity event data.
        
        Args:
            source (str): The source of the event.
            event (ActivityEvent): The activity event.
        """
        super().__init__(source)
        self.event = event
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["event"] = self.event.to_dict() if hasattr(self.event, "to_dict") else str(self.event)
        return data


class WindowChangedEventData(EventData):
    """Event data for window changed events."""
    
    def __init__(self, source: str, window_title: str, executable: str, pid: int):
        """
        Initialize the window changed event data.
        
        Args:
            source (str): The source of the event.
            window_title (str): The title of the window.
            executable (str): The executable name of the process.
            pid (int): The process ID.
        """
        super().__init__(source)
        self.window_title = window_title
        self.executable = executable
        self.pid = pid
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["window_title"] = self.window_title
        data["executable"] = self.executable
        data["pid"] = self.pid
        return data


class IdleStateChangedEventData(EventData):
    """Event data for idle state changed events."""
    
    def __init__(self, source: str, is_idle: bool, idle_time: float):
        """
        Initialize the idle state changed event data.
        
        Args:
            source (str): The source of the event.
            is_idle (bool): Whether the system is idle.
            idle_time (float): The idle time in seconds.
        """
        super().__init__(source)
        self.is_idle = is_idle
        self.idle_time = idle_time
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["is_idle"] = self.is_idle
        data["idle_time"] = self.idle_time
        return data


class ActivityMonitorComponent(BaseComponent):
    """
    Component wrapper for the activity monitor system.
    
    This component provides access to the activity monitor system and
    handles activity events.
    """
    
    def __init__(self, activity_monitor: ActivityMonitor, event_bus: EventBus, config_manager: ConfigurationManager):
        """
        Initialize the activity monitor component.
        
        Args:
            activity_monitor (ActivityMonitor): The activity monitor to use.
            event_bus (EventBus): The event bus to use for communication.
            config_manager (ConfigurationManager): The configuration manager to use.
        """
        super().__init__("activity_monitor", event_bus, config_manager)
        self._activity_monitor = activity_monitor
        self._polling_task = None
        self._polling_interval = 1.0  # Default polling interval in seconds
        self._idle_timeout = 300  # Default idle timeout in seconds
        self._idle_threshold_seconds = 300  # Default idle threshold in seconds
        self._last_window_info = None
        self._is_idle = False
    
    async def _initialize_component(self) -> bool:
        """
        Initialize the activity monitor component.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Configure from settings - handle different config manager interfaces
            if hasattr(self._config_manager, 'get_value'):
                self._polling_interval = self._config_manager.get_value(
                    "activity_monitor.polling_interval_seconds", 
                    self._polling_interval
                )
                self._idle_threshold_seconds = self._config_manager.get_value(
                    "activity_monitor.idle_threshold_seconds", 
                    self._idle_threshold_seconds
                )
                self._idle_timeout = self._config_manager.get_value(
                    "activity_monitor.idle_timeout_seconds", 
                    self._idle_timeout
                )
            else:
                self._polling_interval = self._config_manager.get(
                    "activity_monitor.polling_interval_seconds", 
                    self._polling_interval
                )
                self._idle_threshold_seconds = self._config_manager.get(
                    "activity_monitor.idle_threshold_seconds", 
                    self._idle_threshold_seconds
                )
                self._idle_timeout = self._config_manager.get(
                    "activity_monitor.idle_timeout_seconds", 
                    self._idle_timeout
                )
            
            # Initialize the activity monitor
            self._logger.info("Initializing activity monitor")
            return True
        except Exception as e:
            self._logger.exception(f"Error initializing activity monitor: {e}")
            return False
    
    async def _start_component(self) -> bool:
        """
        Start the activity monitor component.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        try:
            # Start polling for activity
            self._polling_task = asyncio.create_task(self._poll_activity())
            self._logger.info("Activity monitor started")
            return True
        except Exception as e:
            self._logger.exception(f"Error starting activity monitor: {e}")
            return False
    
    async def _stop_component(self) -> bool:
        """
        Stop the activity monitor component.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        try:
            if self._polling_task is not None:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass  # Expected when task is cancelled
                self._polling_task = None
            self._logger.info("Activity monitor stopped")
            return True
        except Exception as e:
            self._logger.exception(f"Error stopping activity monitor: {e}")
            return False
    
    async def _shutdown_component(self) -> bool:
        """
        Shutdown the activity monitor component.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        # Nothing additional to do here
        return True
    
    def _get_component_status(self) -> Dict[str, Any]:
        """
        Get the component-specific status.
        
        Returns:
            Dict[str, Any]: A dictionary containing the component's status information.
        """
        return {
            "polling_interval": self._polling_interval,
            "idle_threshold_seconds": self._idle_threshold_seconds,
            "is_idle": self._is_idle,
            "current_window": self._last_window_info.to_dict() if self._last_window_info else None
        }
    
    def _is_component_healthy(self) -> bool:
        """
        Check if the component implementation is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        # Activity monitor is healthy if polling task is running
        return self._polling_task is not None and not self._polling_task.done()
    
    async def _poll_activity(self) -> None:
        """
        Poll for activity events.
        
        This method runs in a loop, polling for activity events and
        publishing them to the event bus.
        """
        self._logger.debug("Starting activity polling")
        
        try:
            while True:
                try:
                    # Get current window info
                    window_info = self._activity_monitor.get_active_window()
                    
                    if window_info is None:
                        await asyncio.sleep(self._polling_interval)
                        continue
                    
                    # Check if window changed
                    if (self._last_window_info is None or 
                            window_info.pid != self._last_window_info.pid or
                            window_info.window_title != self._last_window_info.window_title or
                            window_info.app_name != self._last_window_info.app_name):
                        
                        # Publish window changed event
                        await self._event_bus.publish(
                            EventTypes.WINDOW_CHANGED,
                            WindowChangedEventData("activity_monitor", window_info.window_title, window_info.app_name, window_info.pid)
                        )
                        
                        self._last_window_info = window_info
                    
                    # Check idle state
                    idle_time = self._activity_monitor.get_idle_time_seconds()
                    is_idle = idle_time >= self._idle_threshold_seconds
                    
                    if is_idle != self._is_idle:
                        # Publish idle state changed event
                        await self._event_bus.publish(
                            EventTypes.IDLE_STATE_CHANGED,
                            IdleStateEventData("activity_monitor", is_idle, idle_time)
                        )
                        
                        self._is_idle = is_idle
                    
                except Exception as e:
                    self._logger.exception(f"Error polling activity: {e}")
                
                # Wait for next poll
                await asyncio.sleep(self._polling_interval)
        
        except asyncio.CancelledError:
            self._logger.debug("Activity polling cancelled")
            raise
    
    async def _handle_config_changed(self, event_data: Any) -> None:
        """
        Handle a configuration change event.
        
        Args:
            event_data (Any): The event data.
        """
        path = event_data.path
        new_value = event_data.new_value
        
        if path == "activity_monitor.polling_interval_seconds":
            self._polling_interval = new_value
            self._logger.info(f"Updated polling interval to {new_value} seconds")
        
        elif path == "activity_monitor.idle_threshold_seconds":
            self._idle_threshold_seconds = new_value
            self._logger.info(f"Updated idle threshold to {new_value} seconds")
        elif path == "activity_monitor.idle_timeout_seconds":
            self._idle_timeout = new_value
            self._logger.info(f"Updated idle timeout to {new_value} seconds")
    
    def get_activity_monitor(self) -> ActivityMonitor:
        """
        Get the activity monitor.
        
        Returns:
            ActivityMonitor: The activity monitor.
        """
        return self._activity_monitor
