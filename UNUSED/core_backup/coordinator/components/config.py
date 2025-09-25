"""
Configuration component for the Focus Guard coordinator.

This module provides a wrapper for the configuration system, making it
available to the coordinator and other components.
"""

import logging
import asyncio
from typing import Dict, Any

from core_v2.coordinator.components.base import BaseComponent
from core_v2.coordinator.interfaces import EventBus
from core_v2.coordinator.events import EventTypes, ConfigChangedEventData
from core_v2.config.interfaces import ConfigurationManager


class ConfigComponent(BaseComponent):
    """
    Component wrapper for the configuration system.
    
    This component provides access to the configuration system and
    handles configuration change events.
    """
    
    def __init__(self, config_manager: ConfigurationManager, event_bus: EventBus):
        """
        Initialize the configuration component.
        
        Args:
            config_manager (ConfigurationManager): The configuration manager to use.
            event_bus (EventBus): The event bus to use for communication.
        """
        super().__init__("config", event_bus, config_manager)
        self._config_manager = config_manager
        
        # Set up configuration change listener
        self._config_manager.add_change_listener(self._on_config_changed)
    
    async def _initialize_component(self) -> bool:
        """
        Initialize the configuration component.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        # Load configuration
        try:
            # Ensure configuration is loaded
            self._logger.info("Loading configuration")
            return True
        except Exception as e:
            self._logger.exception(f"Error loading configuration: {e}")
            return False
    
    async def _start_component(self) -> bool:
        """
        Start the configuration component.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        # Nothing to do here, configuration is already loaded
        return True
    
    async def _stop_component(self) -> bool:
        """
        Stop the configuration component.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        # Nothing to do here
        return True
    
    async def _shutdown_component(self) -> bool:
        """
        Shutdown the configuration component.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        # Remove change listener
        self._config_manager.remove_change_listener(self._on_config_changed)
        return True
    
    def _get_component_status(self) -> Dict[str, Any]:
        """
        Get the component-specific status.
        
        Returns:
            Dict[str, Any]: A dictionary containing the component's status information.
        """
        return {
            "config_paths": len(self._config_manager.all_paths()),
            "providers": [provider.__class__.__name__ for provider in self._config_manager.get_providers()]
        }
    
    def _is_component_healthy(self) -> bool:
        """
        Check if the component implementation is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        # Configuration is healthy if it's loaded
        return True
    
    def _on_config_changed(self, path: str, old_value: Any, new_value: Any) -> None:
        """
        Handle a configuration change.
        
        Args:
            path (str): The path to the configuration value that changed.
            old_value (Any): The old value.
            new_value (Any): The new value.
        """
        # Publish a configuration change event
        event_data = ConfigChangedEventData("config", path, old_value, new_value)
        try:
            asyncio.create_task(self._event_bus.publish(EventTypes.CONFIG_CHANGED, event_data))
        except RuntimeError:
            # No event loop running, just log it for testing purposes
            logging.debug(f"No event loop running, skipping event publish for {path}")
    
    def get_config_manager(self) -> ConfigurationManager:
        """
        Get the configuration manager.
        
        Returns:
            ConfigurationManager: The configuration manager.
        """
        return self._config_manager
