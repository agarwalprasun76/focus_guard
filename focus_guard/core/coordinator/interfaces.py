"""
Core interfaces for the Focus Guard coordinator module.

This module defines the interfaces that all components must implement to be managed
by the coordinator. It establishes the contract for component lifecycle management,
health monitoring, and status reporting.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple


class Component(ABC):
    """Base interface for all coordinator-managed components."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the component name."""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the component.
        
        This method is called during the coordinator's initialization phase.
        Components should perform any setup tasks that don't require other
        components to be running.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """
        Start the component.
        
        This method is called during the coordinator's start phase.
        Components should begin active operations, such as starting threads,
        connecting to external services, etc.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """
        Stop the component.
        
        This method is called during the coordinator's stop phase.
        Components should cease active operations but maintain their state
        for a potential restart.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """
        Shutdown the component.
        
        This method is called during the coordinator's shutdown phase.
        Components should release all resources and perform final cleanup.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the component status.
        
        Returns:
            Dict[str, Any]: A dictionary containing the component's status information.
        """
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if the component is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        pass


class ComponentDependency:
    """
    Represents a dependency between components.
    
    This class is used to define the dependencies between components,
    which the coordinator uses to determine the correct startup and
    shutdown order.
    """
    
    def __init__(self, component_name: str, required: bool = True):
        """
        Initialize a component dependency.
        
        Args:
            component_name (str): The name of the required component.
            required (bool, optional): Whether this dependency is required.
                If True, the coordinator will fail if the dependency cannot be satisfied.
                If False, the coordinator will continue even if the dependency is missing.
                Defaults to True.
        """
        self.component_name = component_name
        self.required = required


class EventListener(ABC):
    """Base interface for event listeners."""
    
    @abstractmethod
    async def on_event(self, event_type: str, event_data: Any) -> None:
        """
        Handle an event.
        
        Args:
            event_type (str): The type of event.
            event_data (Any): The event data.
        """
        pass


class EventBus(ABC):
    """Interface for the event bus."""
    
    @abstractmethod
    async def publish(self, event_type: str, event_data: Any) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type (str): The type of event.
            event_data (Any): The event data.
        """
        pass
    
    @abstractmethod
    def subscribe(self, event_type: str, listener: EventListener) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type (str): The type of event to subscribe to.
            listener (EventListener): The listener to notify when the event occurs.
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: str, listener: EventListener) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type (str): The type of event to unsubscribe from.
            listener (EventListener): The listener to remove.
        """
        pass


class Coordinator(ABC):
    """Interface for the coordinator."""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the coordinator and all components.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """
        Start the coordinator and all components.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """
        Stop the coordinator and all components.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """
        Shutdown the coordinator and all components.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the coordinator and all components.
        
        Returns:
            Dict[str, Any]: A dictionary containing the coordinator's status information.
        """
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if the coordinator and all components are healthy.
        
        Returns:
            bool: True if the coordinator and all components are healthy, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_component(self, name: str) -> Optional[Component]:
        """
        Get a component by name.
        
        Args:
            name (str): The name of the component.
            
        Returns:
            Optional[Component]: The component if found, None otherwise.
        """
        pass
