"""
Component lifecycle management for the Focus Guard coordinator.

This module provides functionality for managing the lifecycle of components,
including dependency resolution, startup/shutdown ordering, and error handling.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
import asyncio

from core_v2.coordinator.interfaces import Component, ComponentDependency


class DependencyError(Exception):
    """Exception raised for dependency resolution errors."""
    pass


class ComponentLifecycleManager:
    """
    Manages the lifecycle of components, including dependency resolution and ordering.
    
    This class is responsible for:
    1. Resolving component dependencies
    2. Determining the correct startup and shutdown order
    3. Managing the lifecycle state of components
    4. Handling errors during lifecycle operations
    """
    
    def __init__(self):
        """Initialize the component lifecycle manager."""
        self.components: Dict[str, Component] = {}
        self.dependencies: Dict[str, List[ComponentDependency]] = {}
        self.started_components: Set[str] = set()
        self.logger = logging.getLogger("focus_guard.coordinator.lifecycle")
    
    def register_component(self, component: Component, dependencies: List[ComponentDependency] = None) -> None:
        """
        Register a component with the lifecycle manager.
        
        Args:
            component (Component): The component to register.
            dependencies (List[ComponentDependency], optional): The component's dependencies.
                Defaults to None.
                
        Raises:
            ValueError: If a component with the same name is already registered.
        """
        if component.name in self.components:
            raise ValueError(f"Component '{component.name}' is already registered")
        
        self.components[component.name] = component
        self.dependencies[component.name] = dependencies or []
        self.logger.debug(f"Registered component: {component.name}")
    
    def get_component(self, name: str) -> Optional[Component]:
        """
        Get a component by name.
        
        Args:
            name (str): The name of the component.
            
        Returns:
            Optional[Component]: The component if found, None otherwise.
        """
        return self.components.get(name)
    
    def get_all_components(self) -> Dict[str, Component]:
        """
        Get all registered components.
        
        Returns:
            Dict[str, Component]: A dictionary of all registered components.
        """
        return self.components.copy()
    
    def resolve_dependencies(self) -> List[str]:
        """
        Resolve component dependencies and determine the startup order.
        
        Returns:
            List[str]: The names of components in the order they should be started.
            
        Raises:
            DependencyError: If there are circular dependencies or missing required dependencies.
        """
        # Check for missing required dependencies
        for component_name, deps in self.dependencies.items():
            for dep in deps:
                if dep.required and dep.component_name not in self.components:
                    raise DependencyError(
                        f"Component '{component_name}' requires '{dep.component_name}', "
                        f"but it is not registered"
                    )
        
        # Topological sort to determine startup order
        visited: Set[str] = set()
        temp_visited: Set[str] = set()
        order: List[str] = []
        
        def visit(name: str) -> None:
            if name in temp_visited:
                # Circular dependency detected
                cycle = " -> ".join(list(temp_visited) + [name])
                raise DependencyError(f"Circular dependency detected: {cycle}")
            
            if name not in visited:
                temp_visited.add(name)
                
                # Visit dependencies first
                for dep in self.dependencies.get(name, []):
                    if dep.component_name in self.components:
                        visit(dep.component_name)
                
                temp_visited.remove(name)
                visited.add(name)
                order.append(name)
        
        # Visit all components
        for name in self.components:
            if name not in visited:
                visit(name)
        
        # Reverse the order to get the correct startup sequence
        return list(reversed(order))
    
    async def initialize_all(self) -> bool:
        """
        Initialize all components in dependency order.
        
        Returns:
            bool: True if all components were initialized successfully, False otherwise.
        """
        try:
            order = self.resolve_dependencies()
        except DependencyError as e:
            self.logger.error(f"Failed to resolve dependencies: {e}")
            return False
        
        self.logger.info(f"Initializing components in order: {', '.join(order)}")
        
        for name in order:
            component = self.components[name]
            try:
                self.logger.debug(f"Initializing component: {name}")
                success = await component.initialize()
                if not success:
                    self.logger.error(f"Failed to initialize component: {name}")
                    return False
            except Exception as e:
                self.logger.exception(f"Error initializing component {name}: {e}")
                return False
        
        return True
    
    async def start_all(self) -> bool:
        """
        Start all components in dependency order.
        
        Returns:
            bool: True if all components were started successfully, False otherwise.
        """
        try:
            order = self.resolve_dependencies()
        except DependencyError as e:
            self.logger.error(f"Failed to resolve dependencies: {e}")
            return False
        
        self.logger.info(f"Starting components in order: {', '.join(order)}")
        
        for name in order:
            component = self.components[name]
            try:
                self.logger.debug(f"Starting component: {name}")
                success = await component.start()
                if not success:
                    self.logger.error(f"Failed to start component: {name}")
                    await self._stop_started_components()
                    return False
                self.started_components.add(name)
            except Exception as e:
                self.logger.exception(f"Error starting component {name}: {e}")
                await self._stop_started_components()
                return False
        
        return True
    
    async def stop_all(self) -> bool:
        """
        Stop all started components in reverse dependency order.
        
        Returns:
            bool: True if all components were stopped successfully, False otherwise.
        """
        return await self._stop_started_components()
    
    async def shutdown_all(self) -> bool:
        """
        Shutdown all components in reverse dependency order.
        
        Returns:
            bool: True if all components were shut down successfully, False otherwise.
        """
        if self.started_components:
            await self.stop_all()
        
        try:
            order = self.resolve_dependencies()
        except DependencyError as e:
            self.logger.error(f"Failed to resolve dependencies: {e}")
            return False
        
        # Shutdown in reverse order
        reverse_order = list(reversed(order))
        self.logger.info(f"Shutting down components in order: {', '.join(reverse_order)}")
        
        all_success = True
        for name in reverse_order:
            component = self.components[name]
            try:
                self.logger.debug(f"Shutting down component: {name}")
                success = await component.shutdown()
                if not success:
                    self.logger.error(f"Failed to shutdown component: {name}")
                    all_success = False
            except Exception as e:
                self.logger.exception(f"Error shutting down component {name}: {e}")
                all_success = False
        
        self.components.clear()
        self.dependencies.clear()
        self.started_components.clear()
        
        return all_success
    
    async def _stop_started_components(self) -> bool:
        """
        Stop all started components in reverse dependency order.
        
        Returns:
            bool: True if all components were stopped successfully, False otherwise.
        """
        try:
            order = self.resolve_dependencies()
        except DependencyError as e:
            self.logger.error(f"Failed to resolve dependencies: {e}")
            return False
        
        # Stop in reverse order
        reverse_order = list(reversed(order))
        self.logger.info(f"Stopping components in order: {', '.join(reverse_order)}")
        
        all_success = True
        for name in reverse_order:
            if name in self.started_components:
                component = self.components[name]
                try:
                    self.logger.debug(f"Stopping component: {name}")
                    success = await component.stop()
                    if not success:
                        self.logger.error(f"Failed to stop component: {name}")
                        all_success = False
                    self.started_components.remove(name)
                except Exception as e:
                    self.logger.exception(f"Error stopping component {name}: {e}")
                    all_success = False
                    if name in self.started_components:
                        self.started_components.remove(name)
        
        return all_success
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of all components.
        
        Returns:
            Dict[str, Any]: A dictionary containing the status of all components.
        """
        status = {
            "registered_components": list(self.components.keys()),
            "started_components": list(self.started_components),
            "components": {}
        }
        
        for name, component in self.components.items():
            try:
                component_status = component.get_status()
                status["components"][name] = component_status
            except Exception as e:
                self.logger.exception(f"Error getting status for component {name}: {e}")
                status["components"][name] = {"error": str(e)}
        
        return status
    
    def is_healthy(self) -> bool:
        """
        Check if all components are healthy.
        
        Returns:
            bool: True if all components are healthy, False otherwise.
        """
        for name, component in self.components.items():
            try:
                if not component.is_healthy():
                    self.logger.warning(f"Component {name} is not healthy")
                    return False
            except Exception as e:
                self.logger.exception(f"Error checking health for component {name}: {e}")
                return False
        
        return True
