"""Thread-safe tab data storage for browser_v2 tab server."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .api_models import TabInfo, BrowserFamily, BrowserStatus, TabsSnapshot


@dataclass
class BrowserConnection:
    """Tracks a connected browser instance."""

    browser: BrowserFamily
    last_heartbeat: float
    extension_version: Optional[str] = None
    tab_ids: Set[str] = field(default_factory=set)
    errors: List[str] = field(default_factory=list)

    @property
    def is_connected(self) -> bool:
        """Consider connected if heartbeat within last 30 seconds."""
        return (time.time() - self.last_heartbeat) < 30.0


class TabStorage:
    """Thread-safe storage for browser tab data.

    Provides atomic operations for tab updates and queries, with automatic
    cleanup of stale data.
    """

    def __init__(self, stale_threshold_seconds: float = 60.0) -> None:
        self._lock = threading.RLock()
        self._tabs: Dict[str, TabInfo] = {}
        self._browsers: Dict[BrowserFamily, BrowserConnection] = {}
        self._stale_threshold = stale_threshold_seconds
        self._last_cleanup = time.time()

    def update_tabs(
        self,
        tabs: List[TabInfo],
        browser: BrowserFamily,
        extension_version: Optional[str] = None,
    ) -> None:
        """Update tab data from a browser extension snapshot.

        Args:
            tabs: List of tab info from the extension.
            browser: The browser family reporting the tabs.
            extension_version: Optional version string of the extension.
        """
        now = time.time()
        with self._lock:
            # Update browser connection
            if browser not in self._browsers:
                self._browsers[browser] = BrowserConnection(
                    browser=browser,
                    last_heartbeat=now,
                    extension_version=extension_version,
                )
            else:
                self._browsers[browser].last_heartbeat = now
                if extension_version:
                    self._browsers[browser].extension_version = extension_version

            # Clear old tabs from this browser
            old_tab_ids = self._browsers[browser].tab_ids.copy()
            for tab_id in old_tab_ids:
                if tab_id in self._tabs:
                    del self._tabs[tab_id]

            # Add new tabs
            new_tab_ids: Set[str] = set()
            for tab in tabs:
                tab.last_updated = now
                self._tabs[tab.id] = tab
                new_tab_ids.add(tab.id)

            self._browsers[browser].tab_ids = new_tab_ids

            # Periodic cleanup
            if now - self._last_cleanup > 30.0:
                self._cleanup_stale_data(now)
                self._last_cleanup = now

    def record_heartbeat(self, browser: BrowserFamily) -> None:
        """Record a heartbeat from a browser extension."""
        now = time.time()
        with self._lock:
            if browser in self._browsers:
                self._browsers[browser].last_heartbeat = now
            else:
                self._browsers[browser] = BrowserConnection(
                    browser=browser,
                    last_heartbeat=now,
                )

    def get_snapshot(self) -> TabsSnapshot:
        """Get a snapshot of all current tab data."""
        now = time.time()
        with self._lock:
            tabs = list(self._tabs.values())
            browsers = [
                BrowserStatus(
                    browser=conn.browser,
                    connected=conn.is_connected,
                    last_heartbeat=conn.last_heartbeat,
                    extension_version=conn.extension_version,
                    errors=conn.errors.copy(),
                )
                for conn in self._browsers.values()
            ]
            return TabsSnapshot(tabs=tabs, browsers=browsers, generated_at=now)

    def get_active_tab(self) -> Optional[TabInfo]:
        """Get the currently active tab across all browsers."""
        with self._lock:
            for tab in self._tabs.values():
                if tab.active:
                    return tab
            return None

    def get_tabs_by_browser(self, browser: BrowserFamily) -> List[TabInfo]:
        """Get all tabs for a specific browser."""
        with self._lock:
            return [tab for tab in self._tabs.values() if tab.browser == browser]

    def get_browser_status(self, browser: BrowserFamily) -> Optional[BrowserStatus]:
        """Get connection status for a specific browser."""
        with self._lock:
            conn = self._browsers.get(browser)
            if conn is None:
                return None
            return BrowserStatus(
                browser=conn.browser,
                connected=conn.is_connected,
                last_heartbeat=conn.last_heartbeat,
                extension_version=conn.extension_version,
                errors=conn.errors.copy(),
            )

    def is_browser_connected(self, browser: BrowserFamily) -> bool:
        """Check if a browser extension is currently connected."""
        with self._lock:
            conn = self._browsers.get(browser)
            return conn is not None and conn.is_connected

    def get_connected_browsers(self) -> List[BrowserFamily]:
        """Get list of currently connected browsers."""
        with self._lock:
            return [
                browser
                for browser, conn in self._browsers.items()
                if conn.is_connected
            ]

    def record_error(self, browser: BrowserFamily, error: str) -> None:
        """Record an error for a browser connection."""
        with self._lock:
            if browser in self._browsers:
                self._browsers[browser].errors.append(error)
                # Keep only last 10 errors
                if len(self._browsers[browser].errors) > 10:
                    self._browsers[browser].errors = self._browsers[browser].errors[-10:]

    def clear(self) -> None:
        """Clear all stored data."""
        with self._lock:
            self._tabs.clear()
            self._browsers.clear()

    def _cleanup_stale_data(self, now: float) -> None:
        """Remove stale tabs and disconnected browsers."""
        stale_tab_ids = [
            tab_id
            for tab_id, tab in self._tabs.items()
            if tab.last_updated and (now - tab.last_updated) > self._stale_threshold
        ]
        for tab_id in stale_tab_ids:
            del self._tabs[tab_id]

        # Update browser tab sets
        for conn in self._browsers.values():
            conn.tab_ids = {tid for tid in conn.tab_ids if tid in self._tabs}


# Global singleton instance
_storage_instance: Optional[TabStorage] = None
_storage_lock = threading.Lock()


def get_tab_storage() -> TabStorage:
    """Get the global TabStorage singleton."""
    global _storage_instance
    if _storage_instance is None:
        with _storage_lock:
            if _storage_instance is None:
                _storage_instance = TabStorage()
    return _storage_instance
