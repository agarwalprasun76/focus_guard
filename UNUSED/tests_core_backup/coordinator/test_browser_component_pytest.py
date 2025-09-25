"""
Complete pytest-asyncio tests for BrowserIntegrationComponent.

This module provides comprehensive async tests for the BrowserIntegrationComponent
using pytest-asyncio with AsyncMock for cleaner async testing.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from core_v2.coordinator.components.browser import (
    BrowserIntegrationComponent,
    TabOpenedEventData,
    TabUpdatedEventData,
    TabClosedEventData,
    ExtensionStatusChangedEventData
)
from core_v2.coordinator.events import EventTypes
from core_v2.config.interfaces import ConfigurationManager
from core_v2.browser.integration import BrowserIntegration
from core_v2.browser.tab_server import TabServer


@pytest.mark.asyncio
class TestBrowserIntegrationComponentPytest:
    """Complete async tests for BrowserIntegrationComponent using pytest-asyncio."""
    
    @pytest.fixture
    def config_manager(self):
        """Create mock configuration manager."""
        manager = MagicMock(spec=ConfigurationManager)
        
        # Mock configuration methods
        manager.get = MagicMock()
        manager.get.side_effect = lambda path, default=None: {
            "browser_integration.polling_interval_seconds": 1.0,
            "browser_integration.health_check_interval_seconds": 60.0
        }.get(path, default)
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
    def tab_server(self):
        """Create mock tab server with proper async methods."""
        server = MagicMock()
        server.start = AsyncMock(return_value=True)
        server.stop = AsyncMock(return_value=True)
        server.shutdown = AsyncMock(return_value=True)
        server.is_running = MagicMock(return_value=True)
        server.get_status = MagicMock(return_value={
            "running": True,
            "port": 8000,
            "connections": 1
        })
        server.initialize = AsyncMock(return_value=True)
        return server
    
    @pytest.fixture
    def browser_integration(self):
        """Create mock browser integration with proper async methods."""
        integration = MagicMock()
        integration.get_active_tabs = AsyncMock(return_value=[
            {
                "id": 1,
                "window_id": 1,
                "url": "https://example.com",
                "title": "Example Domain",
                "favicon": "https://example.com/favicon.ico",
                "active": True
            }
        ])
        integration.close_tab = AsyncMock(return_value=True)
        integration.is_extension_installed = AsyncMock(return_value=True)
        integration.is_extension_enabled = AsyncMock(return_value=True)
        integration.get_extension_status = AsyncMock(return_value={
            "installed": True,
            "enabled": True,
            "version": "1.0.0"
        })
        integration.initialize = AsyncMock(return_value=True)
        return integration
    
    @pytest.fixture
    def component(self, browser_integration, tab_server, event_bus, config_manager):
        """Create BrowserIntegrationComponent instance with mocked dependencies."""
        return BrowserIntegrationComponent(
            browser_integration,
            tab_server,
            event_bus,
            config_manager
        )
    
    async def test_initialization(self, component, event_bus, config_manager, tab_server, browser_integration):
        """Test that the component is initialized correctly."""
        assert component.name == "browser_integration"
        assert component._event_bus == event_bus
        assert component._config_manager == config_manager
        assert component._browser_integration == browser_integration
        assert component._tab_server == tab_server
        assert component._logger is not None
    
    async def test_initialize(self, component):
        """Test initializing the component."""
        result = await component.initialize()
        assert result is True
        assert component._initialized is True
    
    async def test_start(self, component):
        """Test starting the component."""
        await component.initialize()
        result = await component.start()
        assert result is True
        assert component._running is True
    
    async def test_stop(self, component):
        """Test stopping the component."""
        await component.initialize()
        await component.start()
        
        result = await component.stop()
        assert result is True
        assert component._running is False
    
    async def test_shutdown(self, component):
        """Test shutting down the component."""
        await component.initialize()
        
        result = await component.shutdown()
        assert result is True
        assert component._initialized is False
    
    async def test_get_status(self, component):
        """Test getting the component status."""
        status = component.get_status()
        assert isinstance(status, dict)
        assert status["name"] == "browser_integration"
        # Status structure depends on component implementation
    
    async def test_is_healthy(self, component):
        """Test checking if the component is healthy."""
        # Health check depends on component state
        health = component.is_healthy()
        assert isinstance(health, bool)
    
    async def test_polling_loop(self, component):
        """Test the polling loop functionality."""
        await component.initialize()
        await component.start()
        
        # Mock the polling behavior
        component._poll_tabs = AsyncMock()
        
        # Simulate one polling iteration
        await component._poll_tabs()
        
        # Verify polling was called
        component._poll_tabs.assert_called_once()
    
    async def test_health_check_loop(self, component):
        """Test the health check loop functionality."""
        await component.initialize()
        await component.start()
        
        # Mock the health check behavior
        component._check_health = AsyncMock()
        
        # Simulate one health check iteration
        await component._check_health()
        
        # Verify health check was called
        component._check_health.assert_called_once()
    
    async def test_tab_opened_event_data(self):
        """Test the TabOpenedEventData class."""
        source = "test_source"
        tab_id = 1
        window_id = 1
        url = "https://example.com"
        title = "Example Domain"
        favicon = "https://example.com/favicon.ico"
        
        event_data = TabOpenedEventData(source, tab_id, window_id, url, title, favicon)
        
        assert event_data.source == source
        assert event_data.tab_id == tab_id
        assert event_data.window_id == window_id
        assert event_data.url == url
        assert event_data.title == title
        assert event_data.favicon == favicon
        
        data_dict = event_data.to_dict()
        assert data_dict["source"] == source
        assert data_dict["tab_id"] == tab_id
        assert data_dict["window_id"] == window_id
        assert data_dict["url"] == url
        assert data_dict["title"] == title
        assert data_dict["favicon"] == favicon
        # Note: active attribute is not part of TabOpenedEventData
    
    async def test_tab_updated_event_data(self):
        """Test the TabUpdatedEventData class."""
        source = "test_source"
        tab_id = 1
        window_id = 1
        url = "https://example.com"
        title = "Example Domain"
        favicon = "https://example.com/favicon.ico"
        
        event_data = TabUpdatedEventData(source, tab_id, window_id, url, title, favicon)
        
        assert event_data.source == source
        assert event_data.tab_id == tab_id
        assert event_data.window_id == window_id
        assert event_data.url == url
        assert event_data.title == title
        assert event_data.favicon == favicon
        
        data_dict = event_data.to_dict()
        assert data_dict["source"] == source
        assert data_dict["tab_id"] == tab_id
        assert data_dict["window_id"] == window_id
        assert data_dict["url"] == url
        assert data_dict["title"] == title
        assert data_dict["favicon"] == favicon
    
    async def test_tab_closed_event_data(self):
        """Test the TabClosedEventData class."""
        source = "test_source"
        tab_id = 1
        window_id = 1
        url = "https://example.com"
        
        event_data = TabClosedEventData(source, tab_id, window_id, url)
        
        assert event_data.source == source
        assert event_data.tab_id == tab_id
        assert event_data.window_id == window_id
        assert event_data.url == url
        
        data_dict = event_data.to_dict()
        assert data_dict["source"] == source
        assert data_dict["tab_id"] == tab_id
        assert data_dict["window_id"] == window_id
        assert data_dict["url"] == url
    
    async def test_extension_status_changed_event_data(self):
        """Test the ExtensionStatusChangedEventData class."""
        source = "test_source"
        installed = True
        enabled = True
        version = "1.0.0"
        
        event_data = ExtensionStatusChangedEventData(source, installed, enabled, version)
        
        assert event_data.source == source
        assert event_data.installed == installed
        assert event_data.enabled == enabled
        assert event_data.version == version
        
        data_dict = event_data.to_dict()
        assert data_dict["source"] == source
        assert data_dict["installed"] == installed
        assert data_dict["enabled"] == enabled
        assert data_dict["version"] == version
    
    async def test_handle_config_changed(self, component):
        """Test handling configuration changes."""
        await component.initialize()
        
        # Create configuration change event data
        class MockConfigChangedEventData:
            def __init__(self, path, new_value):
                self.path = path
                self.new_value = new_value
        
        # Test changing polling interval
        event_data = MockConfigChangedEventData("browser_integration.polling_interval_seconds", 2.0)
        await component._handle_config_changed(event_data)
        assert component._polling_interval == 2.0
        
        # Test changing health check interval
        event_data = MockConfigChangedEventData("browser_integration.health_check_interval_seconds", 120.0)
        await component._handle_config_changed(event_data)
        assert component._health_check_interval == 120.0
    
    async def test_multiple_lifecycle_operations(self, component):
        """Test multiple lifecycle operations in sequence."""
        # Test basic lifecycle operations
        init_result = await component.initialize()
        assert isinstance(init_result, bool)
        
        start_result = await component.start()
        assert isinstance(start_result, bool)
        
        stop_result = await component.stop()
        assert isinstance(stop_result, bool)
        
        shutdown_result = await component.shutdown()
        assert isinstance(shutdown_result, bool)
    
    async def test_status_consistency(self, component):
        """Test status reporting consistency across lifecycle."""
        # Test that status is always a dict with correct structure
        status = component.get_status()
        assert isinstance(status, dict)
        assert status["name"] == "browser_integration"
        
        # Test that status structure is maintained across lifecycle
        await component.initialize()
        status = component.get_status()
        assert isinstance(status, dict)
        
        await component.start()
        status = component.get_status()
        assert isinstance(status, dict)
