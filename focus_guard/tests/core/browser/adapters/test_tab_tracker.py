"""Tests for the tab tracker adapter."""

import pytest
from unittest.mock import MagicMock, call
from focus_guard.core.browser.adapters.tab_tracker import DefaultTabTracker
from focus_guard.core.browser.models.tab import Tab, TabEvent

@pytest.fixture
def tab_tracker():
    """Fixture that provides a DefaultTabTracker instance."""
    return DefaultTabTracker(cache_ttl=0)  # Disable caching for tests

def test_start_stop(tab_tracker):
    """Test starting and stopping the tab tracker."""
    # Start the tracker
    assert tab_tracker.start() is True
    assert tab_tracker._running is True
    assert tab_tracker._thread.is_alive() is True
    
    # Stop the tracker
    tab_tracker.stop()
    assert tab_tracker._running is False
    assert tab_tracker._thread is None

def test_register_tab_event_handler(tab_tracker):
    """Test registering tab event handlers."""
    # Create a mock handler
    handler = MagicMock()
    
    # Register the handler for CREATED events (was TAB_OPENED)
    tab_tracker.register_tab_event_handler(TabEvent.CREATED, handler)
    
    # Verify the handler was registered
    assert handler in tab_tracker._event_handlers[TabEvent.CREATED]
    
    # Test registering an invalid event type
    with pytest.raises(ValueError):
        tab_tracker.register_tab_event_handler("INVALID_EVENT", handler)

def test_get_all_tabs(tab_tracker):
    """Test getting all tabs."""
    # Mock some tabs with all required parameters
    tab1 = Tab(
        id=1, 
        window_id=1, 
        url="https://example.com", 
        title="Example", 
        browser_id="test-browser",
        domain="example.com",
        is_active=True
    )
    tab2 = Tab(
        id=2, 
        window_id=1, 
        url="https://example.org", 
        title="Example Org", 
        browser_id="test-browser",
        domain="example.org",
        is_active=False
    )
    
    # Replace the _update_tab_data method to return our test data
    tab_tracker._tabs = {tab1.id: tab1, tab2.id: tab2}
    
    # Get all tabs
    tabs = tab_tracker.get_all_tabs()
    
    # Verify the results
    assert len(tabs) == 2
    assert all(isinstance(tab, Tab) for tab in tabs)
    assert tabs[0].id == 1
    assert tabs[1].id == 2

def test_get_active_tab(tab_tracker):
    """Test getting the active tab."""
    # Mock some tabs with all required parameters
    active_tab = Tab(
        id=1, 
        window_id=1,
        url="https://example.com", 
        title="Example", 
        browser_id="test-browser",
        domain="example.com",
        is_active=True
    )
    inactive_tab = Tab(
        id=2, 
        window_id=1,
        url="https://example.org", 
        title="Example Org", 
        browser_id="test-browser",
        domain="example.org",
        is_active=False
    )
    
    # Replace the _update_tab_data method to return our test data
    tab_tracker._tabs = {active_tab.id: active_tab, inactive_tab.id: inactive_tab}
    
    # Get the active tab
    result = tab_tracker.get_active_tab()
    
    # Verify the result
    assert result is not None
    assert result.id == 1
    assert result.is_active is True

def test_get_tabs_by_domain(tab_tracker):
    """Test getting tabs by domain."""
    # Mock some tabs with all required parameters
    tab1 = Tab(
        id=1, 
        window_id=1,
        url="https://example.com/page1", 
        title="Page 1", 
        browser_id="test-browser",
        domain="example.com",
        is_active=True
    )
    tab2 = Tab(
        id=2, 
        window_id=1,
        url="https://example.org/page1", 
        title="Org Page 1", 
        browser_id="test-browser",
        domain="example.org",
        is_active=False
    )
    tab3 = Tab(
        id=3, 
        window_id=1,
        url="https://example.com/page2", 
        title="Page 2", 
        browser_id="test-browser",
        domain="example.com",
        is_active=False
    )
    
    # Replace the _update_tab_data method to return our test data
    tab_tracker._tabs = {tab.id: tab for tab in [tab1, tab2, tab3]}
    
    # Get tabs by domain
    example_tabs = tab_tracker.get_tabs_by_domain("example.com")
    org_tabs = tab_tracker.get_tabs_by_domain("example.org")
    
    # Verify the results
    assert len(example_tabs) == 2
    assert all(tab.domain == "example.com" for tab in example_tabs)
    
    assert len(org_tabs) == 1
    assert org_tabs[0].domain == "example.org"

def test_event_handling(tab_tracker):
    """Test tab event handling."""
    # Create mock handlers
    created_handler = MagicMock()
    removed_handler = MagicMock()
    
    # Register the handlers (using correct event types)
    tab_tracker.register_tab_event_handler(TabEvent.CREATED, created_handler)
    tab_tracker.register_tab_event_handler(TabEvent.REMOVED, removed_handler)
    
    # Create a test tab with all required parameters
    test_tab = Tab(
        id=1,
        window_id=1,
        url="https://example.com",
        title="Example",
        browser_id="test-browser",
        domain="example.com"
    )
    
    # Trigger the handlers with correct event types
    tab_tracker._notify_event_handlers(TabEvent.CREATED, test_tab)
    tab_tracker._notify_event_handlers(TabEvent.REMOVED, test_tab)
    
    # Verify the handlers were called with the correct arguments
    created_handler.assert_called_once_with(test_tab)
    removed_handler.assert_called_once_with(test_tab)
    
    # Test error handling in handlers
    def failing_handler(tab):
        raise Exception("Handler error")
    
    tab_tracker.register_tab_event_handler(TabEvent.UPDATED, failing_handler)
    
    # This should not raise an exception
    tab_tracker._notify_event_handlers(TabEvent.UPDATED, test_tab)
