"""
Working pytest-asyncio tests for DistractionDetectorComponent.
This demonstrates the clean async testing approach with pytest-asyncio.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from core_v2.coordinator.components.distraction import DistractionDetectorComponent
from core_v2.config.interfaces import ConfigurationManager
from core_v2.distraction.interfaces import DistractionDetector
from core_v2.classification.models import Category
from core_v2.coordinator.events import EventTypes


@pytest.mark.asyncio
class TestDistractionDetectorComponentPytest:
    """Async tests for DistractionDetectorComponent using pytest-asyncio."""
    
    @pytest.fixture
    def config_manager(self):
        """Create mock configuration manager."""
        manager = MagicMock(spec=ConfigurationManager)
        manager.get_value = MagicMock()
        manager.get_value.side_effect = lambda path, default=None: {
            "distraction.rules.enabled": True,
            "distraction.rules.social_media": True,
            "distraction.rules.entertainment": True,
            "distraction.rules.productivity": False,
            "distraction.alert.level": "medium",
            "distraction.alert.timeout": 300
        }.get(path, default)
        return manager
    
    @pytest.fixture
    def distraction_detector(self):
        """Create mock distraction detector."""
        detector = MagicMock(spec=DistractionDetector)
        detector.add_rule = MagicMock()
        detector.add_alert_handler = MagicMock()
        detector.update = MagicMock()
        detector.is_distracted = PropertyMock(return_value=False)
        detector.get_distraction_state = MagicMock(return_value={})
        return detector
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        return AsyncMock()
    
    async def test_initialization(self, config_manager, distraction_detector, event_bus):
        """Test that the component initializes correctly."""
        component = DistractionDetectorComponent(
            config_manager=config_manager,
            distraction_detector=distraction_detector,
            event_bus=event_bus
        )
        
        result = await component.initialize()
        assert result is True
        assert component._initialized is True
        
        # Check subscriptions - the component subscribes to these specific events
        event_bus.subscribe.assert_any_call(
            EventTypes.DOMAIN_CLASSIFIED, component
        )
        event_bus.subscribe.assert_any_call(
            EventTypes.TAB_CLOSED, component
        )
        event_bus.subscribe.assert_any_call(
            EventTypes.IDLE_STATE_CHANGED, component
        )
        
        # Verify the exact number of subscriptions
        assert event_bus.subscribe.call_count == 3
    
    async def test_start_stop_lifecycle(self, config_manager, distraction_detector, event_bus):
        """Test component start/stop lifecycle."""
        component = DistractionDetectorComponent(
            config_manager=config_manager,
            distraction_detector=distraction_detector,
            event_bus=event_bus
        )
        
        await component.initialize()
        
        # Test start
        result = await component.start()
        assert result is True
        assert component._running is True
        
        # Test stop
        result = await component.stop()
        assert result is True
        assert component._running is False
    
    async def test_health_check(self, config_manager, distraction_detector, event_bus):
        """Test the health check functionality."""
        component = DistractionDetectorComponent(
            config_manager=config_manager,
            distraction_detector=distraction_detector,
            event_bus=event_bus
        )
        
        await component.initialize()
        await component.start()
        
        # Component should be healthy when initialized
        assert component.is_healthy() is True
    
    async def test_domain_classification_handling(self, config_manager, distraction_detector, event_bus):
        """Test handling domain classification events."""
        component = DistractionDetectorComponent(
            config_manager=config_manager,
            distraction_detector=distraction_detector,
            event_bus=event_bus
        )
        
        await component.initialize()
        await component.start()
        
        # Mock domain classified event
        class MockDomainClassifiedEventData:
            def __init__(self):
                self.source = "test_source"
                self.url = "https://example.com"
                self.domain = "example.com"
                self.result = type('Result', (), {'category': Category.SOCIAL_MEDIA})()
        
        event_data = MockDomainClassifiedEventData()
        await component.on_event(EventTypes.DOMAIN_CLASSIFIED, event_data)
        
        # Verify the component processed the event
        distraction_detector.update.assert_called()
    
    async def test_tab_closed_event_processing(self, config_manager, distraction_detector, event_bus):
        """Test that tab closed events are processed correctly."""
        component = DistractionDetectorComponent(
            config_manager=config_manager,
            distraction_detector=distraction_detector,
            event_bus=event_bus
        )
        
        await component.initialize()
        await component.start()
        
        # Create tab closed event
        class MockTabClosedEventData:
            def __init__(self):
                self.url = "https://example.com"
                self.domain = "example.com"
                self.tab = type('Tab', (), {'url': "https://example.com"})()
        
        event_data = MockTabClosedEventData()
        await component.on_event(EventTypes.TAB_CLOSED, event_data)
        
        # Verify event was processed without error
        # The component should handle the event gracefully

    async def test_idle_state_changed_processing(self, config_manager, distraction_detector, event_bus):
        """Test that idle state changes are processed correctly."""
        component = DistractionDetectorComponent(
            config_manager=config_manager,
            distraction_detector=distraction_detector,
            event_bus=event_bus
        )
        
        await component.initialize()
        await component.start()
        
        # Mock idle state event
        class MockIdleStateChangedEventData:
            def __init__(self):
                self.is_idle = True
                self.idle_duration = 300
        
        event_data = MockIdleStateChangedEventData()
        await component.on_event(EventTypes.IDLE_STATE_CHANGED, event_data)
        
        # Verify event was processed without error
        # The component should handle the event gracefully

    async def test_config_change_processing(self, config_manager, distraction_detector, event_bus):
        """Test that configuration changes are processed."""
        component = DistractionDetectorComponent(
            config_manager=config_manager,
            distraction_detector=distraction_detector,
            event_bus=event_bus
        )
        
        await component.initialize()
        await component.start()
        
        # Mock config change event with proper structure
        class MockConfigChangedEventData:
            def __init__(self):
                self.path = "distraction.rules.social_media"
                self.new_value = False
                self.old_value = True
        
        event_data = MockConfigChangedEventData()
        await component.on_event(EventTypes.CONFIG_CHANGED, event_data)
        
        # Verify config was accessed
        config_manager.get_value.assert_called()

    async def test_concurrent_event_handling(self, config_manager, distraction_detector, event_bus):
        """Test handling multiple events concurrently."""
        component = DistractionDetectorComponent(
            config_manager=config_manager,
            distraction_detector=distraction_detector,
            event_bus=event_bus
        )

        await component.initialize()
        await component.start()

        # Create multiple concurrent events
        events = []

        class MockDomainClassifiedEventData:
            def __init__(self, domain):
                self.source = "test_source"
                self.url = f"https://{domain}.com"
                self.domain = domain
                self.result = type('Result', (), {'category': Category.SOCIAL_MEDIA})()

        # Create 5 concurrent events
        domains = ["facebook", "twitter", "instagram", "youtube", "reddit"]
        for domain in domains:
            event_data = MockDomainClassifiedEventData(domain)
            events.append(component.on_event(EventTypes.DOMAIN_CLASSIFIED, event_data))

        # Run all events concurrently
        await asyncio.gather(*events)

        # Verify all events were processed
        assert distraction_detector.update.call_count == 5
