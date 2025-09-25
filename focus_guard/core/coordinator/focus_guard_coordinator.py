"""
Main coordinator implementation for the Focus Guard application.

This module provides the FocusGuardCoordinator class, which is responsible for
orchestrating all components of the Focus Guard application.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Set

from focus_guard.core.coordinator.interfaces import Component, Coordinator, EventBus, EventListener, ComponentDependency
from focus_guard.core.coordinator.lifecycle import ComponentLifecycleManager
from focus_guard.core.coordinator.events import DefaultEventBus, EventTypes, ComponentEventData, ComponentErrorEventData
from focus_guard.core.config.interfaces import ConfigurationManager


class FocusGuardCoordinator(Coordinator):
    """
    Main coordinator for the Focus Guard application.
    
    Responsibilities:
    1. Initialize and manage all components
    2. Handle inter-component communication
    3. Manage component lifecycle
    4. Monitor component health
    5. Collect and report metrics
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        """
        Initialize the coordinator with a configuration manager.
        
        Args:
            config_manager (ConfigurationManager): The configuration manager to use.
        """
        self.config_manager = config_manager
        self.lifecycle_manager = ComponentLifecycleManager()
        self.event_bus = DefaultEventBus()
        self.running = False
        self.logger = logging.getLogger("focus_guard.coordinator")
    
    async def initialize(self) -> bool:
        """
        Initialize the coordinator and all components.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        self.logger.info("Initializing Focus Guard Coordinator")
        
        # Register components with the lifecycle manager
        try:
            await self._register_components()
        except Exception as e:
            self.logger.exception(f"Error registering components: {e}")
            return False
        
        # Initialize all components
        success = await self.lifecycle_manager.initialize_all()
        if not success:
            self.logger.error("Failed to initialize all components")
            await self.shutdown()
            return False
            
        # Don't set running=True here - that should happen in start()
        self.logger.info("Focus Guard Coordinator initialized successfully")
        return True
    
    async def start(self) -> bool:
        """
        Start the coordinator and all components.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        if self.running:
            self.logger.warning("Coordinator is already running")
            return True
        
        self.logger.info("Starting Focus Guard Coordinator")
        
        # Start all components
        success = await self.lifecycle_manager.start_all()
        if not success:
            self.logger.error("Failed to start all components")
            return False
        
        self.running = True
        self.logger.info("Focus Guard Coordinator started successfully")
        return True
    
    async def stop(self) -> bool:
        """
        Stop the coordinator and all components.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        if not self.running:
            self.logger.warning("Coordinator is not running")
            return True
        
        self.logger.info("Stopping Focus Guard Coordinator")
        
        # Stop all components
        success = await self.lifecycle_manager.stop_all()
        if not success:
            self.logger.error("Failed to stop all components")
            return False
        
        self.running = False
        self.logger.info("Focus Guard Coordinator stopped successfully")
        return True
    
    async def shutdown(self) -> bool:
        """
        Shutdown the coordinator and all components.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        if self.running:
            await self.stop()
        
        self.logger.info("Shutting down Focus Guard Coordinator")
        
        # Shutdown all components
        success = await self.lifecycle_manager.shutdown_all()
        if not success:
            self.logger.error("Failed to shutdown all components")
            return False
        
        self.logger.info("Focus Guard Coordinator shut down successfully")
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the coordinator and all components.
        
        Returns:
            Dict[str, Any]: A dictionary containing the coordinator's status information.
        """
        status = {
            "coordinator_running": self.running,
            "components": self.lifecycle_manager.get_status()
        }
        return status
    
    def is_healthy(self) -> bool:
        """
        Check if the coordinator and all components are healthy.
        
        Returns:
            bool: True if the coordinator and all components are healthy, False otherwise.
        """
        if not self.running:
            return False
        
        return self.lifecycle_manager.is_healthy()
    
    def get_component(self, name: str) -> Optional[Component]:
        """
        Get a component by name.
        
        Args:
            name (str): The name of the component.
            
        Returns:
            Optional[Component]: The component if found, None otherwise.
        """
        return self.lifecycle_manager.get_component(name)
    
    async def _register_components(self) -> bool:
        """
        Register all components with the lifecycle manager.
        
        This method creates and registers all the components that the coordinator
        will manage. The components are registered with their dependencies to
        ensure proper startup and shutdown order.
        """
        from focus_guard.core.coordinator.components.config import ConfigComponent
        from focus_guard.core.coordinator.components.activity import ActivityMonitorComponent
        from focus_guard.core.coordinator.components.browser import BrowserIntegrationComponent
        from focus_guard.core.coordinator.components.classification import DomainClassifierComponent
        from focus_guard.core.coordinator.components.distraction import DistractionDetectorComponent
        from focus_guard.core.coordinator.components.alert import AlertSystemComponent
        
        # Configuration component (always first)
        config_component = ConfigComponent(self.config_manager, self.event_bus)
        if config_component is None:
            self.logger.error("Failed to create config component")
            return False
            
        self.lifecycle_manager.register_component(config_component, [])
        
        # Activity monitoring
        activity_component = await self._create_activity_component()
        if activity_component is None:
            self.logger.error("Failed to create activity component")
            return False
            
        self.lifecycle_manager.register_component(
            activity_component,
            [ComponentDependency("config")]
        )
        
        # Browser detection and integration
        browser_component = await self._create_browser_component()
        if browser_component is None:
            self.logger.error("Failed to create browser component")
            return False
            
        self.lifecycle_manager.register_component(
            browser_component,
            [ComponentDependency("config")]
        )
        
        # Domain classification
        classifier_component = await self._create_classifier_component()
        if classifier_component is None:
            self.logger.error("Failed to create classifier component")
            return False
            
        self.lifecycle_manager.register_component(
            classifier_component,
            [ComponentDependency("config")]
        )
        
        # Distraction detection
        distraction_component = await self._create_distraction_component()
        if distraction_component is None:
            self.logger.error("Failed to create distraction component")
            return False
            
        self.lifecycle_manager.register_component(
            distraction_component,
            [
                ComponentDependency("config"),
                ComponentDependency("activity_monitor"),
                ComponentDependency("browser_integration"),
                ComponentDependency("domain_classifier")
            ]
        )
        
        # Alert system
        alert_component = await self._create_alert_component()
        if alert_component is not None:  # Alert system is optional
            self.lifecycle_manager.register_component(
                alert_component,
                [
                    ComponentDependency("config"),
                    ComponentDependency("distraction_detector")
                ]
            )
        
        # API server (if enabled)
        # Handle different config manager interfaces
        if hasattr(self.config_manager, 'get_value'):
            api_enabled = self.config_manager.get_value("api_server.enabled", False)
        else:
            api_enabled = self.config_manager.get("api_server.enabled", False)
        
        if api_enabled:
            api_component = await self._create_api_component()
            if api_component is not None:  # API server is optional
                self.lifecycle_manager.register_component(
                    api_component,
                    [ComponentDependency("config")]
                )
                
        return True  # All components registered successfully
    
    async def _create_activity_component(self) -> Component:
        """
        Create and configure the activity monitor component.
        
        Returns:
            Component: The activity monitor component.
        """
        from focus_guard.core.coordinator.components.activity import create_activity_component
        
        try:
            # Create and return the component using the factory function
            return create_activity_component(
                event_bus=self.event_bus,
                config_manager=self.config_manager
            )
        except Exception as e:
            self.logger.error(f"Failed to create activity component: {e}", exc_info=True)
            return None
    
    async def _create_browser_component(self) -> Component:
        """
        Create and configure the browser integration component.
        
        Returns:
            Component: The browser integration component.
        """
        from focus_guard.core.coordinator.components.browser import create_browser_component
        
        try:
            # Create and return the component using the factory function
            return create_browser_component(
                event_bus=self.event_bus,
                config_manager=self.config_manager
            )
        except Exception as e:
            self.logger.error(f"Failed to create browser component: {e}", exc_info=True)
            return None
    
    async def _create_distraction_component(self) -> Component:
        """
        Create and configure the distraction detector component.
        
        Returns:
            Component: The distraction detector component.
        """
        from focus_guard.core.coordinator.components.distraction import create_distraction_component
        
        try:
            # Create and return the component using the factory function
            return create_distraction_component(
                event_bus=self.event_bus,
                config_manager=self.config_manager
            )
        except Exception as e:
            self.logger.error(f"Failed to create distraction component: {e}", exc_info=True)
            return None
    
    async def _create_classifier_component(self) -> Component:
        """
        Create and configure the domain classifier component.
        
        Returns:
            Component: The domain classifier component.
        """
        from focus_guard.core.coordinator.components.classification import create_classifier_component
        
        try:
            # Create and return the component using the factory function
            return create_classifier_component(
                event_bus=self.event_bus,
                config_manager=self.config_manager
            )
        except Exception as e:
            self.logger.error(f"Failed to create classifier component: {e}", exc_info=True)
            return None
    
    async def _create_alert_component(self) -> Component:
        """
        Create and configure the alert system component.
        
        Returns:
            Component: The alert system component.
        """
        from focus_guard.core.coordinator.components.alert import create_alert_component
        
        try:
            # Create and return the component using the factory function
            return create_alert_component(
                event_bus=self.event_bus,
                config_manager=self.config_manager
            )
        except Exception as e:
            self.logger.error(f"Failed to create alert component: {e}", exc_info=True)
            return None
    
    async def _create_api_component(self) -> Component:
        """
        Create and configure the API server component.
        
        Returns:
            Component: The API server component.
        """
        from focus_guard.core.coordinator.components.api import ApiServerComponent
        from focus_guard.core.api.server import ApiServer
        
        api_server = ApiServer()
        
        return ApiServerComponent(
            api_server,
            self.event_bus,
            self.config_manager
        )
