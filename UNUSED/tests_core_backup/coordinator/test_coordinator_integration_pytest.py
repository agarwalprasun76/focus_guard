"""
Integration tests for the Focus Guard Coordinator using pytest-asyncio.

This module tests the interaction between multiple components through the coordinator
using modern pytest-asyncio framework.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from core_v2.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from core_v2.coordinator.lifecycle import ComponentLifecycleManager
from core_v2.coordinator.interfaces import Component
from core_v2.coordinator.components.base import BaseComponent
from core_v2.coordinator.events import DefaultEventBus, EventTypes, EventData
from core_v2.coordinator.components.config import ConfigComponent
from core_v2.coordinator.components.activity import ActivityMonitorComponent
from core_v2.coordinator.components.browser import BrowserIntegrationComponent
from core_v2.coordinator.components.classification import ClassificationComponent
from core_v2.coordinator.components.distraction import DistractionDetectorComponent
from core_v2.coordinator.components.alert import AlertSystemComponent
from core_v2.coordinator.components.api import ApiServerComponent


class MockComponent(BaseComponent):
    """Mock component for testing."""
    
    def __init__(self, name, event_bus, config_manager=None):
        super().__init__(name, event_bus, config_manager)
        self.initialize_called = False
        self.start_called = False
        self.stop_called = False
        self.shutdown_called = False
        self.event_received = False
        self.last_event_type = None
        self.last_event_data = None
        self._is_healthy = True
    
    async def _initialize_component(self):
        self.initialize_called = True
        return True
    
    async def _start_component(self):
        self.start_called = True
        return True
    
    async def _stop_component(self):
        self.stop_called = True
        return True
    
    async def _shutdown_component(self):
        self.shutdown_called = True
        return True
    
    def _get_component_status(self):
        return {
            "status": "mock",
            "initialized": self.initialize_called,
            "started": self.start_called
        }
    
    def _is_component_healthy(self):
        return self._is_healthy
        
    def on_event(self, event_type, event_data):
        """Handle events directly."""
        self.event_received = True
        self.last_event_type = event_type
        self.last_event_data = event_data


@pytest.fixture
def config_manager():
    """Fixture providing a mock config manager."""
    config_manager = Mock()
    config_manager.get = Mock(return_value=None)
    return config_manager


@pytest.fixture
def coordinator(config_manager):
    """Fixture providing a FocusGuardCoordinator instance."""
    return FocusGuardCoordinator(config_manager)


@pytest.fixture
def event_bus(coordinator):
    """Fixture providing access to the event bus."""
    return coordinator.event_bus


@pytest.fixture
def mock_component(event_bus, config_manager):
    """Fixture providing a MockComponent instance."""
    return MockComponent("test_component", event_bus, config_manager)


@pytest.mark.asyncio
async def test_component_registration(coordinator, mock_component):
    """Test that components are registered correctly."""
    # Register the mock component
    coordinator.lifecycle_manager.register_component(mock_component)
    
    # Check that our test component is registered
    assert "test_component" in coordinator.lifecycle_manager.get_all_components()
    
    # Check that the component can be retrieved by name
    assert coordinator.lifecycle_manager.get_component("test_component") == mock_component


@pytest.mark.asyncio
async def test_coordinator_lifecycle(coordinator, mock_component):
    """Test the coordinator lifecycle."""
    # Register the mock component
    coordinator.lifecycle_manager.register_component(mock_component)
    
    # Initialize the coordinator
    result = await coordinator.lifecycle_manager.initialize_all()
    assert result is True
    
    # Verify that our test component was initialized
    assert mock_component.initialize_called is True
    
    # Start the coordinator
    result = await coordinator.lifecycle_manager.start_all()
    assert result is True
    
    # Verify that our test component was started
    assert mock_component.start_called is True
    
    # Stop the coordinator
    result = await coordinator.lifecycle_manager.stop_all()
    assert result is True
    
    # Verify that our test component was stopped
    assert mock_component.stop_called is True
    
    # Shutdown the coordinator
    result = await coordinator.lifecycle_manager.shutdown_all()
    assert result is True
    
    # Verify that our test component was shut down
    assert mock_component.shutdown_called is True


@pytest.mark.asyncio
async def test_event_propagation(coordinator, mock_component):
    """Test event propagation through the coordinator."""
    # Register the mock component
    coordinator.lifecycle_manager.register_component(mock_component)
    
    # Initialize and start the coordinator
    await coordinator.lifecycle_manager.initialize_all()
    await coordinator.lifecycle_manager.start_all()
    
    # Reset event flags
    mock_component.event_received = False
    mock_component.last_event_type = None
    mock_component.last_event_data = None
    
    # Define a test event type and data
    test_event_type = "TEST_EVENT"
    test_event = {"source": "test", "data": "test_data"}
    
    # Use a simple callback to track events
    event_received = False
    last_event_type = None
    last_event_data = None

    def event_handler(event_type, event_data):
        nonlocal event_received, last_event_type, last_event_data
        event_received = True
        last_event_type = event_type
        last_event_data = event_data

    coordinator.event_bus.subscribe(test_event_type, event_handler)

    # Publish the test event
    await coordinator.event_bus.publish(test_event_type, test_event)

    # Give a small delay for event processing
    await asyncio.sleep(0.01)

    # Check that our event handler received the event
    assert event_received is True
    assert last_event_type == test_event_type
    assert last_event_data == test_event


@pytest.mark.asyncio
async def test_component_health_check(coordinator, mock_component):
    """Test component health checks."""
    # Register the mock component
    coordinator.lifecycle_manager.register_component(mock_component)
    
    # Initialize and start the coordinator
    await coordinator.lifecycle_manager.initialize_all()
    await coordinator.lifecycle_manager.start_all()
    
    # Check component health
    health_status = coordinator.lifecycle_manager.is_healthy()
    
    # Check that all components are healthy
    assert health_status is True
    
    # Test unhealthy component
    mock_component._is_healthy = False
    health_status = coordinator.lifecycle_manager.is_healthy()
    assert health_status is False


@pytest.mark.asyncio
async def test_component_status(coordinator, mock_component):
    """Test getting component status."""
    # Register the mock component
    coordinator.lifecycle_manager.register_component(mock_component)
    
    # Start the coordinator
    await coordinator.lifecycle_manager.start_all()
    
    # Get the coordinator status
    status = coordinator.lifecycle_manager.get_status()
    
    # Check the status structure
    assert "registered_components" in status
    assert "started_components" in status
    assert "components" in status
    
    # Check that our test component is registered
    assert "test_component" in status["registered_components"]
    
    # Check that our test component status is included
    test_component_status = status["components"]["test_component"]
    assert "status" in test_component_status
    assert "initialized" in test_component_status
    assert "started" in test_component_status


@pytest.mark.asyncio
async def test_end_to_end_workflow(coordinator, mock_component):
    """Test an end-to-end workflow through the coordinator."""
    # Register the mock component
    coordinator.lifecycle_manager.register_component(mock_component)
    
    # Initialize and start the coordinator
    await coordinator.lifecycle_manager.initialize_all()
    await coordinator.lifecycle_manager.start_all()
    
    # Reset event flags
    mock_component.event_received = False
    mock_component.last_event_type = None
    mock_component.last_event_data = None
    
    # Define a test event type and data
    test_event_type = "TEST_EVENT"
    test_event = {"source": "test_source", "data": "test_data"}

    # Use a simple callback to track events
    event_received = False
    last_event_type = None
    last_event_data = None

    def event_handler(event_type, event_data):
        nonlocal event_received, last_event_type, last_event_data
        event_received = True
        last_event_type = event_type
        last_event_data = event_data

    coordinator.event_bus.subscribe(test_event_type, event_handler)

    # Publish the test event
    await coordinator.event_bus.publish(test_event_type, test_event)

    # Give a small delay for event processing
    await asyncio.sleep(0.01)

    # Check that our event handler received the event
    assert event_received is True
    assert last_event_type == test_event_type
    assert last_event_data == test_event
    
    # Test another event type
    mock_component.event_received = False
    mock_component.last_event_type = None
    mock_component.last_event_data = None
    # Define another test event type and data
    another_event_type = "ANOTHER_TEST_EVENT"
    another_event = {"source": "another_source", "data": "another_data"}
    
    # Use a simple function callback to track events
    another_event_received = False
    another_last_event_type = None
    another_last_event_data = None

    def another_event_handler(event_type, event_data):
        nonlocal another_event_received, another_last_event_type, another_last_event_data
        another_event_received = True
        another_last_event_type = event_type
        another_last_event_data = event_data

    coordinator.event_bus.subscribe(another_event_type, another_event_handler)

    # Publish the test event
    await coordinator.event_bus.publish(another_event_type, another_event)
    
    # Give a small delay for event processing
    await asyncio.sleep(0.01)
    
    # Check that our event handler received the event
    assert another_event_received is True
    assert another_last_event_type == another_event_type
    assert another_last_event_data == another_event
    
    # Test stopping and shutting down the coordinator
    result = await coordinator.lifecycle_manager.stop_all()
    assert result is True
    
    result = await coordinator.lifecycle_manager.shutdown_all()
    assert result is True
    
    # Verify that our mock component was stopped and shut down
    assert mock_component.stop_called is True
    assert mock_component.shutdown_called is True


@pytest.mark.asyncio
async def test_multiple_lifecycle_operations(coordinator, mock_component):
    """Test multiple lifecycle operations in sequence."""
    # Register the mock component
    coordinator.lifecycle_manager.register_component(mock_component)
    
    # Test complete lifecycle
    assert await coordinator.lifecycle_manager.initialize_all() is True
    assert await coordinator.lifecycle_manager.start_all() is True
    
    # Test restart sequence
    assert await coordinator.lifecycle_manager.stop_all() is True
    assert await coordinator.lifecycle_manager.start_all() is True
    
    # Test shutdown
    assert await coordinator.lifecycle_manager.shutdown_all() is True
    
    # Verify final state
    assert mock_component.initialize_called is True
    assert mock_component.start_called is True
    assert mock_component.stop_called is True
    assert mock_component.shutdown_called is True


@pytest.mark.asyncio
async def test_status_consistency(coordinator, mock_component):
    """Test status reporting consistency across lifecycle states."""
    # Register the mock component
    coordinator.lifecycle_manager.register_component(mock_component)
    
    # Before initialization
    status = coordinator.lifecycle_manager.get_status()
    assert "registered_components" in status
    assert "started_components" in status
    assert "components" in status
    
    # After initialization
    await coordinator.lifecycle_manager.initialize_all()
    status = coordinator.lifecycle_manager.get_status()
    assert "registered_components" in status
    assert "started_components" in status
    assert "components" in status
    
    # After start
    await coordinator.lifecycle_manager.start_all()
    status = coordinator.lifecycle_manager.get_status()
    assert "registered_components" in status
    assert "started_components" in status
    assert "components" in status
    
    # After shutdown
    await coordinator.lifecycle_manager.shutdown_all()
    status = coordinator.lifecycle_manager.get_status()
    assert "registered_components" in status
    assert "started_components" in status
    assert "components" in status


@pytest.mark.asyncio
async def test_get_nonexistent_component(coordinator):
    """Test getting a component that is not registered."""
    # Try to get a component that is not registered
    component = coordinator.get_component("nonexistent")
    assert component is None


@pytest.mark.asyncio
async def test_get_event_bus(coordinator):
    """Test getting the event bus."""
    # Get the event bus directly from the property
    event_bus = coordinator.event_bus
    
    # Check that the correct event bus is returned
    assert isinstance(event_bus, DefaultEventBus)
    assert event_bus is not None


@pytest.mark.asyncio
async def test_is_healthy_with_unhealthy_component(coordinator, mock_component):
    """Test checking health with an unhealthy component."""
    # Register the mock component
    coordinator.lifecycle_manager.register_component(mock_component)
    
    # Make the component unhealthy
    mock_component._is_healthy = False
    
    # Check health (is_healthy is synchronous)
    health = coordinator.lifecycle_manager.is_healthy()
    
    # Check that health is reported as bad
    assert health is False
