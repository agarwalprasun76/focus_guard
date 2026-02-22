"""Tests for tab_server storage module."""

import time
import pytest
from ..tab_server.storage import TabStorage, BrowserConnection
from ..tab_server.api_models import TabInfo, BrowserFamily


class TestTabStorage:
    """Tests for TabStorage class."""

    def test_init_creates_empty_storage(self):
        """Storage should start empty."""
        storage = TabStorage()
        snapshot = storage.get_snapshot()
        
        assert len(snapshot.tabs) == 0
        assert len(snapshot.browsers) == 0

    def test_update_tabs_stores_data(self):
        """Updating tabs should store the data."""
        storage = TabStorage()
        
        tabs = [
            TabInfo(
                id="1",
                url="https://example.com",
                title="Example",
                browser=BrowserFamily.CHROME,
                active=True,
            ),
            TabInfo(
                id="2",
                url="https://test.com",
                title="Test",
                browser=BrowserFamily.CHROME,
                active=False,
            ),
        ]
        
        storage.update_tabs(tabs, BrowserFamily.CHROME)
        snapshot = storage.get_snapshot()
        
        assert len(snapshot.tabs) == 2
        assert len(snapshot.browsers) == 1
        assert snapshot.browsers[0].browser == BrowserFamily.CHROME
        assert snapshot.browsers[0].connected is True

    def test_update_tabs_replaces_old_tabs(self):
        """Updating tabs should replace old tabs from same browser."""
        storage = TabStorage()
        
        # First update
        tabs1 = [
            TabInfo(id="1", url="https://old.com", title="Old", browser=BrowserFamily.CHROME),
        ]
        storage.update_tabs(tabs1, BrowserFamily.CHROME)
        
        # Second update
        tabs2 = [
            TabInfo(id="2", url="https://new.com", title="New", browser=BrowserFamily.CHROME),
        ]
        storage.update_tabs(tabs2, BrowserFamily.CHROME)
        
        snapshot = storage.get_snapshot()
        
        assert len(snapshot.tabs) == 1
        assert snapshot.tabs[0].id == "2"
        assert snapshot.tabs[0].url == "https://new.com"

    def test_multiple_browsers(self):
        """Storage should handle multiple browsers."""
        storage = TabStorage()
        
        chrome_tabs = [
            TabInfo(id="c1", url="https://chrome.com", title="Chrome", browser=BrowserFamily.CHROME),
        ]
        edge_tabs = [
            TabInfo(id="e1", url="https://edge.com", title="Edge", browser=BrowserFamily.EDGE),
        ]
        
        storage.update_tabs(chrome_tabs, BrowserFamily.CHROME)
        storage.update_tabs(edge_tabs, BrowserFamily.EDGE)
        
        snapshot = storage.get_snapshot()
        
        assert len(snapshot.tabs) == 2
        assert len(snapshot.browsers) == 2

    def test_get_active_tab(self):
        """Should return the active tab."""
        storage = TabStorage()
        
        tabs = [
            TabInfo(id="1", url="https://inactive.com", title="Inactive", browser=BrowserFamily.CHROME, active=False),
            TabInfo(id="2", url="https://active.com", title="Active", browser=BrowserFamily.CHROME, active=True),
        ]
        
        storage.update_tabs(tabs, BrowserFamily.CHROME)
        active = storage.get_active_tab()
        
        assert active is not None
        assert active.id == "2"
        assert active.active is True

    def test_get_active_tab_returns_none_when_no_active(self):
        """Should return None when no tab is active."""
        storage = TabStorage()
        
        tabs = [
            TabInfo(id="1", url="https://test.com", title="Test", browser=BrowserFamily.CHROME, active=False),
        ]
        
        storage.update_tabs(tabs, BrowserFamily.CHROME)
        active = storage.get_active_tab()
        
        assert active is None

    def test_get_tabs_by_browser(self):
        """Should filter tabs by browser."""
        storage = TabStorage()
        
        storage.update_tabs(
            [TabInfo(id="c1", url="https://c.com", title="C", browser=BrowserFamily.CHROME)],
            BrowserFamily.CHROME,
        )
        storage.update_tabs(
            [TabInfo(id="e1", url="https://e.com", title="E", browser=BrowserFamily.EDGE)],
            BrowserFamily.EDGE,
        )
        
        chrome_tabs = storage.get_tabs_by_browser(BrowserFamily.CHROME)
        edge_tabs = storage.get_tabs_by_browser(BrowserFamily.EDGE)
        
        assert len(chrome_tabs) == 1
        assert chrome_tabs[0].id == "c1"
        assert len(edge_tabs) == 1
        assert edge_tabs[0].id == "e1"

    def test_is_browser_connected(self):
        """Should correctly report browser connection status."""
        storage = TabStorage()
        
        assert storage.is_browser_connected(BrowserFamily.CHROME) is False
        
        storage.update_tabs(
            [TabInfo(id="1", url="https://test.com", title="Test", browser=BrowserFamily.CHROME)],
            BrowserFamily.CHROME,
        )
        
        assert storage.is_browser_connected(BrowserFamily.CHROME) is True
        assert storage.is_browser_connected(BrowserFamily.EDGE) is False

    def test_record_heartbeat(self):
        """Recording heartbeat should update connection status."""
        storage = TabStorage()
        
        # First add a browser
        storage.update_tabs(
            [TabInfo(id="1", url="https://test.com", title="Test", browser=BrowserFamily.CHROME)],
            BrowserFamily.CHROME,
        )
        
        # Record heartbeat
        storage.record_heartbeat(BrowserFamily.CHROME)
        
        status = storage.get_browser_status(BrowserFamily.CHROME)
        assert status is not None
        assert status.connected is True

    def test_clear(self):
        """Clear should remove all data."""
        storage = TabStorage()
        
        storage.update_tabs(
            [TabInfo(id="1", url="https://test.com", title="Test", browser=BrowserFamily.CHROME)],
            BrowserFamily.CHROME,
        )
        
        storage.clear()
        snapshot = storage.get_snapshot()
        
        assert len(snapshot.tabs) == 0
        assert len(snapshot.browsers) == 0

    def test_get_connected_browsers(self):
        """Should return list of connected browsers."""
        storage = TabStorage()
        
        storage.update_tabs(
            [TabInfo(id="1", url="https://c.com", title="C", browser=BrowserFamily.CHROME)],
            BrowserFamily.CHROME,
        )
        storage.update_tabs(
            [TabInfo(id="2", url="https://e.com", title="E", browser=BrowserFamily.EDGE)],
            BrowserFamily.EDGE,
        )
        
        connected = storage.get_connected_browsers()
        
        assert len(connected) == 2
        assert BrowserFamily.CHROME in connected
        assert BrowserFamily.EDGE in connected

    def test_record_error(self):
        """Should record errors for a browser."""
        storage = TabStorage()
        
        storage.update_tabs(
            [TabInfo(id="1", url="https://test.com", title="Test", browser=BrowserFamily.CHROME)],
            BrowserFamily.CHROME,
        )
        
        storage.record_error(BrowserFamily.CHROME, "Test error")
        
        status = storage.get_browser_status(BrowserFamily.CHROME)
        assert status is not None
        assert "Test error" in status.errors


class TestBrowserConnection:
    """Tests for BrowserConnection dataclass."""

    def test_is_connected_recent_heartbeat(self):
        """Should be connected with recent heartbeat."""
        conn = BrowserConnection(
            browser=BrowserFamily.CHROME,
            last_heartbeat=time.time(),
        )
        assert conn.is_connected is True

    def test_is_disconnected_old_heartbeat(self):
        """Should be disconnected with old heartbeat."""
        conn = BrowserConnection(
            browser=BrowserFamily.CHROME,
            last_heartbeat=time.time() - 60,  # 60 seconds ago
        )
        assert conn.is_connected is False
