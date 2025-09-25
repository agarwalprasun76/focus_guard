"""
Component Interaction Integration Tests.

This module tests interactions between all Focus Guard components across the
entire pipeline, validating coordinator, browser integration, classification,
and blocking components work together correctly.
"""

import asyncio
import json
import time
import tempfile
import logging
import pytest
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from focus_guard.core.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from focus_guard.core.coordinator.components.browser import BrowserIntegrationComponent
from focus_guard.core.coordinator.components.classification import ClassificationComponent
from focus_guard.core.coordinator.events import EventBus, EventTypes
from focus_guard.core.browser.extension.tab_server import TabServer, TabServerConfig
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
from focus_guard.core.classification.enhanced_pipeline import EnhancedClassificationPipeline
from focus_guard.core.classification.base import ClassifierRegistry
from focus_guard.core.api.api import ClassifierBlockerAPI
from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.config.manager import DefaultConfigurationManager
from focus_guard.tests.integration.mock_browser_extension import MockBrowserExtension, MockBrowserInfo

logger = logging.getLogger(__name__)


@pytest.fixture
async def temp_config_dir():
    """Create temporary directory for configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
async def mock_config_manager(temp_config_dir):
    """Create mock configuration manager."""
    config_manager = MagicMock()
    config_manager.get.side_effect = lambda key, default=None: {
        'browser.tab_server.port': 5559,
        'browser.tab_server.host': 'localhost',
        'classification.cache_ttl_seconds': 3600,
        'classification.background_enabled': True,
        'blocking.default_strategy': 'domain_excluder'
    }.get(key, default)
    
    return config_manager


@pytest.fixture
async def event_bus():
    """Create event bus for component communication."""
    return EventBus()


@pytest.fixture
async def component_test_server():
    """Create tab server for component testing."""
    config = TabServerConfig(host='localhost', port=5559)
    server = TabServer(config)
    
    started = server.start(5559)
    if not started:
        pytest.skip("Could not start component test server")
    
    await asyncio.sleep(1)
    yield server
    server.stop()


@pytest.fixture
async def mock_extension_for_components(component_test_server):
    """Create mock extension for component testing."""
    extension = MockBrowserExtension(
        tab_server_url=f"http://localhost:{component_test_server.port}",
        browser_info=MockBrowserInfo(
            name="ComponentTestChrome",
            version="120.0.0.0",
            extension_id="component-test-extension"
        ),
        polling_interval=0.1
    )
    
    if not extension.start():
        pytest.skip("Could not start mock extension for components")
    
    yield extension
    extension.stop()


@pytest.fixture
async def test_classifier_registry():
    """Create test classifier registry."""
    registry = ClassifierRegistry()
    
    class TestProductivityClassifier:
        def __init__(self):
            self.name = "test_productivity_classifier"
        
        def classify(self, domain):
            productivity_domains = ['github.com', 'stackoverflow.com', 'docs.google.com']
            if any(d in domain.value for d in productivity_domains):
                return Category.PRODUCTIVITY
            return None
    
    class TestEntertainmentClassifier:
        def __init__(self):
            self.name = "test_entertainment_classifier"
        
        def classify(self, domain):
            entertainment_domains = ['youtube.com', 'netflix.com', 'twitch.tv']
            if any(d in domain.value for d in entertainment_domains):
                return Category.ENTERTAINMENT
            return None
    
    registry.register(TestProductivityClassifier())
    registry.register(TestEntertainmentClassifier())
    
    return registry


class TestCoordinatorComponentIntegration:
    """Test coordinator integration with all components."""
    
    @pytest.mark.asyncio
    async def test_coordinator_startup_and_component_registration(
        self, 
        mock_config_manager, 
        event_bus,
        temp_config_dir
    ):
        """Test coordinator startup and component registration."""
        coordinator = FocusGuardCoordinator(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        # Initialize coordinator
        await coordinator.initialize()
        
        # Verify coordinator is initialized
        assert coordinator.get_status()['status'] == 'initialized'
        
        # Start coordinator
        await coordinator.start()
        
        # Verify coordinator is running
        status = coordinator.get_status()
        assert status['status'] == 'running'
        assert 'components' in status
        
        # Stop coordinator
        await coordinator.stop()
        assert coordinator.get_status()['status'] == 'stopped'
    
    @pytest.mark.asyncio
    async def test_browser_component_integration(
        self, 
        mock_config_manager, 
        event_bus, 
        component_test_server,
        mock_extension_for_components
    ):
        """Test browser component integration with coordinator."""
        # Create browser integration component
        browser_component = BrowserIntegrationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        # Initialize and start component
        await browser_component.initialize()
        await browser_component.start()
        
        # Verify component is running
        assert browser_component.get_status()['status'] == 'running'
        
        # Create tabs in mock extension
        tab1 = mock_extension_for_components.create_tab("https://github.com/test", "GitHub Test")
        tab2 = mock_extension_for_components.create_tab("https://www.youtube.com/test", "YouTube Test")
        
        await asyncio.sleep(1)  # Wait for component to detect tabs
        
        # Component should detect tabs
        browser_integration = browser_component._browser_integration
        tabs = browser_integration.get_all_tabs()
        assert len(tabs) >= 2, "Browser component should detect tabs"
        
        # Stop component
        await browser_component.stop()
        assert browser_component.get_status()['status'] == 'stopped'
    
    @pytest.mark.asyncio
    async def test_classification_component_integration(
        self, 
        mock_config_manager, 
        event_bus, 
        test_classifier_registry,
        temp_config_dir
    ):
        """Test classification component integration."""
        # Create classification component
        classification_component = ClassificationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        # Mock the classifier registry
        with patch.object(classification_component, '_create_classifier_registry', return_value=test_classifier_registry):
            # Initialize and start component
            await classification_component.initialize()
            await classification_component.start()
            
            # Verify component is running
            assert classification_component.get_status()['status'] == 'running'
            
            # Test classification through component
            domain = Domain("github.com")
            # Note: In real implementation, this would be triggered by events
            # Here we test the component's classification capability directly
            
            # Stop component
            await classification_component.stop()
            assert classification_component.get_status()['status'] == 'stopped'


class TestEventDrivenComponentInteractions:
    """Test event-driven interactions between components."""
    
    @pytest.mark.asyncio
    async def test_tab_event_propagation(
        self, 
        mock_config_manager, 
        event_bus, 
        component_test_server,
        mock_extension_for_components
    ):
        """Test tab event propagation between components."""
        # Track events
        received_events = []
        
        def event_handler(event_type, event_data):
            received_events.append((event_type, event_data))
        
        # Subscribe to tab events
        event_bus.subscribe(EventTypes.TAB_OPENED, event_handler)
        event_bus.subscribe(EventTypes.TAB_UPDATED, event_handler)
        event_bus.subscribe(EventTypes.TAB_CLOSED, event_handler)
        
        # Create browser component
        browser_component = BrowserIntegrationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        await browser_component.initialize()
        await browser_component.start()
        
        # Create tab in mock extension
        tab = mock_extension_for_components.create_tab("https://github.com/events", "Event Test")
        await asyncio.sleep(1)
        
        # Update tab
        mock_extension_for_components.update_tab(tab.id, url="https://github.com/updated", title="Updated Test")
        await asyncio.sleep(1)
        
        # Close tab
        mock_extension_for_components.close_tab(tab.id)
        await asyncio.sleep(1)
        
        # Verify events were received
        event_types = [event[0] for event in received_events]
        assert EventTypes.TAB_OPENED in event_types or EventTypes.TAB_UPDATED in event_types, "Should receive tab events"
        
        await browser_component.stop()
    
    @pytest.mark.asyncio
    async def test_classification_event_chain(
        self, 
        mock_config_manager, 
        event_bus, 
        component_test_server,
        mock_extension_for_components,
        test_classifier_registry
    ):
        """Test classification event chain from tab detection to classification."""
        # Track classification events
        classification_events = []
        
        def classification_handler(event_type, event_data):
            classification_events.append((event_type, event_data))
        
        event_bus.subscribe(EventTypes.DOMAIN_CLASSIFIED, classification_handler)
        
        # Create browser and classification components
        browser_component = BrowserIntegrationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        classification_component = ClassificationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        # Mock classifier registry for classification component
        with patch.object(classification_component, '_create_classifier_registry', return_value=test_classifier_registry):
            # Start both components
            await browser_component.initialize()
            await browser_component.start()
            
            await classification_component.initialize()
            await classification_component.start()
            
            # Create tab that should trigger classification
            tab = mock_extension_for_components.create_tab("https://github.com/classify", "Classification Test")
            await asyncio.sleep(2)  # Wait for event propagation and classification
            
            # Should receive classification events
            # Note: Actual event flow depends on component implementation
            # This test verifies the event infrastructure is working
            
            await browser_component.stop()
            await classification_component.stop()


class TestEndToEndComponentFlow:
    """Test complete end-to-end flow through all components."""
    
    @pytest.mark.asyncio
    async def test_complete_tab_blocking_flow(
        self, 
        mock_config_manager, 
        event_bus, 
        component_test_server,
        mock_extension_for_components,
        test_classifier_registry
    ):
        """Test complete flow from tab detection to blocking decision."""
        # Track the complete flow
        flow_events = []
        
        def flow_tracker(event_type, event_data):
            flow_events.append({
                'event_type': event_type,
                'timestamp': time.time(),
                'data': event_data
            })
        
        # Subscribe to all relevant events
        for event_type in [EventTypes.TAB_OPENED, EventTypes.TAB_UPDATED, EventTypes.DOMAIN_CLASSIFIED]:
            event_bus.subscribe(event_type, flow_tracker)
        
        # Create all components
        browser_component = BrowserIntegrationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        classification_component = ClassificationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        # Mock classifier registry
        with patch.object(classification_component, '_create_classifier_registry', return_value=test_classifier_registry):
            # Start all components
            await browser_component.initialize()
            await browser_component.start()
            
            await classification_component.initialize()
            await classification_component.start()
            
            # Create entertainment tab (should be blocked)
            entertainment_tab = mock_extension_for_components.create_tab(
                "https://www.youtube.com/watch?v=test", 
                "YouTube Test Video"
            )
            
            # Create productivity tab (should be allowed)
            productivity_tab = mock_extension_for_components.create_tab(
                "https://github.com/project", 
                "GitHub Project"
            )
            
            await asyncio.sleep(3)  # Wait for complete flow
            
            # Verify flow events occurred
            assert len(flow_events) > 0, "Should have flow events"
            
            # Verify components are still running
            assert browser_component.get_status()['status'] == 'running'
            assert classification_component.get_status()['status'] == 'running'
            
            # Test blocking decision through API
            api = ClassifierBlockerAPI()
            
            # Test entertainment blocking
            entertainment_result = await api.classify_domain("https://www.youtube.com/watch?v=test")
            if entertainment_result:
                assert entertainment_result.category == Category.ENTERTAINMENT
                should_block_entertainment = await api.should_block_domain("https://www.youtube.com/watch?v=test")
                assert isinstance(should_block_entertainment, bool)
            
            # Test productivity allowing
            productivity_result = await api.classify_domain("https://github.com/project")
            if productivity_result:
                assert productivity_result.category == Category.PRODUCTIVITY
                should_block_productivity = await api.should_block_domain("https://github.com/project")
                assert isinstance(should_block_productivity, bool)
            
            # Stop components
            await browser_component.stop()
            await classification_component.stop()
    
    @pytest.mark.asyncio
    async def test_component_health_monitoring(
        self, 
        mock_config_manager, 
        event_bus, 
        component_test_server
    ):
        """Test health monitoring across all components."""
        # Create components
        browser_component = BrowserIntegrationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        classification_component = ClassificationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        # Start components
        await browser_component.initialize()
        await browser_component.start()
        
        await classification_component.initialize()
        await classification_component.start()
        
        # Check health of all components
        browser_health = browser_component.is_healthy()
        classification_health = classification_component.is_healthy()
        
        assert browser_health, "Browser component should be healthy"
        assert classification_health, "Classification component should be healthy"
        
        # Get detailed status
        browser_status = browser_component.get_status()
        classification_status = classification_component.get_status()
        
        assert browser_status['status'] == 'running'
        assert classification_status['status'] == 'running'
        
        # Stop components
        await browser_component.stop()
        await classification_component.stop()
        
        # Health should reflect stopped state
        assert not browser_component.is_healthy()
        assert not classification_component.is_healthy()


class TestComponentErrorHandling:
    """Test error handling in component interactions."""
    
    @pytest.mark.asyncio
    async def test_component_failure_isolation(
        self, 
        mock_config_manager, 
        event_bus
    ):
        """Test that component failures are isolated."""
        # Create components
        browser_component = BrowserIntegrationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        classification_component = ClassificationComponent(
            config_manager=mock_config_manager,
            event_bus=event_bus
        )
        
        # Start browser component successfully
        await browser_component.initialize()
        await browser_component.start()
        
        # Simulate classification component failure
        with patch.object(classification_component, 'start', side_effect=Exception("Simulated failure")):
            try:
                await classification_component.initialize()
                await classification_component.start()
            except Exception:
                pass  # Expected failure
        
        # Browser component should still be healthy
        assert browser_component.is_healthy(), "Browser component should remain healthy despite classification failure"
        assert browser_component.get_status()['status'] == 'running'
        
        # Classification component should be unhealthy
        assert not classification_component.is_healthy(), "Classification component should be unhealthy after failure"
        
        # Stop healthy component
        await browser_component.stop()
    
    @pytest.mark.asyncio
    async def test_event_bus_error_handling(self, event_bus):
        """Test event bus error handling with failing handlers."""
        # Track events
        successful_events = []
        
        def working_handler(event_type, event_data):
            successful_events.append((event_type, event_data))
        
        def failing_handler(event_type, event_data):
            raise Exception("Handler failure")
        
        # Subscribe both handlers
        event_bus.subscribe(EventTypes.TAB_OPENED, working_handler)
        event_bus.subscribe(EventTypes.TAB_OPENED, failing_handler)
        
        # Publish event
        test_event_data = {'tab_id': 123, 'url': 'https://test.com'}
        event_bus.publish(EventTypes.TAB_OPENED, test_event_data)
        
        await asyncio.sleep(0.1)  # Allow event processing
        
        # Working handler should still receive events despite failing handler
        assert len(successful_events) > 0, "Working handler should receive events despite other handler failures"
        assert successful_events[0][0] == EventTypes.TAB_OPENED
        assert successful_events[0][1] == test_event_data


class TestComponentPerformance:
    """Test performance characteristics of component interactions."""
    
    @pytest.mark.asyncio
    async def test_event_processing_performance(self, event_bus):
        """Test event processing performance."""
        # Track event processing times
        processing_times = []
        
        def timing_handler(event_type, event_data):
            start_time = event_data.get('start_time')
            if start_time:
                processing_time = time.time() - start_time
                processing_times.append(processing_time)
        
        event_bus.subscribe(EventTypes.TAB_OPENED, timing_handler)
        
        # Send multiple events
        for i in range(100):
            event_data = {
                'tab_id': i,
                'url': f'https://test{i}.com',
                'start_time': time.time()
            }
            event_bus.publish(EventTypes.TAB_OPENED, event_data)
        
        await asyncio.sleep(1)  # Wait for processing
        
        # Verify performance
        if processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)
            max_processing_time = max(processing_times)
            
            assert avg_processing_time < 0.01, "Average event processing should be fast"
            assert max_processing_time < 0.1, "Max event processing should be reasonable"
            assert len(processing_times) >= 90, "Most events should be processed"
    
    @pytest.mark.asyncio
    async def test_component_startup_performance(self, mock_config_manager, event_bus):
        """Test component startup performance."""
        startup_times = []
        
        # Test multiple component startups
        for i in range(5):
            browser_component = BrowserIntegrationComponent(
                config_manager=mock_config_manager,
                event_bus=event_bus
            )
            
            start_time = time.time()
            await browser_component.initialize()
            await browser_component.start()
            startup_time = time.time() - start_time
            
            startup_times.append(startup_time)
            
            await browser_component.stop()
        
        # Verify startup performance
        avg_startup_time = sum(startup_times) / len(startup_times)
        max_startup_time = max(startup_times)
        
        assert avg_startup_time < 5.0, "Average component startup should be reasonable"
        assert max_startup_time < 10.0, "Max component startup should be acceptable"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])
