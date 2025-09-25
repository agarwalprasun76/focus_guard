"""
Tests for the coordinator interfaces using pytest.

This module tests the core interfaces defined in the coordinator module
using modern pytest framework.
"""

import pytest

from focus_guard.core.coordinator.interfaces import Component, EventBus, EventListener, Coordinator


class TestComponentInterfacePytest:
    """Test cases for the Component interface using pytest."""
    
    def test_component_interface(self):
        """Test that the Component interface has the expected methods."""
        # Check that the Component interface has the expected methods
        assert hasattr(Component, "initialize")
        assert hasattr(Component, "start")
        assert hasattr(Component, "stop")
        assert hasattr(Component, "shutdown")
        assert hasattr(Component, "get_status")
        assert hasattr(Component, "is_healthy")
        assert hasattr(Component, "name")


class TestEventBusInterfacePytest:
    """Test cases for the EventBus interface using pytest."""
    
    def test_event_bus_interface(self):
        """Test that the EventBus interface has the expected methods."""
        # Check that the EventBus interface has the expected methods
        assert hasattr(EventBus, "publish")
        assert hasattr(EventBus, "subscribe")
        assert hasattr(EventBus, "unsubscribe")


class TestEventListenerInterfacePytest:
    """Test cases for the EventListener interface using pytest."""
    
    def test_event_listener_interface(self):
        """Test that the EventListener interface has the expected methods."""
        # Check that the EventListener interface has the expected methods
        assert hasattr(EventListener, "on_event")


class TestCoordinatorInterfacePytest:
    """Test cases for the Coordinator interface using pytest."""
    
    def test_coordinator_interface(self):
        """Test that the Coordinator interface has the expected methods."""
        # Check that the Coordinator interface has the expected methods
        assert hasattr(Coordinator, "initialize")
        assert hasattr(Coordinator, "start")
        assert hasattr(Coordinator, "stop")
        assert hasattr(Coordinator, "shutdown")
        assert hasattr(Coordinator, "get_status")
        assert hasattr(Coordinator, "is_healthy")
        # register_component is not part of the interface but implemented in FocusGuardCoordinator
        assert hasattr(Coordinator, "get_component")
        # get_event_bus is not part of the interface but implemented in FocusGuardCoordinator
