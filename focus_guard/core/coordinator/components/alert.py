"""
Alert system component for the Focus Guard coordinator.

This module provides a wrapper for the alert system, making it
available to the coordinator and other components.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

from focus_guard.core.coordinator.components.base import BaseComponent
from focus_guard.core.coordinator.interfaces import EventBus, Component
from focus_guard.core.coordinator.events import EventTypes, EventData
from focus_guard.core.config.interfaces import ConfigurationManager
from focus_guard.core.alert.system import AlertSystem
from focus_guard.core.alert.models import Alert, AlertType, AlertAction


def create_alert_component(event_bus: EventBus, config_manager: ConfigurationManager) -> Component:
    """
    Create and configure the alert system component.
    
    Args:
        event_bus: The event bus for component communication
        config_manager: The configuration manager
        
    Returns:
        Component: The configured alert system component
    """
    from focus_guard.core.alert.system import AlertSystem
    
    # Create alert system with config manager
    alert_system = AlertSystem(config_manager=config_manager)
    
    # Create and return the component
    return AlertSystemComponent(
        alert_system=alert_system,
        event_bus=event_bus,
        config_manager=config_manager
    )


class AlertTriggeredEventData(EventData):
    """Event data for alert triggered events."""
    
    def __init__(self, source: str, alert: Alert):
        """
        Initialize the alert triggered event data.
        
        Args:
            source (str): The source of the event.
            alert (Alert): The alert that was triggered.
        """
        super().__init__(source)
        self.alert = alert
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["alert"] = self.alert.to_dict() if hasattr(self.alert, "to_dict") else str(self.alert)
        return data


class AlertActionEventData(EventData):
    """Event data for alert action events."""
    
    def __init__(self, source: str, alert: Alert, action: AlertAction):
        """
        Initialize the alert action event data.
        
        Args:
            source (str): The source of the event.
            alert (Alert): The alert that the action is for.
            action (AlertAction): The action that was taken.
        """
        super().__init__(source)
        self.alert = alert
        self.action = action
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["alert"] = self.alert.to_dict() if hasattr(self.alert, "to_dict") else str(self.alert)
        data["action"] = self.action.to_dict() if hasattr(self.action, "to_dict") else str(self.action)
        return data


class AlertSystemComponent(BaseComponent):
    """
    Component wrapper for the alert system.
    
    This component provides access to the alert system and
    handles alert events.
    """
    
    def __init__(self, alert_system: AlertSystem, event_bus: EventBus, config_manager: ConfigurationManager):
        """
        Initialize the alert system component.
        
        Args:
            alert_system (AlertSystem): The alert system to use.
            event_bus (EventBus): The event bus to use for communication.
            config_manager (ConfigurationManager): The configuration manager to use.
        """
        super().__init__("alert_system", event_bus, config_manager)
        self._alert_system = alert_system
        self._active_alerts = {}  # Dictionary of active alerts by ID
        self._enabled = True
        self._is_idle = False
        self._cooldown_seconds = 60  # Default cooldown period in seconds
        self._last_alert_time = {}  # Dictionary of last alert times by domain
    
    async def _initialize_component(self) -> bool:
        """
        Initialize the alert system component.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Configure from settings
            # Handle different config manager interfaces
            if hasattr(self._config_manager, 'get_value'):
                self._enabled = self._config_manager.get_value("alert_system.enabled", True)
            else:
                self._enabled = self._config_manager.get("alert_system.enabled", True)
            # Handle different config manager interfaces for cooldown
            if hasattr(self._config_manager, 'get_value'):
                self._cooldown_seconds = self._config_manager.get_value("alert_system.cooldown_seconds", self._cooldown_seconds)
            else:
                self._cooldown_seconds = self._config_manager.get("alert_system.cooldown_seconds", self._cooldown_seconds)
            
            # Initialize the alert system
            self._logger.info("Initializing alert system")
            
            # Subscribe to relevant events
            self._event_bus.subscribe(EventTypes.DISTRACTION_DETECTED, self)
            self._event_bus.subscribe(EventTypes.IDLE_STATE_CHANGED, self)
            
            return True
        except Exception as e:
            self._logger.exception(f"Error initializing alert system: {e}")
            return False
    
    async def _start_component(self) -> bool:
        """
        Start the alert system component.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        try:
            self._logger.info("Alert system started")
            return True
        except Exception as e:
            self._logger.exception(f"Error starting alert system: {e}")
            return False
    
    async def _stop_component(self) -> bool:
        """
        Stop the alert system component.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        try:
            # Dismiss all active alerts
            for alert_id in list(self._active_alerts.keys()):
                await self._dismiss_alert(alert_id)
            
            self._logger.info("Alert system stopped")
            return True
        except Exception as e:
            self._logger.exception(f"Error stopping alert system: {e}")
            return False
    
    async def _shutdown_component(self) -> bool:
        """
        Shutdown the alert system component.
        
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
            "enabled": self._enabled,
            "active_alerts": len(self._active_alerts),
            "is_idle": self._is_idle,
            "cooldown_seconds": self._cooldown_seconds
        }
    
    def _is_component_healthy(self) -> bool:
        """
        Check if the component implementation is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        # Alert system is always healthy if initialized
        return True
    
    async def on_event(self, event_type: str, event_data: Any) -> None:
        """
        Handle an event.
        
        Args:
            event_type (str): The type of event.
            event_data (Any): The event data.
        """
        await super().on_event(event_type, event_data)
        
        if not self._enabled:
            return
        
        if event_type == EventTypes.IDLE_STATE_CHANGED:
            # Handle idle state changes
            self._is_idle = event_data.is_idle
            
            if self._is_idle:
                # User is idle, dismiss all active alerts
                self._logger.info("User is idle, dismissing all active alerts")
                for alert_id in list(self._active_alerts.keys()):
                    await self._dismiss_alert(alert_id)
        
        elif event_type == EventTypes.DISTRACTION_DETECTED and not self._is_idle:
            # Handle distraction detected events
            distraction_event = event_data.distraction_event
            domain = distraction_event.domain
            
            # Check cooldown period
            now = datetime.now()
            last_alert_time = self._last_alert_time.get(domain)
            if last_alert_time and (now - last_alert_time).total_seconds() < self._cooldown_seconds:
                # Still in cooldown period, don't trigger another alert
                self._logger.debug(f"Skipping alert for {domain} due to cooldown period")
                return
            
            # Trigger alert
            await self._trigger_alert(distraction_event)
    
    async def _trigger_alert(self, distraction_event) -> None:
        """
        Trigger an alert for a distraction event.
        
        Args:
            distraction_event: The distraction event to trigger an alert for.
        """
        try:
            # Create alert
            alert = await self._alert_system.create_alert(
                alert_type=AlertType.DISTRACTION,
                title=f"Distraction Detected: {distraction_event.domain}",
                message=f"You are being distracted by {distraction_event.domain}",
                data={
                    "domain": distraction_event.domain,
                    "url": distraction_event.url,
                    "category": str(distraction_event.category)
                }
            )
            
            # Add to active alerts
            self._active_alerts[alert.id] = alert
            
            # Update last alert time
            self._last_alert_time[distraction_event.domain] = datetime.now()
            
            # Publish alert triggered event
            await self._event_bus.publish(
                EventTypes.ALERT_TRIGGERED,
                AlertTriggeredEventData("alert_system", alert)
            )
            
            # Show alert
            await self._alert_system.show_alert(alert)
            
            self._logger.info(f"Alert triggered for {distraction_event.domain}")
        
        except Exception as e:
            self._logger.exception(f"Error triggering alert: {e}")
    
    async def _dismiss_alert(self, alert_id: str) -> None:
        """
        Dismiss an alert.
        
        Args:
            alert_id (str): The ID of the alert to dismiss.
        """
        try:
            # Get alert
            alert = self._active_alerts.get(alert_id)
            if not alert:
                return
            
            # Remove from active alerts
            del self._active_alerts[alert_id]
            
            # Dismiss alert
            await self._alert_system.dismiss_alert(alert)
            
            # Publish alert dismissed event
            await self._event_bus.publish(
                EventTypes.ALERT_DISMISSED,
                AlertActionEventData("alert_system", alert, AlertAction.DISMISS)
            )
            
            self._logger.info(f"Alert dismissed: {alert_id}")
        
        except Exception as e:
            self._logger.exception(f"Error dismissing alert: {e}")
    
    async def _handle_config_changed(self, event_data: Any) -> None:
        """
        Handle a configuration change event.
        
        Args:
            event_data (Any): The event data.
        """
        path = event_data.path
        new_value = event_data.new_value
        
        if path == "alert_system.enabled":
            old_enabled = self._enabled
            self._enabled = new_value
            
            self._logger.info(f"Alert system {'enabled' if new_value else 'disabled'}")
            
            if old_enabled and not new_value:
                # System was disabled, dismiss all active alerts
                for alert_id in list(self._active_alerts.keys()):
                    await self._dismiss_alert(alert_id)
        
        elif path == "alert_system.cooldown_seconds":
            self._cooldown_seconds = new_value
            self._logger.info(f"Updated cooldown period to {new_value} seconds")
    
    def get_alert_system(self) -> AlertSystem:
        """
        Get the alert system.
        
        Returns:
            AlertSystem: The alert system.
        """
        return self._alert_system
    
    def get_active_alerts(self) -> Dict[str, Alert]:
        """
        Get the active alerts.
        
        Returns:
            Dict[str, Alert]: A dictionary of active alerts by ID.
        """
        return self._active_alerts
    
    async def trigger_alert(self, alert_type: AlertType, title: str, message: str, data: Dict[str, Any] = None) -> Optional[Alert]:
        """
        Trigger an alert.
        
        Args:
            alert_type (AlertType): The type of alert.
            title (str): The alert title.
            message (str): The alert message.
            data (Dict[str, Any], optional): Additional alert data. Defaults to None.
            
        Returns:
            Optional[Alert]: The created alert, or None if the alert could not be created.
        """
        if not self._enabled or self._is_idle:
            return None
        
        try:
            # Create alert
            alert = await self._alert_system.create_alert(
                alert_type=alert_type,
                title=title,
                message=message,
                data=data or {}
            )
            
            # Add to active alerts
            self._active_alerts[alert.id] = alert
            
            # Publish alert triggered event
            await self._event_bus.publish(
                EventTypes.ALERT_TRIGGERED,
                AlertTriggeredEventData("alert_system", alert)
            )
            
            # Show alert
            await self._alert_system.show_alert(alert)
            
            self._logger.info(f"Alert triggered: {title}")
            
            return alert
        
        except Exception as e:
            self._logger.exception(f"Error triggering alert: {e}")
            return None
    
    async def dismiss_alert(self, alert_id: str) -> bool:
        """
        Dismiss an alert.
        
        Args:
            alert_id (str): The ID of the alert to dismiss.
            
        Returns:
            bool: True if the alert was dismissed, False otherwise.
        """
        if alert_id not in self._active_alerts:
            return False
        
        await self._dismiss_alert(alert_id)
        return True
