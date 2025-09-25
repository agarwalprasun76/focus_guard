"""
Complete pytest-asyncio tests for BaseComponent.

This module provides comprehensive async tests for the BaseComponent
using pytest-asyncio with AsyncMock for cleaner async testing.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from focus_guard.core.coordinator.components.base import BaseComponent
from focus_guard.core.coordinator.events import EventTypes, EventData
from focus_guard.core.config.interfaces import ConfigurationManager


@pytest.mark.asyncio
class TestBaseComponentPytest:
    """Complete async tests for BaseComponent using pytest-asyncio."""
    
    @pytest.fixture
    def config_manager(self):
        """Create mock configuration manager."""
        manager = MagicMock(spec=ConfigurationManager)
        
        # Mock configuration methods
        manager.get = MagicMock()
        manager.get.side_effect = lambda path, default=None: default
        manager.set = MagicMock(return_value=True)
        manager.has = MagicMock(return_value=False)
        manager.delete = MagicMock(return_value=True)
        manager.clear = MagicMock(return_value=True)
        manager.all_paths = MagicMock(return_value=[])
        
        return manager
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        bus = MagicMock()
        bus.subscribe = AsyncMock()
        bus.publish = AsyncMock()
        bus.unsubscribe = AsyncMock()
        return bus
    
    @pytest.fixture
    def component(self, event_bus, config_manager):
        """Create BaseComponent instance with mocked dependencies."""
        
        class ConcreteComponent(BaseComponent):
            """Concrete implementation of BaseComponent for testing."""
            
            def __init__(self, name, event_bus, config_manager):
                super().__init__(name, event_bus, config_manager)
                self._initialize_component_called = False
                self._start_component_called = False
                self._stop_component_called = False
                self._shutdown_component_called = False
                self._get_component_status_called = False
                self._is_component_healthy_called = False
                self._handle_config_changed_called = False
                self._handle_config_changed_event_data = None
            
            async def _initialize_component(self):
                self._initialize_component_called = True
                return True
            
            async def _start_component(self):
                self._start_component_called = True
                return True
            
            async def _stop_component(self):
                self._stop_component_called = True
                return True
            
            async def _shutdown_component(self):
                self._shutdown_component_called = True
                return True
            
            def _get_component_status(self):
                self._get_component_status_called = True
                return {"status": "ok", "test": True}
            
            def _is_component_healthy(self):
                self._is_component_healthy_called = True
                return True
            
            async def _handle_config_changed(self, event_data):
                self._handle_config_changed_called = True
                self._handle_config_changed_event_data = event_data
        
        return ConcreteComponent("test_component", event_bus, config_manager)
    
    async def test_initialization(self, component, event_bus, config_manager):
        """Test that the component is initialized correctly."""
        assert component.name == "test_component"
        assert component._event_bus == event_bus
        assert component._config_manager == config_manager
        assert component._logger is not None
    
    async def test_initialize(self, component):
        """Test initializing the component."""
        result = await component.initialize()
        assert result is True
        assert component._initialize_component_called is True
        assert component._initialized is True
    
    async def test_start(self, component):
        """Test starting the component."""
        await component.initialize()
        result = await component.start()
        assert result is True
        assert component._start_component_called is True
        assert component._running is True
    
    async def test_stop(self, component):
        """Test stopping the component."""
        await component.initialize()
        await component.start()
        
        result = await component.stop()
        assert result is True
        assert component._stop_component_called is True
        assert component._running is False
    
    async def test_shutdown(self, component):
        """Test shutting down the component."""
        await component.initialize()
        
        result = await component.shutdown()
        assert result is True
        assert component._shutdown_component_called is True
        assert component._initialized is False
    
    async def test_get_status(self, component):
        """Test getting the component status."""
        status = component.get_status()
        assert isinstance(status, dict)
        assert status["name"] == "test_component"
        assert status["status"] == "ok"
        assert component._get_component_status_called is True
    
    async def test_is_healthy(self, component):
        """Test checking if the component is healthy."""
        await component.initialize()
        await component.start()
        
        health = component.is_healthy()
        assert health is True
        assert component._is_component_healthy_called is True
    
    async def test_on_event_config_changed(self, component):
        """Test handling configuration change events."""
        await component.initialize()
        
        # Create configuration change event data
        class MockConfigChangedEventData:
            def __init__(self):
                self.path = "test.path"
                self.new_value = "test_value"
        
        event_data = MockConfigChangedEventData()
        
        await component.on_event(EventTypes.CONFIG_CHANGED, event_data)
        assert component._handle_config_changed_called is True
        assert component._handle_config_changed_event_data == event_data
    
    async def test_on_event_unknown_type(self, component):
        """Test handling unknown event types."""
        await component.initialize()
        
        # Create unknown event data
        class MockUnknownEventData:
            def __init__(self):
                self.source = "test_source"
        
        event_data = MockUnknownEventData()
        
        # Should not raise an exception
        await component.on_event("UNKNOWN_EVENT_TYPE", event_data)
        assert component._handle_config_changed_called is False
    
    async def test_multiple_lifecycle_operations(self, component):
        """Test multiple lifecycle operations in sequence."""
        # Initialize
        result = await component.initialize()
        assert result is True
        assert component._initialized is True
        
        # Start
        result = await component.start()
        assert result is True
        assert component._running is True
        
        # Stop
        result = await component.stop()
        assert result is True
        assert component._running is False
        
        # Start again
        result = await component.start()
        assert result is True
        assert component._running is True
        
        # Shutdown
        result = await component.shutdown()
        assert result is True
        assert component._initialized is False
    
    async def test_status_consistency(self, component):
        """Test status reporting consistency across lifecycle."""
        # Before initialization
        status = component.get_status()
        assert status["name"] == "test_component"
        assert status["initialized"] is False
        assert status["running"] is False
        
        # After initialization
        await component.initialize()
        status = component.get_status()
        assert status["initialized"] is True
        assert status["running"] is False
        
        # After start
        await component.start()
        status = component.get_status()
        assert status["initialized"] is True
        assert status["running"] is True
        
        # After stop
        await component.stop()
        status = component.get_status()
        assert status["initialized"] is True
        assert status["running"] is False
        
        # After shutdown
        await component.shutdown()
        status = component.get_status()
        assert status["initialized"] is False
        assert status["running"] is False
