"""
Tests for the coordinator lifecycle management using pytest-asyncio.

This module tests the lifecycle management implementation in the coordinator module
using modern pytest-asyncio framework.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from core_v2.coordinator.lifecycle import ComponentLifecycleManager
from core_v2.coordinator.interfaces import Component


class MockComponent:
    """Mock implementation of the Component interface."""
    
    def __init__(self, name="mock_component"):
        self._name = name
        self.initialize = AsyncMock(return_value=True)
        self.start = AsyncMock(return_value=True)
        self.stop = AsyncMock(return_value=True)
        self.shutdown = AsyncMock(return_value=True)
        self.get_status = Mock(return_value={"status": "ok"})
        self.is_healthy = Mock(return_value=True)
    
    @property
    def name(self):
        """Get the component name."""
        return self._name


class TestComponentLifecycleManagerPytest:
    """Test cases for the ComponentLifecycleManager class using pytest-asyncio."""
    
    @pytest.fixture
    def lifecycle_manager(self):
        """Create a fresh lifecycle manager for each test."""
        return ComponentLifecycleManager()
    
    @pytest.fixture
    def component1(self):
        """Create mock component 1."""
        return MockComponent(name="component1")
    
    @pytest.fixture
    def component2(self):
        """Create mock component 2."""
        return MockComponent(name="component2")
    
    def test_register_component(self, lifecycle_manager, component1, component2):
        """Test registering components."""
        # Register components
        lifecycle_manager.register_component(component1)
        lifecycle_manager.register_component(component2)
        
        # Check that the components are registered
        assert component1 in lifecycle_manager.components.values()
        assert component2 in lifecycle_manager.components.values()
    
    def test_register_duplicate_component(self, lifecycle_manager, component1):
        """Test registering a component with a duplicate name."""
        # Register a component
        lifecycle_manager.register_component(component1)
        
        # Register another component with the same name
        component_duplicate = MockComponent(name="component1")
        with pytest.raises(ValueError):
            lifecycle_manager.register_component(component_duplicate)
    
    def test_get_component(self, lifecycle_manager, component1):
        """Test getting a registered component."""
        # Register a component
        lifecycle_manager.register_component(component1)
        
        # Get the component
        component = lifecycle_manager.get_component("component1")
        
        # Check that the correct component is returned
        assert component == component1
    
    def test_get_nonexistent_component(self, lifecycle_manager):
        """Test getting a component that is not registered."""
        # Try to get a component that is not registered
        component = lifecycle_manager.get_component("nonexistent")
        assert component is None
    
    @pytest.mark.asyncio
    async def test_initialize_components(self, lifecycle_manager, component1, component2):
        """Test initializing components."""
        # Register components
        lifecycle_manager.register_component(component1)
        lifecycle_manager.register_component(component2)
        
        # Initialize components
        result = await lifecycle_manager.initialize_all()
        
        # Check that initialization was successful
        assert result is True
        
        # Check that the components were initialized
        component1.initialize.assert_called_once()
        component2.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_components_failure(self, lifecycle_manager, component1, component2):
        """Test initializing components where one fails."""
        # Register components
        lifecycle_manager.register_component(component1)
        component2.initialize.return_value = False
        lifecycle_manager.register_component(component2)
        
        # Initialize components
        result = await lifecycle_manager.initialize_all()
        
        # Check that initialization failed
        assert result is False
        
        # Check which components were actually initialized based on dependency order
        # The actual order depends on dependency resolution, so we check both
        # but expect component2 (the failing one) to be called
        component2.initialize.assert_called()
    
    @pytest.mark.asyncio
    async def test_start_components(self, lifecycle_manager, component1, component2):
        """Test starting components."""
        # Register components
        lifecycle_manager.register_component(component1)
        lifecycle_manager.register_component(component2)
        
        # Initialize components first
        await lifecycle_manager.initialize_all()
        
        # Start components
        result = await lifecycle_manager.start_all()
        
        # Check that starting was successful
        assert result is True
        
        # Check that the components were started
        component1.start.assert_called_once()
        component2.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_components_failure(self, lifecycle_manager, component1, component2):
        """Test starting components where one fails."""
        # Register components
        lifecycle_manager.register_component(component1)
        component2.start.return_value = False
        lifecycle_manager.register_component(component2)
        
        # Initialize components first
        await lifecycle_manager.initialize_all()
        
        # Start components
        result = await lifecycle_manager.start_all()
        
        # Check that starting failed
        assert result is False
        
        # Check which components were actually started based on dependency order
        # The actual order depends on dependency resolution
        component2.start.assert_called()
    
    @pytest.mark.asyncio
    async def test_stop_components(self, lifecycle_manager, component1, component2):
        """Test stopping components."""
        # Register components
        lifecycle_manager.register_component(component1)
        lifecycle_manager.register_component(component2)
        
        # Initialize and start components first
        await lifecycle_manager.initialize_all()
        await lifecycle_manager.start_all()
        
        # Stop components
        result = await lifecycle_manager.stop_all()
        
        # Check that stopping was successful
        assert result is True
        
        # Check that the components were stopped
        component1.stop.assert_called_once()
        component2.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_components_failure(self, lifecycle_manager, component1, component2):
        """Test stopping components where one fails."""
        # Register components
        lifecycle_manager.register_component(component1)
        component2.stop.return_value = False
        lifecycle_manager.register_component(component2)
        
        # Initialize and start components first
        await lifecycle_manager.initialize_all()
        await lifecycle_manager.start_all()
        
        # Stop components
        result = await lifecycle_manager.stop_all()
        
        # Check that stopping failed
        assert result is False
        
        # Check that both components were still stopped
        component1.stop.assert_called()
        component2.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_components(self, lifecycle_manager, component1, component2):
        """Test shutting down components."""
        # Register components
        lifecycle_manager.register_component(component1)
        lifecycle_manager.register_component(component2)
        
        # Shutdown components
        result = await lifecycle_manager.shutdown_all()
        
        # Check that shutdown was successful
        assert result is True
        
        # Check that the components were shut down
        component1.shutdown.assert_called_once()
        component2.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_components_failure(self, lifecycle_manager, component1, component2):
        """Test shutting down components where one fails."""
        # Register components
        lifecycle_manager.register_component(component1)
        component2.shutdown.return_value = False
        lifecycle_manager.register_component(component2)
        
        # Shutdown components
        result = await lifecycle_manager.shutdown_all()
        
        # Check that shutdown failed
        assert result is False
        
        # Check that both components were still shut down
        component1.shutdown.assert_called()
        component2.shutdown.assert_called_once()
    
    def test_get_component_status(self, lifecycle_manager, component1, component2):
        """Test getting component status."""
        # Register components
        lifecycle_manager.register_component(component1)
        lifecycle_manager.register_component(component2)
        
        # Get component status
        status = lifecycle_manager.get_status()
        
        # Check that the status includes both components
        assert "component1" in status["components"]
        assert "component2" in status["components"]
        
        # Check that the status values are correct
        assert status["components"]["component1"] == {"status": "ok"}
        assert status["components"]["component2"] == {"status": "ok"}
    
    def test_is_healthy(self, lifecycle_manager, component1, component2):
        """Test checking if all components are healthy."""
        # Register components
        lifecycle_manager.register_component(component1)
        lifecycle_manager.register_component(component2)
        
        # Check health
        health = lifecycle_manager.is_healthy()
        
        # Check that health is reported as good
        assert health is True
    
    def test_is_healthy_with_unhealthy_component(self, lifecycle_manager, component1, component2):
        """Test checking health with an unhealthy component."""
        # Register components
        lifecycle_manager.register_component(component1)
        component2.is_healthy.return_value = False
        lifecycle_manager.register_component(component2)
        
        # Check health
        health = lifecycle_manager.is_healthy()
        
        # Check that health is reported as bad
        assert health is False
