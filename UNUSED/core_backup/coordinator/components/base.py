"""
Base component implementation for the Focus Guard coordinator.

This module provides a base class for all component wrappers, implementing
common functionality and enforcing a consistent interface.
"""

import logging
from abc import abstractmethod
from typing import Dict, Any, Optional

from core_v2.coordinator.interfaces import Component, EventBus, EventListener
from core_v2.coordinator.events import EventTypes, ComponentEventData, ComponentErrorEventData
from core_v2.config.interfaces import ConfigurationManager


class BaseComponent(Component, EventListener):
    """
    Base class for all component wrappers.
    
    This class implements common functionality for all components, such as
    event handling, status reporting, and health monitoring.
    """
    
    def __init__(self, component_name: str, event_bus: EventBus, config_manager: ConfigurationManager):
        """
        Initialize the base component.
        
        Args:
            component_name (str): The name of the component.
            event_bus (EventBus): The event bus to use for communication.
            config_manager (ConfigurationManager): The configuration manager to use.
        """
        self._name = component_name
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._initialized = False
        self._running = False
        self._logger = logging.getLogger(f"focus_guard.coordinator.components.{component_name}")
    
    @property
    def name(self) -> str:
        """Get the component name."""
        return self._name
    
    async def initialize(self) -> bool:
        """
        Initialize the component.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        if self._initialized:
            self._logger.warning(f"Component {self._name} is already initialized")
            return True
        
        try:
            success = await self._initialize_component()
            if success:
                self._initialized = True
                await self._event_bus.publish(
                    EventTypes.COMPONENT_INITIALIZED,
                    ComponentEventData("coordinator", self._name)
                )
                self._logger.info(f"Component {self._name} initialized successfully")
            else:
                self._logger.error(f"Failed to initialize component {self._name}")
            return success
        except Exception as e:
            self._logger.exception(f"Error initializing component {self._name}: {e}")
            await self._event_bus.publish(
                EventTypes.COMPONENT_ERROR,
                ComponentErrorEventData("coordinator", self._name, e, f"Error initializing component {self._name}")
            )
            return False
    
    async def start(self) -> bool:
        """
        Start the component.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        if not self._initialized:
            self._logger.error(f"Component {self._name} is not initialized")
            return False
        
        if self._running:
            self._logger.warning(f"Component {self._name} is already running")
            return True
        
        try:
            success = await self._start_component()
            if success:
                self._running = True
                await self._event_bus.publish(
                    EventTypes.COMPONENT_STARTED,
                    ComponentEventData("coordinator", self._name)
                )
                self._logger.info(f"Component {self._name} started successfully")
            else:
                self._logger.error(f"Failed to start component {self._name}")
            return success
        except Exception as e:
            self._logger.exception(f"Error starting component {self._name}: {e}")
            await self._event_bus.publish(
                EventTypes.COMPONENT_ERROR,
                ComponentErrorEventData("coordinator", self._name, e, f"Error starting component {self._name}")
            )
            return False
    
    async def stop(self) -> bool:
        """
        Stop the component.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        if not self._running:
            self._logger.warning(f"Component {self._name} is not running")
            return True
        
        try:
            success = await self._stop_component()
            if success:
                self._running = False
                await self._event_bus.publish(
                    EventTypes.COMPONENT_STOPPED,
                    ComponentEventData("coordinator", self._name)
                )
                self._logger.info(f"Component {self._name} stopped successfully")
            else:
                self._logger.error(f"Failed to stop component {self._name}")
            return success
        except Exception as e:
            self._logger.exception(f"Error stopping component {self._name}: {e}")
            await self._event_bus.publish(
                EventTypes.COMPONENT_ERROR,
                ComponentErrorEventData("coordinator", self._name, e, f"Error stopping component {self._name}")
            )
            return False
    
    async def shutdown(self) -> bool:
        """
        Shutdown the component.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        if self._running:
            await self.stop()
        
        if not self._initialized:
            return True
        
        try:
            success = await self._shutdown_component()
            if success:
                self._initialized = False
                await self._event_bus.publish(
                    EventTypes.COMPONENT_SHUTDOWN,
                    ComponentEventData("coordinator", self._name)
                )
                self._logger.info(f"Component {self._name} shut down successfully")
            else:
                self._logger.error(f"Failed to shutdown component {self._name}")
            return success
        except Exception as e:
            self._logger.exception(f"Error shutting down component {self._name}: {e}")
            await self._event_bus.publish(
                EventTypes.COMPONENT_ERROR,
                ComponentErrorEventData("coordinator", self._name, e, f"Error shutting down component {self._name}")
            )
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the component status.
        
        Returns:
            Dict[str, Any]: A dictionary containing the component's status information.
        """
        status = {
            "name": self._name,
            "initialized": self._initialized,
            "running": self._running
        }
        
        try:
            component_status = self._get_component_status()
            status.update(component_status)
        except Exception as e:
            self._logger.exception(f"Error getting component status: {e}")
            status["error"] = str(e)
        
        return status
    
    def is_healthy(self) -> bool:
        """
        Check if the component is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        if not self._initialized:
            return False
        
        if not self._running:
            return False
        
        try:
            return self._is_component_healthy()
        except Exception as e:
            self._logger.exception(f"Error checking component health: {e}")
            return False
    
    async def on_event(self, event_type: str, event_data: Any) -> None:
        """
        Handle an event.
        
        Args:
            event_type (str): The type of event.
            event_data (Any): The event data.
        """
        if event_type == EventTypes.CONFIG_CHANGED:
            await self._handle_config_changed(event_data)
    
    @abstractmethod
    async def _initialize_component(self) -> bool:
        """
        Initialize the component implementation.
        
        This method should be overridden by subclasses to perform
        component-specific initialization.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def _start_component(self) -> bool:
        """
        Start the component implementation.
        
        This method should be overridden by subclasses to perform
        component-specific startup.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def _stop_component(self) -> bool:
        """
        Stop the component implementation.
        
        This method should be overridden by subclasses to perform
        component-specific shutdown.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def _shutdown_component(self) -> bool:
        """
        Shutdown the component implementation.
        
        This method should be overridden by subclasses to perform
        component-specific cleanup.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def _get_component_status(self) -> Dict[str, Any]:
        """
        Get the component-specific status.
        
        This method should be overridden by subclasses to provide
        component-specific status information.
        
        Returns:
            Dict[str, Any]: A dictionary containing the component's status information.
        """
        pass
    
    @abstractmethod
    def _is_component_healthy(self) -> bool:
        """
        Check if the component implementation is healthy.
        
        This method should be overridden by subclasses to provide
        component-specific health checks.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        pass
    
    async def _handle_config_changed(self, event_data: Any) -> None:
        """
        Handle a configuration change event.
        
        This method can be overridden by subclasses to handle
        component-specific configuration changes.
        
        Args:
            event_data (Any): The event data.
        """
        # Default implementation does nothing
        pass
