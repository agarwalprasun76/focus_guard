"""
Complete pytest-asyncio tests for ClassificationComponent.

This module provides comprehensive async tests for the ClassificationComponent
using pytest-asyncio with AsyncMock for cleaner async testing.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from core_v2.coordinator.components.classification import (
    ClassificationComponent,
    DomainClassifiedEventData
)
from core_v2.coordinator.events import EventTypes
from core_v2.config.interfaces import ConfigurationManager
from core_v2.classification.classifier import DomainClassifier
from core_v2.classification.models import Category, ClassificationResult


@pytest.mark.asyncio
class TestClassificationComponentPytest:
    """Complete async tests for ClassificationComponent using pytest-asyncio."""

    @pytest.fixture
    def config_manager(self):
        """Create a mock ConfigurationManager instance."""
        manager = MagicMock()
        # Mock configuration methods
        manager.get = MagicMock()
        manager.get.side_effect = lambda path, default=None: {
            "classification.cache_ttl_seconds": 300,
            "classification.cache_cleanup_interval_seconds": 60
        }.get(path, default)
        manager.set = MagicMock(return_value=True)
        manager.has = MagicMock(return_value=False)
        manager.delete = MagicMock(return_value=True)
        manager.clear = MagicMock(return_value=True)
        manager.all_paths = MagicMock(return_value=[])
        
        return manager

    @pytest.fixture
    def event_bus(self):
        """Create a mock EventBus instance."""
        bus = MagicMock()
        bus.subscribe = AsyncMock()
        bus.publish = AsyncMock()
        bus.unsubscribe = AsyncMock()
        return bus

    @pytest.fixture
    def domain_classifier(self):
        """Create a mock DomainClassifier instance."""
        classifier = MagicMock()
        classifier.initialize = AsyncMock(return_value=True)
        classifier.classify_domain = AsyncMock(
            return_value=ClassificationResult(
                domain="example.com",
                category=Category.SOCIAL_MEDIA,
                metadata={
                    "confidence": 0.95,
                    "category_name": "Social Media",
                    "category_description": "Social media websites"
                }
            )
        )
        return classifier

    @pytest.fixture
    def component(self, domain_classifier, event_bus, config_manager):
        """Create ClassificationComponent instance with mocked dependencies."""
        return ClassificationComponent(
            domain_classifier,
            event_bus,
            config_manager
        )

    async def test_initialization(self, component, event_bus, config_manager, domain_classifier):
        """Test that the component is initialized correctly."""
        assert component.name == "domain_classifier"
        assert component._event_bus == event_bus
        assert component._config_manager == config_manager
        assert component._domain_classifier == domain_classifier

    async def test_initialize(self, component, config_manager):
        """Test initializing the component."""
        result = await component.initialize()
        
        assert result is True
        assert component._cache_ttl_seconds == 300
        assert component._cache_cleanup_interval == 60

    async def test_start(self, component):
        """Test starting the component."""
        await component.initialize()
        result = await component.start()
        assert result is True
        assert component._running is True

    async def test_stop(self, component):
        """Test stopping the component."""
        await component.start()
        result = await component.stop()
        assert result is True

    async def test_shutdown(self, component):
        """Test shutting down the component."""
        await component.initialize()
        result = await component.shutdown()
        assert result is True

    async def test_get_status(self, component):
        """Test getting the component status."""
        status = component.get_status()
        assert isinstance(status, dict)
        assert "cache_ttl_seconds" in status
        assert "cache_size" in status
        assert "cache_cleanup_interval" in status

    async def test_is_healthy(self, component):
        """Test checking if the component is healthy."""
        health = component.is_healthy()
        assert isinstance(health, bool)

    async def test_cache_cleanup_loop(self, component):
        """Test the cache cleanup loop functionality."""
        # Initialize component first
        await component.initialize()
        
        # Test that cleanup loop can be started
        await component.start()
        
        # Test that cleanup loop can be stopped
        await component.stop()

    async def test_on_tab_opened(self, component, event_bus):
        """Test handling tab opened events."""
        # Create spy on publish method
        publish_calls = []
        original_publish = event_bus.publish
        
        async def spy_publish(event_type, event_data):
            publish_calls.append((event_type, event_data))
            return await original_publish(event_type, event_data)
        
        event_bus.publish = spy_publish
        
        # Create tab event data
        class MockTab:
            def __init__(self, url):
                self.url = url
                self.tab_id = 1
                self.window_id = 1
                self.title = "Test Title"
        
        class MockTabEventData:
            def __init__(self, url):
                self.source = "test_source"
                self.tab = MockTab(url)

        await component.initialize()
        
        # Clear cache to ensure classification is triggered
        component._classification_cache.clear()
        
        # Handle tab opened event
        event_data = MockTabEventData("https://example.com")
        await component.on_event(EventTypes.TAB_OPENED, event_data)
        
        # Allow async tasks to complete
        await asyncio.sleep(0.5)
        
        # Verify classification occurred
        component._domain_classifier.classify_domain.assert_called_once_with("example.com", "https://example.com")
        
        # Verify event was published
        classification_events = [e for e in publish_calls if e[0] == EventTypes.DOMAIN_CLASSIFIED]
        assert len(classification_events) == 1
        event_type, event_data = classification_events[0]
        assert isinstance(event_data, DomainClassifiedEventData)
        assert event_data.url == "https://example.com"
        assert event_data.domain == "example.com"
        assert event_data.result.category == Category.SOCIAL_MEDIA

    async def test_on_tab_updated(self, component, event_bus):
        """Test handling tab updated events."""
        # Create spy on publish method
        publish_calls = []
        original_publish = event_bus.publish
        
        async def spy_publish(event_type, event_data):
            publish_calls.append((event_type, event_data))
            return await original_publish(event_type, event_data)
        
        event_bus.publish = spy_publish
        
        # Create tab event data
        class MockTab:
            def __init__(self, url):
                self.url = url
                self.tab_id = 1
                self.window_id = 1
                self.title = "Test Title"

        class MockTabEventData:
            def __init__(self, url):
                self.source = "test_source"
                self.tab = MockTab(url)
        
        await component.initialize()
        
        # Clear cache to ensure classification is triggered
        component._classification_cache.clear()
        
        # Handle tab updated event
        event_data = MockTabEventData("https://example.com")
        await component.on_event(EventTypes.TAB_UPDATED, event_data)
        
        # Allow async tasks to complete
        await asyncio.sleep(0.1)
        
        # Verify classification occurred
        component._domain_classifier.classify_domain.assert_called_once_with("example.com", "https://example.com")
        
        # Verify event was published
        classification_events = [e for e in publish_calls if e[0] == EventTypes.DOMAIN_CLASSIFIED]
        assert len(classification_events) == 1
        event_type, event_data = classification_events[0]
        assert event_data.domain == "example.com"
        assert event_data.url == "https://example.com"
        assert event_data.result.category == Category.SOCIAL_MEDIA

    async def test_domain_classified_event_data(self):
        """Test the DomainClassifiedEventData class."""
        source = "test_source"
        domain = "example.com"
        url = "https://example.com"
        result = ClassificationResult(
            domain="example.com",
            category=Category.SOCIAL_MEDIA,
            metadata={
                "confidence": 0.95,
                "category_name": "Social Media",
                "category_description": "Social media websites"
            }
        )
        
        event_data = DomainClassifiedEventData(source, domain, url, result)
        
        assert event_data.source == source
        assert event_data.url == url
        assert event_data.domain == domain
        assert event_data.result.category == Category.SOCIAL_MEDIA
        assert event_data.result.metadata["category_name"] == "Social Media"
        
        data_dict = event_data.to_dict()
        assert data_dict["source"] == source
        assert data_dict["url"] == url
        assert data_dict["domain"] == domain
        assert data_dict["result"]["category"] == Category.SOCIAL_MEDIA.name
        assert data_dict["result"]["metadata"]["category_name"] == "Social Media"

    async def test_handle_config_changed(self, component):
        """Test handling configuration changes."""
        await component.initialize()
        
        # Create configuration change event data
        class MockConfigChangedEventData:
            def __init__(self, path, new_value):
                self.path = path
                self.new_value = new_value
        
        # Test changing cache TTL
        event_data = MockConfigChangedEventData("classification.cache_ttl_seconds", 600)
        await component._handle_config_changed(event_data)
        assert component._cache_ttl_seconds == 600
        
        # Test changing cache cleanup interval
        event_data = MockConfigChangedEventData("classification.cache_cleanup_interval_seconds", 120)
        await component._handle_config_changed(event_data)
        assert component._cache_cleanup_interval == 120

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
        assert status["name"] == "domain_classifier"
        
        # Test that status structure is maintained across lifecycle
        await component.initialize()
        status = component.get_status()
        assert isinstance(status, dict)
        
        await component.start()
        status = component.get_status()
        assert isinstance(status, dict)
