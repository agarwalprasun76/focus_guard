"""
Tests for the configuration component wrapper using pytest-asyncio.

This module tests the configuration component implementation in the coordinator module
using modern pytest-asyncio framework.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from core_v2.coordinator.components.config import ConfigComponent, ConfigChangedEventData
from core_v2.coordinator.events import DefaultEventBus, EventTypes
from core_v2.config.interfaces import ConfigurationManager


class MockConfigManager(Mock):
    """Mock implementation of the ConfigurationManager interface."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config_data = {}
        self.get = Mock(side_effect=self._mock_get)
        self.set = Mock(side_effect=self._mock_set)
        self.delete = Mock(return_value=True)
        self.has = Mock(side_effect=self._mock_has)
        self.clear = Mock(return_value=True)
        self.all_paths = Mock(return_value=list(self._config_data.keys()))
        self.add_change_listener = Mock()
        self.remove_change_listener = Mock()
        self.get_providers = Mock(return_value=[])
    
    def _mock_get(self, path, default=None):
        """Mock implementation of get."""
        return self._config_data.get(path, default)
    
    def _mock_set(self, path, value):
        """Mock implementation of set."""
        self._config_data[path] = value
        return True
    
    def _mock_has(self, path):
        """Mock implementation of has."""
        return path in self._config_data


@pytest.fixture
def event_bus():
    """Fixture providing a DefaultEventBus instance."""
    return DefaultEventBus()


@pytest.fixture
def config_manager():
    """Fixture providing a MockConfigManager instance."""
    return MockConfigManager()


@pytest.fixture
def component(config_manager, event_bus):
    """Fixture providing a ConfigComponent instance."""
    return ConfigComponent(config_manager, event_bus)


@pytest.mark.asyncio
async def test_initialization(config_manager, event_bus):
    """Test that the component is initialized correctly."""
    component = ConfigComponent(config_manager, event_bus)
    
    # Check that the component has the correct name
    assert component.name == "config"
    
    # Check that the component has an event bus
    assert component._event_bus == event_bus
    
    # Check that the component has a config manager
    assert component._config_manager == config_manager


@pytest.mark.asyncio
async def test_initialize(config_manager, component):
    """Test initializing the component."""
    # Initialize the component
    result = await component.initialize()
    
    # Check that initialization was successful
    assert result is True
    
    # Check that the component registered a change listener
    config_manager.add_change_listener.assert_called_once()


@pytest.mark.asyncio
async def test_start(config_manager, component):
    """Test starting the component."""
    # Initialize first
    await component.initialize()
    
    # Start the component
    result = await component.start()
    
    # Check that startup was successful
    assert result is True


@pytest.mark.asyncio
async def test_stop(config_manager, component):
    """Test stopping the component."""
    # Initialize and start first
    await component.initialize()
    await component.start()
    component._running = True
    
    # Stop the component
    result = await component.stop()
    
    # Check that stopping was successful
    assert result is True


@pytest.mark.asyncio
async def test_shutdown(config_manager, component):
    """Test shutting down the component."""
    # Initialize first
    await component.initialize()
    
    # Shutdown the component
    result = await component.shutdown()
    
    # Check that shutdown was successful
    assert result is True
    
    # Check that the component removed the change listener
    config_manager.remove_change_listener.assert_called_once()


@pytest.mark.asyncio
async def test_get_status(config_manager, component):
    """Test getting the component status."""
    # Get the component status
    status = component.get_status()
    
    # Check that the status includes the expected fields
    assert "config_paths" in status
    assert "providers" in status


@pytest.mark.asyncio
async def test_is_healthy(config_manager, component):
    """Test checking if the component is healthy."""
    # Initialize and start first
    await component.initialize()
    await component.start()
    component._running = True
    
    # Check health
    health = component.is_healthy()
    
    # Check that health is reported as good
    assert health is True


@pytest.mark.asyncio
async def test_on_config_changed(config_manager, event_bus, component):
    """Test handling configuration changes."""
    # Initialize the component
    await component.initialize()
    
    # Verify that a change listener was registered
    assert config_manager.add_change_listener.called
    
    # Get the change listener callback
    change_listener = config_manager.add_change_listener.call_args[0][0]
    
    # Test the change listener directly
    path = "test.path"
    old_value = "old_value"
    new_value = "new_value"
    
    # Create a mock for the event bus publish method
    with patch.object(event_bus, 'publish') as mock_publish:
        # Call the change listener
        change_listener(path, old_value, new_value)
        
        # Verify that publish was called with the correct arguments
        mock_publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_publish.call_args[0]
        event_type, event_data = call_args
        
        # Check that the event type is correct
        assert event_type == EventTypes.CONFIG_CHANGED
        
        # Check that the event data is correct
        assert isinstance(event_data, ConfigChangedEventData)
        assert event_data.path == path
        assert event_data.old_value == old_value
        assert event_data.new_value == new_value


@pytest.mark.asyncio
async def test_config_changed_event_data():
    """Test the ConfigChangedEventData class."""
    # Create event data
    source = "test_source"
    path = "test.path"
    old_value = "old_value"
    new_value = "new_value"
    event_data = ConfigChangedEventData(source, path, old_value, new_value)
    
    # Check that the event data has the correct values
    assert event_data.source == source
    assert event_data.path == path
    assert event_data.old_value == old_value
    assert event_data.new_value == new_value
    
    # Check that the event data can be converted to a dictionary
    data_dict = event_data.to_dict()
    assert data_dict["source"] == source
    assert data_dict["path"] == path
    assert data_dict["old_value"] == old_value
    assert data_dict["new_value"] == new_value


@pytest.mark.asyncio
async def test_multiple_lifecycle_operations(config_manager, event_bus):
    """Test multiple lifecycle operations in sequence."""
    component = ConfigComponent(config_manager, event_bus)
    
    # Test complete lifecycle
    assert await component.initialize() is True
    assert await component.start() is True
    assert component.is_healthy() is True
    
    # Test restart sequence
    assert await component.stop() is True
    assert await component.start() is True
    assert component.is_healthy() is True
    
    # Test shutdown
    assert await component.shutdown() is True
    
    # Verify final state
    assert component._running is False
    config_manager.remove_change_listener.assert_called()


@pytest.mark.asyncio
async def test_status_consistency(config_manager, event_bus):
    """Test status reporting consistency across lifecycle states."""
    component = ConfigComponent(config_manager, event_bus)
    
    # Before initialization
    status = component.get_status()
    assert "config_paths" in status
    assert "providers" in status
    assert status["providers"] == []
    
    # After initialization
    await component.initialize()
    status = component.get_status()
    assert status["config_paths"] is not None
    assert status["providers"] is not None
    
    # After start
    await component.start()
    status = component.get_status()
    assert status["config_paths"] is not None
    assert status["providers"] is not None
    
    # After shutdown
    await component.shutdown()
    status = component.get_status()
    assert status["config_paths"] is not None
    assert status["providers"] is not None
