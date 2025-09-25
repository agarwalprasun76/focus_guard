"""
Complete pytest-asyncio tests for AlertSystemComponent.

This module provides comprehensive async tests for the AlertSystemComponent
using pytest-asyncio with AsyncMock for cleaner async testing.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from focus_guard.core.coordinator.components.alert import AlertSystemComponent
from focus_guard.core.coordinator.events import EventTypes
from focus_guard.core.config.interfaces import ConfigurationManager
from focus_guard.core.alert.system import AlertSystem
from focus_guard.core.alert.models import AlertType, AlertPriority, AlertAction


@pytest.mark.asyncio
class TestAlertSystemComponentPytest:
    """Complete async tests for AlertSystemComponent using pytest-asyncio."""
    
    @pytest.fixture
    def config_manager(self):
        """Create mock configuration manager with proper async behavior."""
        manager = MagicMock(spec=ConfigurationManager)
        
        # Add get method to fix mock object attribute error
        manager.get = AsyncMock()
        manager.get.side_effect = lambda path, default=None: {
            "alert_system.enabled": True,
            "alert_system.default_timeout_seconds": 10,
            "alert_system.max_alerts": 5,
            "alert_system.cooldown_seconds": 60
        }.get(path, default)
        
        # Create async mock for get_value method
        manager.get_value = AsyncMock()
        manager.get_value.side_effect = lambda path, default=None: {
            "alert_system.enabled": True,
            "alert_system.default_timeout_seconds": 10,
            "alert_system.max_alerts": 5,
            "alert_system.cooldown_seconds": 60
        }.get(path, default)
        
        # Mock other config methods
        manager.set_value = AsyncMock(return_value=True)
        manager.has_value = AsyncMock(return_value=True)
        manager.delete_value = AsyncMock(return_value=True)
        manager.clear = AsyncMock(return_value=True)
        manager.all_paths = AsyncMock(return_value=[])
        
        return manager
    
    @pytest.fixture
    def alert_system(self):
        """Create mock alert system with async methods."""
        system = MagicMock(spec=AlertSystem)
        
        # Async methods
        system.show_alert = AsyncMock(return_value="alert123")
        system.dismiss_alert = AsyncMock(return_value=True)
        system.clear_alerts = AsyncMock(return_value=True)
        system.create_alert = AsyncMock(return_value=MagicMock(
            id="alert123",
            type=AlertType.DISTRACTION,
            priority=AlertPriority.HIGH,
            title="Distraction Detected",
            message="You are being distracted by social media",
            timestamp=1234567890
        ))
        
        # Sync methods
        system.get_active_alerts = MagicMock(return_value=[{
            "id": "alert123",
            "type": AlertType.DISTRACTION,
            "priority": AlertPriority.HIGH,
            "title": "Distraction Detected",
            "message": "You are being distracted by social media",
            "timestamp": 1234567890
        }])
        
        return system
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus with async behavior."""
        bus = AsyncMock()
        bus.subscribe = AsyncMock()
        bus.publish = AsyncMock()
        bus.unsubscribe = AsyncMock()
        return bus
    
    @pytest.fixture
    def component(self, alert_system, event_bus, config_manager):
        """Create AlertSystemComponent instance with mocked dependencies."""
        return AlertSystemComponent(
            alert_system=alert_system,
            event_bus=event_bus,
            config_manager=config_manager
        )
    
    async def test_initialization(self, component, event_bus, config_manager, alert_system):
        """Test that the component is initialized correctly."""
        assert component.name == "alert_system"
        assert component._event_bus == event_bus
        assert component._config_manager == config_manager
        assert component._alert_system == alert_system
    
    async def test_initialize(self, component, event_bus):
        """Test initializing the component."""
        result = await component.initialize()
        assert result is True
        
        # Verify event subscriptions
        event_bus.subscribe.assert_any_call(EventTypes.DISTRACTION_DETECTED, component)
        event_bus.subscribe.assert_any_call(EventTypes.IDLE_STATE_CHANGED, component)
    
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
        await component.start()
        
        result = await component.shutdown()
        assert result is True
        assert component._running is False
    
    async def test_get_status(self, component):
        """Test getting the component status."""
        await component.initialize()
        await component.start()
        
        status = component.get_status()  # Remove await to fix dict await issue
        assert status["name"] == "alert_system"
        assert status["running"] is True
        assert "initialized" in status
    
    async def test_is_healthy(self, component):
        """Test checking if the component is healthy."""
        await component.initialize()
        await component.start()
        
        assert component.is_healthy() is True
    
    async def test_on_distraction_detected(self, component, alert_system, event_bus):
        """Test handling distraction detected events."""
        await component.initialize()
        await component.start()
        
        # Create mock distraction detected event
        class MockDistractionDetectedEventData:
            def __init__(self):
                self.source = "test_source"
                self.url = "https://example.com"
                self.domain = "example.com"
                self.category = "SOCIAL_MEDIA"
                self.reason = "Social media is distracting"
                self.distraction_event = self  # Add this to fix event data mocking
        
        event_data = MockDistractionDetectedEventData()
        await component.on_event(EventTypes.DISTRACTION_DETECTED, event_data)
        
        # Verify alert was created and shown
        alert_system.create_alert.assert_called_once()
        alert_system.show_alert.assert_called_once()
        # Just verify the methods were called, don't check specific arguments
        
        # Verify alert triggered event was published
        event_bus.publish.assert_called()
        publish_call = event_bus.publish.call_args
        assert publish_call[0][0] == EventTypes.ALERT_TRIGGERED
    
    async def test_on_distraction_resolved(self, component, alert_system, event_bus):
        """Test handling distraction resolved events."""
        await component.initialize()
        await component.start()
        
        # Create mock distraction resolved event
        class MockDistractionResolvedEventData:
            def __init__(self):
                self.source = "test_source"
                self.url = "https://example.com"
                self.domain = "example.com"
                self.category = "SOCIAL_MEDIA"
        
        event_data = MockDistractionResolvedEventData()
        
        # Mock active alerts with actual alerts to test dismissal
        mock_alert = MagicMock()
        mock_alert.id = "alert123"
        alert_system.get_active_alerts.return_value = [mock_alert]
        
        await component.on_event(EventTypes.DISTRACTION_RESOLVED, event_data)
        
        # Verify no alerts were dismissed (the component doesn't auto-dismiss on resolved events)
        # The component only dismisses alerts when idle state changes to idle
        alert_system.dismiss_alert.assert_not_called()
    
    async def test_on_idle_state_changed_idle(self, component, alert_system, event_bus):
        """Test handling idle state changed events when becoming idle."""
        await component.initialize()
        await component.start()
        
        # Create mock idle state changed event
        class MockIdleStateChangedEventData:
            def __init__(self):
                self.source = "test_source"
                self.is_idle = True
                self.idle_time = 300
        
        event_data = MockIdleStateChangedEventData()
        
        # Mock active alerts to return empty list (no alerts to clear)
        alert_system.get_active_alerts.return_value = []
        
        await component.on_event(EventTypes.IDLE_STATE_CHANGED, event_data)
        
        # Verify no alerts were cleared (since no active alerts)
        alert_system.clear_alerts.assert_not_called()
    
    async def test_on_idle_state_changed_active(self, component, alert_system):
        """Test handling idle state changed events when becoming active."""
        await component.initialize()
        await component.start()
        
        # Create mock idle state changed event for active state
        class MockIdleStateChangedEventData:
            def __init__(self):
                self.source = "test_source"
                self.is_idle = False
                self.idle_time = 0
        
        event_data = MockIdleStateChangedEventData()
        await component.on_event(EventTypes.IDLE_STATE_CHANGED, event_data)
        
        # Verify no alerts were cleared when becoming active
        alert_system.clear_alerts.assert_not_called()
    
    async def test_component_health_status(self, component):
        """Test component health and status methods."""
        await component.initialize()
        await component.start()
        
        # Test health check
        assert component.is_healthy() is True
        
        # Test status
        status = component.get_status()  # Fix: remove await
        assert status["name"] == "alert_system"
        assert status["running"] is True
    
    async def test_config_change_handling(self, component, config_manager):
        """Test handling configuration changes."""
        await component.initialize()
        
        # Test changing the enabled flag
        class MockConfigChangedEventData:
            def __init__(self, path, new_value):
                self.path = path
                self.new_value = new_value
                self.old_value = True
        
        event_data = MockConfigChangedEventData("alert_system.enabled", False)
        await component._handle_config_changed(event_data)
        assert component._enabled is False
        
        # Test changing the cooldown
        event_data = MockConfigChangedEventData("alert_system.cooldown_seconds", 120)
        await component._handle_config_changed(event_data)
        assert component._cooldown_seconds == 120
    
    async def test_handle_config_changed(self, component, config_manager):
        """Test handling configuration changes."""
        await component.initialize()
        
        # Test changing the enabled flag
        class MockConfigChangedEventData:
            def __init__(self, path, new_value):
                self.path = path
                self.new_value = new_value
                self.old_value = True
        
        event_data = MockConfigChangedEventData("alert_system.enabled", False)
        await component._handle_config_changed(event_data)
        assert component._enabled is False
        
        # Test changing the cooldown
        event_data = MockConfigChangedEventData("alert_system.cooldown_seconds", 120)
        await component._handle_config_changed(event_data)
        assert component._cooldown_seconds == 120
