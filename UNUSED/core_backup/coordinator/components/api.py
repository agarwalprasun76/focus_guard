"""
API server component for the Focus Guard coordinator.

This module provides a wrapper for the API server, making it
available to the coordinator and other components.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from core_v2.coordinator.components.base import BaseComponent
from core_v2.coordinator.interfaces import EventBus
from core_v2.coordinator.events import EventTypes, EventData
from core_v2.config.interfaces import ConfigurationManager
from core_v2.api.server import ApiServer


class ApiRequestEventData(EventData):
    """Event data for API request events."""
    
    def __init__(self, source: str, endpoint: str, method: str, data: Dict[str, Any]):
        """
        Initialize the API request event data.
        
        Args:
            source (str): The source of the event.
            endpoint (str): The API endpoint.
            method (str): The HTTP method.
            data (Dict[str, Any]): The request data.
        """
        super().__init__(source)
        self.endpoint = endpoint
        self.method = method
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["endpoint"] = self.endpoint
        data["method"] = self.method
        data["data"] = self.data
        return data


class ApiServerComponent(BaseComponent):
    """
    Component wrapper for the API server.
    
    This component provides access to the API server and
    handles API events.
    """
    
    def __init__(self, api_server: ApiServer, event_bus: EventBus, config_manager: ConfigurationManager):
        """
        Initialize the API server component.
        
        Args:
            api_server (ApiServer): The API server to use.
            event_bus (EventBus): The event bus to use for communication.
            config_manager (ConfigurationManager): The configuration manager to use.
        """
        super().__init__("api_server", event_bus, config_manager)
        self._api_server = api_server
        self._enabled = True
        self._host = "127.0.0.1"  # Default host
        self._port = 5000  # Default port
        self._health_check_interval = 60.0  # Default health check interval in seconds
        self._health_check_task = None
    
    async def _initialize_component(self) -> bool:
        """
        Initialize the API server component.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Configure from settings
            self._enabled = self._config_manager.get(
                "api_server.enabled", 
                self._enabled
            )
            self._host = self._config_manager.get(
                "api_server.host", 
                self._host
            )
            self._port = self._config_manager.get(
                "api_server.port", 
                self._port
            )
            self._health_check_interval = self._config_manager.get(
                "api_server.health_check_interval_seconds", 
                self._health_check_interval
            )
            
            # Initialize the API server
            self._logger.info("Initializing API server")
            
            # Set up API server event handlers
            self._api_server.on_request(self._on_api_request)
            
            # Initialize the API server
            await self._api_server.initialize(self._host, self._port)
            
            return True
        except Exception as e:
            self._logger.exception(f"Error initializing API server: {e}")
            return False
    
    async def _start_component(self) -> bool:
        """
        Start the API server component.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        try:
            if not self._enabled:
                self._logger.info("API server is disabled, not starting")
                return True
            
            # Start the API server
            self._logger.info(f"Starting API server on {self._host}:{self._port}")
            await self._api_server.start()
            
            # Start health check
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._logger.info("API server started")
            return True
        except Exception as e:
            self._logger.exception(f"Error starting API server: {e}")
            return False
    
    async def _stop_component(self) -> bool:
        """
        Stop the API server component.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        try:
            # Stop health check
            if self._health_check_task is not None:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
                self._health_check_task = None
            
            # Stop the API server
            if self._api_server.is_running():
                self._logger.info("Stopping API server")
                await self._api_server.stop()
            
            self._logger.info("API server stopped")
            return True
        except Exception as e:
            self._logger.exception(f"Error stopping API server: {e}")
            return False
    
    async def _shutdown_component(self) -> bool:
        """
        Shutdown the API server component.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        try:
            # Shutdown the API server
            self._logger.info("Shutting down API server")
            await self._api_server.shutdown()
            
            return True
        except Exception as e:
            self._logger.exception(f"Error shutting down API server: {e}")
            return False
    
    def _get_component_status(self) -> Dict[str, Any]:
        """
        Get the component-specific status.
        
        Returns:
            Dict[str, Any]: A dictionary containing the component's status information.
        """
        return {
            "enabled": self._enabled,
            "host": self._host,
            "port": self._port,
            "running": self._api_server.is_running()
        }
    
    def _is_component_healthy(self) -> bool:
        """
        Check if the component implementation is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        # API server is healthy if it's running or disabled
        return not self._enabled or self._api_server.is_running()
    
    async def _health_check_loop(self) -> None:
        """
        Perform periodic health checks on the API server.
        
        This method runs in a loop, checking the health of the API server
        and attempting to recover if necessary.
        """
        self._logger.debug("Starting API server health check loop")
        
        try:
            while True:
                try:
                    # Check if API server is running
                    if self._enabled and not self._api_server.is_running():
                        self._logger.warning("API server is not running, attempting to restart")
                        await self._api_server.stop()
                        await self._api_server.start()
                
                except Exception as e:
                    self._logger.exception(f"Error in API server health check: {e}")
                
                # Wait for next health check
                await asyncio.sleep(self._health_check_interval)
        
        except asyncio.CancelledError:
            self._logger.debug("API server health check cancelled")
            raise
    
    async def _on_api_request(self, endpoint: str, method: str, data: Dict[str, Any]) -> None:
        """
        Handle an API request.
        
        Args:
            endpoint (str): The API endpoint.
            method (str): The HTTP method.
            data (Dict[str, Any]): The request data.
        """
        try:
            # Publish API request event
            await self._event_bus.publish(
                EventTypes.API_REQUEST,
                ApiRequestEventData("api_server", endpoint, method, data)
            )
        except Exception as e:
            self._logger.exception(f"Error handling API request: {e}")
    
    async def _handle_config_changed(self, event_data: Any) -> None:
        """
        Handle a configuration change event.
        
        Args:
            event_data (Any): The event data.
        """
        path = event_data.path
        new_value = event_data.new_value
        
        if path == "api_server.enabled":
            old_enabled = self._enabled
            self._enabled = new_value
            
            self._logger.info(f"API server {'enabled' if new_value else 'disabled'}")
            
            if old_enabled and not new_value:
                # Server was enabled and is now disabled, stop it
                if self._api_server.is_running():
                    await self._api_server.stop()
            elif not old_enabled and new_value:
                # Server was disabled and is now enabled, start it
                if not self._api_server.is_running():
                    await self._api_server.start()
        
        elif path == "api_server.host":
            self._host = new_value
            self._logger.info(f"Updated API server host to {new_value}")
            
            # Restart server if running
            if self._enabled and self._api_server.is_running():
                await self._api_server.stop()
                await self._api_server.initialize(self._host, self._port)
                await self._api_server.start()
        
        elif path == "api_server.port":
            self._port = new_value
            self._logger.info(f"Updated API server port to {new_value}")
            
            # Restart server if running
            if self._enabled and self._api_server.is_running():
                await self._api_server.stop()
                await self._api_server.initialize(self._host, self._port)
                await self._api_server.start()
        
        elif path == "api_server.health_check_interval_seconds":
            self._health_check_interval = new_value
            self._logger.info(f"Updated health check interval to {new_value} seconds")
    
    def get_api_server(self) -> ApiServer:
        """
        Get the API server.
        
        Returns:
            ApiServer: The API server.
        """
        return self._api_server
    
    def is_api_server_running(self) -> bool:
        """
        Check if the API server is running.
        
        Returns:
            bool: True if the API server is running, False otherwise.
        """
        return self._api_server.is_running()
    
    def get_api_url(self) -> str:
        """
        Get the API server URL.
        
        Returns:
            str: The API server URL.
        """
        return f"http://{self._host}:{self._port}"
