"""
Tests for the coordinator event system using pytest-asyncio.

This module tests the event system implementation in the coordinator module
using modern pytest-asyncio framework.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from focus_guard.core.coordinator.events import DefaultEventBus, EventTypes, EventData


class TestEventDataPytest:
    """Test cases for the EventData class using pytest."""
    
    def test_event_data_initialization(self):
        """Test that EventData can be initialized correctly."""
        source = "test_source"
        event_data = EventData(source)
        
        assert event_data.source == source
        assert event_data.timestamp is not None
    
    def test_event_data_to_dict(self):
        """Test that EventData can be converted to a dictionary."""
        source = "test_source"
        event_data = EventData(source)
        
        data_dict = event_data.to_dict()
        
        assert data_dict["source"] == source
        assert "timestamp" in data_dict


@pytest.mark.asyncio
class TestDefaultEventBusPytest:
    """Test cases for the DefaultEventBus class using pytest-asyncio."""
    
    @pytest.fixture
    def event_bus(self):
        """Create a fresh event bus for each test."""
        return DefaultEventBus()
    
    @pytest.fixture
    def event_type(self):
        """Standard event type for testing."""
        return EventTypes.COMPONENT_INITIALIZED
    
    @pytest.fixture
    def event_data(self):
        """Standard event data for testing."""
        return EventData("test_source")
    
    async def test_subscribe_and_unsubscribe(self, event_bus, event_type):
        """Test subscribing and unsubscribing from events."""
        # Create a mock listener
        listener = Mock()
        listener.on_event = AsyncMock()
        
        # Subscribe to an event
        event_bus.subscribe(event_type, listener)
        
        # Check that the listener is subscribed
        subscribers = event_bus.subscribers.get(event_type, set())
        has_listener = any(ref() is listener for ref in subscribers if ref() is not None)
        assert has_listener is True
        
        # Unsubscribe from the event
        event_bus.unsubscribe(event_type, listener)
        
        # Check that the listener is no longer subscribed
        subscribers = event_bus.subscribers.get(event_type, set())
        has_listener = any(ref() is listener for ref in subscribers if ref() is not None)
        assert has_listener is False
    
    async def test_unsubscribe_nonexistent(self, event_bus, event_type):
        """Test unsubscribing a listener that is not subscribed."""
        # Create a mock listener
        listener = Mock()
        
        # Unsubscribe from an event (should not raise an exception)
        event_bus.unsubscribe(event_type, listener)
    
    async def test_publish_no_subscribers(self, event_bus, event_type, event_data):
        """Test publishing an event with no subscribers."""
        # This should not raise an exception
        await event_bus.publish(event_type, event_data)
    
    async def test_publish_with_subscribers(self, event_bus, event_type, event_data):
        """Test publishing an event with subscribers."""
        # Create mock listeners
        listener1 = Mock()
        listener1.on_event = AsyncMock()
        listener2 = Mock()
        listener2.on_event = AsyncMock()
        
        # Subscribe to an event
        event_bus.subscribe(event_type, listener1)
        event_bus.subscribe(event_type, listener2)
        
        # Publish an event
        await event_bus.publish(event_type, event_data)
        
        # Check that the listeners were called
        listener1.on_event.assert_called_once_with(event_type, event_data)
        listener2.on_event.assert_called_once_with(event_type, event_data)
    
    async def test_publish_with_exception(self, event_bus, event_type, event_data):
        """Test publishing an event where a subscriber raises an exception."""
        # Create mock listeners
        listener1 = Mock()
        listener1.on_event = AsyncMock(side_effect=Exception("Test exception"))
        listener2 = Mock()
        listener2.on_event = AsyncMock()
        
        # Subscribe to an event
        event_bus.subscribe(event_type, listener1)
        event_bus.subscribe(event_type, listener2)
        
        # Publish an event (should not raise an exception)
        await event_bus.publish(event_type, event_data)
        
        # Check that both listeners were called
        listener1.on_event.assert_called_once_with(event_type, event_data)
        listener2.on_event.assert_called_once_with(event_type, event_data)
    
    async def test_multiple_event_types(self, event_bus, event_data):
        """Test handling multiple event types."""
        listener = Mock()
        listener.on_event = AsyncMock()
        
        # Subscribe to multiple event types
        event_bus.subscribe(EventTypes.COMPONENT_INITIALIZED, listener)
        event_bus.subscribe(EventTypes.DOMAIN_CLASSIFIED, listener)
        
        # Publish events to both types
        await event_bus.publish(EventTypes.COMPONENT_INITIALIZED, event_data)
        await event_bus.publish(EventTypes.DOMAIN_CLASSIFIED, event_data)
        
        # Check that listener was called twice
        assert listener.on_event.call_count == 2
        
        # Check correct event types were passed
        call_args = listener.on_event.call_args_list
        assert call_args[0][0][0] == EventTypes.COMPONENT_INITIALIZED
        assert call_args[1][0][0] == EventTypes.DOMAIN_CLASSIFIED
