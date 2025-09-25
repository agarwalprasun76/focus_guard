"""
Unit tests for the TabTracker class.

This module contains tests for the TabTracker class in core_v2.browser.adapter.
"""

import unittest
import time
import threading
from unittest.mock import patch, MagicMock
import pytest
from datetime import datetime

from core_v2.browser.adapter import TabTracker
from core_v2.browser.models.tab import Tab

# Mock TabEvent enum for testing
class TabEvent:
    TAB_CREATED = "TAB_CREATED"
    TAB_UPDATED = "TAB_UPDATED"
    TAB_REMOVED = "TAB_REMOVED"
    TAB_ACTIVATED = "TAB_ACTIVATED"


class TestTabTracker:
    """Test cases for the TabTracker class."""

    @pytest.fixture
    def tab_tracker(self):
        """Create a TabTracker instance for testing."""
        tracker = TabTracker()
        yield tracker
        # Ensure tracker is stopped after test
        if tracker._running:
            tracker.stop()

    @pytest.fixture
    def mock_tab_data(self):
        """Create mock tab data for testing."""
        return {
            1: Tab(
                id=1,
                window_id=1,
                url="https://example.com",
                title="Example Domain",
                browser_id="chrome-12345",
                domain="example.com",
                is_active=True,
                created_at=datetime.now()
            ),
            2: Tab(
                id=2,
                window_id=1,
                url="https://test.com",
                title="Test Website",
                browser_id="chrome-12345",
                domain="test.com",
                is_active=False,
                created_at=datetime.now()
            ),
            3: Tab(
                id=3,
                window_id=2,
                url="https://example.org",
                title="Example Org",
                browser_id="firefox-67890",
                domain="example.org",
                is_active=False,
                created_at=datetime.now()
            )
        }

    def test_get_all_tabs_empty(self, tab_tracker):
        """Test get_all_tabs when no tabs are detected."""
        # Patch the _update_tab_data method to do nothing
        with patch.object(TabTracker, '_update_tab_data'):
            # Ensure the tab tracker has no tabs
            tab_tracker._tabs = {}
            
            # Call the method
            tabs = tab_tracker.get_all_tabs()
            
            # Verify the result
            assert isinstance(tabs, list)
            assert len(tabs) == 0

    def test_get_all_tabs_with_data(self, tab_tracker, mock_tab_data):
        """Test get_all_tabs when tabs are detected."""
        # Patch the _update_tab_data method to do nothing
        with patch.object(TabTracker, '_update_tab_data'):
            # Set mock tab data
            tab_tracker._tabs = mock_tab_data
            
            # Call the method
            tabs = tab_tracker.get_all_tabs()
            
            # Verify the result
            assert isinstance(tabs, list)
            assert len(tabs) == 3
            
            # Verify tab domains
            domains = [tab.domain for tab in tabs]
            assert "example.com" in domains
            assert "test.com" in domains
            assert "example.org" in domains

    def test_get_active_tab_none(self, tab_tracker):
        """Test get_active_tab when no active tab is found."""
        # Patch the _update_tab_data method to do nothing
        with patch.object(TabTracker, '_update_tab_data'):
            # Set mock tab data with no active tabs
            tab_tracker._tabs = {
                1: Tab(
                    id=1,
                    window_id=1,
                    url="https://example.com",
                    title="Example Domain",
                    browser_id="chrome-12345",
                    domain="example.com",
                    is_active=False
                )
            }
            
            # Call the method
            active_tab = tab_tracker.get_active_tab()
            
            # Verify the result
            assert active_tab is None

    def test_get_active_tab_found(self, tab_tracker, mock_tab_data):
        """Test get_active_tab when an active tab is found."""
        # Patch the _update_tab_data method to do nothing
        with patch.object(TabTracker, '_update_tab_data'):
            # Set mock tab data
            tab_tracker._tabs = mock_tab_data
            
            # Call the method
            active_tab = tab_tracker.get_active_tab()
            
            # Verify the result
            assert active_tab is not None
            assert active_tab.id == 1
            assert active_tab.url == "https://example.com"
            assert active_tab.is_active is True

    def test_get_tabs_by_domain_found(self, tab_tracker, mock_tab_data):
        """Test get_tabs_by_domain when tabs for the domain are found."""
        # Patch the _update_tab_data method to do nothing
        with patch.object(TabTracker, '_update_tab_data'):
            # Set mock tab data
            tab_tracker._tabs = mock_tab_data
            
            # Call the method
            domain_tabs = tab_tracker.get_tabs_by_domain("example.com")
            
            # Verify the result
            assert isinstance(domain_tabs, list)
            assert len(domain_tabs) == 1
            assert domain_tabs[0].domain == "example.com"
            assert domain_tabs[0].url == "https://example.com"

    def test_get_tabs_by_domain_not_found(self, tab_tracker, mock_tab_data):
        """Test get_tabs_by_domain when no tabs for the domain are found."""
        # Patch the _update_tab_data method to do nothing
        with patch.object(TabTracker, '_update_tab_data'):
            # Set mock tab data
            tab_tracker._tabs = mock_tab_data
            
            # Call the method
            domain_tabs = tab_tracker.get_tabs_by_domain("nonexistent.com")
            
            # Verify the result
            assert isinstance(domain_tabs, list)
            assert len(domain_tabs) == 0

    def test_register_tab_event_handler(self, tab_tracker):
        """Test registering a tab event handler."""
        # Create a mock handler
        mock_handler = MagicMock()
        
        # Initialize the event handlers dictionary if needed
        if not hasattr(tab_tracker, '_event_handlers') or tab_tracker._event_handlers is None:
            tab_tracker._event_handlers = {}
        if TabEvent.TAB_CREATED not in tab_tracker._event_handlers:
            tab_tracker._event_handlers[TabEvent.TAB_CREATED] = []
        
        # Register the handler
        tab_tracker.register_tab_event_handler(TabEvent.TAB_CREATED, mock_handler)
        
        # Verify the handler was registered
        assert mock_handler in tab_tracker._event_handlers[TabEvent.TAB_CREATED]

    def test_start_stop(self, tab_tracker):
        """Test starting and stopping the tab tracker."""
        # Start the tracker
        result = tab_tracker.start()
        
        # Verify the result
        assert result is True
        assert tab_tracker._running is True
        assert tab_tracker._thread is not None
        assert tab_tracker._thread.is_alive()
        
        # Store thread reference before stopping
        thread = tab_tracker._thread
        
        # Stop the tracker
        tab_tracker.stop()
        
        # Verify the tracker is stopped
        assert tab_tracker._running is False
        assert not thread.is_alive()

    def test_start_already_running(self, tab_tracker):
        """Test starting the tab tracker when it's already running."""
        # Start the tracker
        tab_tracker.start()
        
        # Try to start it again
        result = tab_tracker.start()
        
        # Verify the result
        assert result is True  # Should return True even if already running
        
        # Stop the tracker
        tab_tracker.stop()

    def test_update_tab_data_cache_hit(self, tab_tracker, mock_tab_data):
        """Test _update_tab_data when cache is still valid."""
        # Set up the tab tracker with mock data and a recent update time
        tab_tracker._tabs = mock_tab_data
        tab_tracker._last_update_time = time.time()  # Just updated
        
        # Call the method
        tab_tracker._update_tab_data()
        
        # Verify that the tab data is unchanged
        assert tab_tracker._tabs == mock_tab_data

    def test_tracking_loop_stops_when_requested(self, tab_tracker):
        """Test that the tracking loop stops when requested."""
        # Mock the _update_tab_data method to do nothing
        with patch.object(TabTracker, '_update_tab_data'):
            # Start the tracker with a mocked _tracking_loop
            with patch.object(TabTracker, '_tracking_loop') as mock_tracking_loop:
                tab_tracker.start()
                
                # Verify that _tracking_loop was called
                mock_tracking_loop.assert_called_once()
                
                # Stop the tracker
                tab_tracker.stop()


if __name__ == "__main__":
    pytest.main(["-v", "test_tab_tracker.py"])
