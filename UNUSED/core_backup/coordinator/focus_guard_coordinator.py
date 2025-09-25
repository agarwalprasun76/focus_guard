"""
Main coordinator implementation for the Focus Guard application.

This module provides the FocusGuardCoordinator class, which is responsible for
orchestrating all components of the Focus Guard application.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Set

from core_v2.coordinator.interfaces import Component, Coordinator, EventBus, EventListener, ComponentDependency
from core_v2.coordinator.lifecycle import ComponentLifecycleManager
from core_v2.coordinator.events import DefaultEventBus, EventTypes, ComponentEventData, ComponentErrorEventData
from core_v2.config.interfaces import ConfigurationManager


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
            return False
        
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
    
    async def _register_components(self) -> None:
        """
        Register all components with the lifecycle manager.
        
        This method creates and registers all the components that the coordinator
        will manage. The components are registered with their dependencies to
        ensure proper startup and shutdown order.
        """
        from core_v2.coordinator.components.config import ConfigComponent
        from core_v2.coordinator.components.activity import ActivityMonitorComponent
        from core_v2.coordinator.components.browser import BrowserIntegrationComponent
        from core_v2.coordinator.components.classification import DomainClassifierComponent
        from core_v2.coordinator.components.distraction import DistractionDetectorComponent
        from core_v2.coordinator.components.alert import AlertSystemComponent
        
        # Configuration component (always first)
        config_component = ConfigComponent(self.config_manager, self.event_bus)
        self.lifecycle_manager.register_component(config_component, [])
        
        # Activity monitoring
        activity_component = await self._create_activity_component()
        self.lifecycle_manager.register_component(
            activity_component,
            [ComponentDependency("config")]
        )
        
        # Browser detection and integration
        browser_component = await self._create_browser_component()
        self.lifecycle_manager.register_component(
            browser_component,
            [ComponentDependency("config")]
        )
        
        # Domain classification
        classifier_component = await self._create_classifier_component()
        self.lifecycle_manager.register_component(
            classifier_component,
            [ComponentDependency("config")]
        )
        
        # Distraction detection
        distraction_component = await self._create_distraction_component()
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
        self.lifecycle_manager.register_component(
            alert_component,
            [
                ComponentDependency("config"),
                ComponentDependency("distraction_detector")
            ]
        )
        
        # API server (if enabled)
        if self.config_manager.get("api_server.enabled", False):
            api_component = await self._create_api_component()
            self.lifecycle_manager.register_component(
                api_component,
                [ComponentDependency("config")]
            )
    
    async def _create_activity_component(self) -> Component:
        """
        Create and configure the activity monitor component.
        
        Returns:
            Component: The activity monitor component.
        """
        from core_v2.coordinator.components.activity import ActivityMonitorComponent
        from core_v2.activity.monitor import ActivityMonitor
        from core_v2.activity.platform import get_platform_implementation
        
        platform_impl = get_platform_implementation()
        activity_monitor = ActivityMonitor(platform_impl)
        
        return ActivityMonitorComponent(
            activity_monitor,
            self.event_bus,
            self.config_manager
        )
    
    async def _create_browser_component(self) -> Component:
        """
        Create and configure the browser integration component.
        
        Returns:
            Component: The browser integration component.
        """
        from core_v2.coordinator.components.browser import BrowserIntegrationComponent
        from core_v2.browser.integration import BrowserIntegration
        from core_v2.browser.tab_server import TabServer
        
        tab_server = TabServer()
        browser_integration = BrowserIntegration(tab_server)
        
        return BrowserIntegrationComponent(
            browser_integration,
            tab_server,
            self.event_bus,
            self.config_manager
        )
    
    async def _create_classifier_component(self) -> Component:
        """
        Create and configure the domain classifier component.
        
        Returns:
            Component: The domain classifier component.
        """
        from core_v2.coordinator.components.classification import DomainClassifierComponent
        from core_v2.classification.domain_classifier import StandardDomainClassifier
        
        domain_classifier = StandardDomainClassifier()
        
        return DomainClassifierComponent(
            domain_classifier,
            self.event_bus,
            self.config_manager
        )
    
    async def _create_distraction_component(self) -> Component:
        """
        Create and configure the distraction detector component.
        
        Returns:
            Component: The distraction detector component.
        """
        from core_v2.coordinator.components.distraction import DistractionDetectorComponent
        from core_v2.distraction.detector import DistractionDetector
        from core_v2.distraction.factory import DistractionDetectorFactory
        
        # Get the required components
        activity_component = self.get_component("activity_monitor")
        browser_component = self.get_component("browser_integration")
        classifier_component = self.get_component("domain_classifier")
        
        # Create the detector using the factory
        factory = DistractionDetectorFactory(self.config_manager)
        detector = factory.create_detector(
            activity_monitor=activity_component.get_activity_monitor(),
            browser_integration=browser_component.get_browser_integration(),
            domain_classifier=classifier_component.get_domain_classifier()
        )
        
        return DistractionDetectorComponent(
            detector,
            self.event_bus,
            self.config_manager
        )
    
    async def _create_alert_component(self) -> Component:
        """
        Create and configure the alert system component.
        
        Returns:
            Component: The alert system component.
        """
        from core_v2.coordinator.components.alert import AlertSystemComponent
        from core_v2.alert.system import AlertSystem
        from core_v2.alert.platform import get_platform_implementation
        
        platform_impl = get_platform_implementation()
        alert_system = AlertSystem(platform_impl)
        
        return AlertSystemComponent(
            alert_system,
            self.event_bus,
            self.config_manager
        )
    
    async def _create_api_component(self) -> Component:
        """
        Create and configure the API server component.
        
        Returns:
            Component: The API server component.
        """
        from core_v2.coordinator.components.api import ApiServerComponent
        from core_v2.api.server import ApiServer
        
        api_server = ApiServer()
        
        return ApiServerComponent(
            api_server,
            self.event_bus,
            self.config_manager
        )
