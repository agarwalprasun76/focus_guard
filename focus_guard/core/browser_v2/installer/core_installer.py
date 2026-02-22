"""Core installer orchestrating extension installation strategies.

This module provides the main entry point for extension installation,
coordinating strategy selection, privilege handling, and status reporting.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable

from .strategies import (
    InstallerStrategy,
    InstallResult,
    InstallStatus,
    BrowserInfo,
    DevUnpackedStrategy,
    StoreInstallStrategy,
    detect_browsers,
)
from focus_guard.core.browser_v2.installer.strategies import StoreInstallStrategy
from focus_guard.core.tab_server_endpoint import resolve_tab_server_base_url

logger = logging.getLogger(__name__)


class InstallMode(str, Enum):
    """Installation mode selection."""

    AUTO = "auto"  # Automatically select best strategy
    STORE = "store"  # Prefer store installation
    DEV = "dev"  # Use developer mode
    ENTERPRISE = "enterprise"  # Use enterprise policy


@dataclass
class InstallationStatus:
    """Overall installation status across browsers."""

    browsers: Dict[str, InstallResult] = field(default_factory=dict)
    all_connected: bool = False
    any_connected: bool = False
    pending_user_action: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "browsers": {
                name: {
                    "success": r.success,
                    "status": r.status.value,
                    "message": r.message,
                    "store_url": r.store_url,
                    "requires_user_action": r.requires_user_action,
                    "error": r.error,
                }
                for name, r in self.browsers.items()
            },
            "all_connected": self.all_connected,
            "any_connected": self.any_connected,
            "pending_user_action": self.pending_user_action,
            "timestamp": self.timestamp,
        }


class ExtensionInstaller:
    """Orchestrates browser extension installation.

    Coordinates strategy selection, browser detection, installation attempts,
    and verification of extension connections.
    """

    def __init__(
        self,
        extension_path: Optional[Path] = None,
        tab_server_url: Optional[str] = None,
        mode: InstallMode = InstallMode.AUTO,
        on_status_change: Optional[Callable[[InstallationStatus], None]] = None,
    ) -> None:
        """Initialize the installer.

        Args:
            extension_path: Path to the extension directory.
            tab_server_url: URL of the tab server for verification.
            mode: Installation mode to use.
            on_status_change: Optional callback for status updates.
        """
        self._extension_path = extension_path or self._find_extension_path()
        self._tab_server_url = tab_server_url or resolve_tab_server_base_url()
        self._mode = mode
        self._on_status_change = on_status_change
        self._status = InstallationStatus()
        self._strategies: Dict[str, InstallerStrategy] = {
            "dev": DevUnpackedStrategy(),
            "store": StoreInstallStrategy(),
        }

    @property
    def extension_path(self) -> Optional[Path]:
        """Get the extension path."""
        return self._extension_path

    @property
    def status(self) -> InstallationStatus:
        """Get current installation status."""
        return self._status

    def detect_browsers(self) -> List[BrowserInfo]:
        """Detect installed browsers."""
        return detect_browsers()

    def install_for_browser(
        self,
        browser: BrowserInfo,
        strategy: Optional[InstallerStrategy] = None,
    ) -> InstallResult:
        """Install extension for a specific browser.

        Args:
            browser: Target browser information.
            strategy: Optional specific strategy to use.

        Returns:
            InstallResult with the outcome.
        """
        if not self._extension_path or not self._extension_path.exists():
            return InstallResult(
                success=False,
                status=InstallStatus.FAILED,
                browser=browser.name,
                error="Extension path not found",
            )

        # Select strategy
        if strategy is None:
            strategy = self._select_strategy(browser)

        logger.info(
            "Installing extension for %s using %s strategy",
            browser.name,
            strategy.name,
        )

        # Attempt installation
        result = strategy.install(browser, self._extension_path)
        self._status.browsers[browser.name] = result
        self._update_status_flags()
        self._notify_status_change()

        return result

    def install_for_all_browsers(self) -> InstallationStatus:
        """Install extension for all detected browsers.

        Returns:
            Overall installation status.
        """
        browsers = self.detect_browsers()
        
        if not browsers:
            logger.warning("No supported browsers detected")
            return self._status

        for browser in browsers:
            self.install_for_browser(browser)

        return self._status

    def verify_connection(
        self,
        browser: BrowserInfo,
        timeout: float = 30.0,
        poll_interval: float = 2.0,
    ) -> bool:
        """Wait for extension to connect to tab server.

        Args:
            browser: Browser to verify.
            timeout: Maximum time to wait in seconds.
            poll_interval: Time between verification attempts.

        Returns:
            True if extension connected within timeout.
        """
        strategy = self._select_strategy(browser)
        deadline = time.time() + timeout

        while time.time() < deadline:
            if strategy.verify(browser, self._tab_server_url):
                # Update status
                if browser.name in self._status.browsers:
                    self._status.browsers[browser.name] = InstallResult(
                        success=True,
                        status=InstallStatus.CONNECTED,
                        browser=browser.name,
                        message="Extension connected successfully",
                    )
                    self._update_status_flags()
                    self._notify_status_change()
                return True
            time.sleep(poll_interval)

        return False

    def verify_all_connections(self, timeout: float = 30.0) -> bool:
        """Verify all installed extensions are connected.

        Args:
            timeout: Maximum time to wait for each browser.

        Returns:
            True if all extensions connected.
        """
        browsers = self.detect_browsers()
        all_connected = True

        for browser in browsers:
            if not self.verify_connection(browser, timeout=timeout):
                all_connected = False

        return all_connected

    def get_store_urls(self) -> Dict[str, Optional[str]]:
        """Get store URLs for all supported browsers.

        Returns:
            Dictionary mapping browser family to store URL.
        """
        return {
            "chrome": StoreInstallStrategy.get_store_url("chrome"),
            "edge": StoreInstallStrategy.get_store_url("edge"),
        }

    def is_store_published(self, browser_family: str) -> bool:
        """Check if extension is published for a browser."""
        return StoreInstallStrategy.is_published(browser_family)

    def _select_strategy(self, browser: BrowserInfo) -> InstallerStrategy:
        """Select the best strategy for a browser."""
        if self._mode == InstallMode.DEV:
            return self._strategies["dev"]
        elif self._mode == InstallMode.STORE:
            return self._strategies["store"]
        elif self._mode == InstallMode.AUTO:
            # Prefer store if published, otherwise dev
            if StoreInstallStrategy.is_published(browser.family):
                return self._strategies["store"]
            return self._strategies["dev"]
        else:
            return self._strategies["dev"]

    def _find_extension_path(self) -> Optional[Path]:
        """Find the extension directory."""
        # Try common locations relative to this file
        possible_paths = [
            Path(__file__).parent.parent.parent / "browser" / "extension" / "webextension_mv3",
            Path(__file__).parent.parent / "extension" / "webextension_mv3",
        ]

        for path in possible_paths:
            if path.exists() and (path / "manifest.json").exists():
                return path

        return None

    def _update_status_flags(self) -> None:
        """Update aggregate status flags."""
        results = list(self._status.browsers.values())
        
        if not results:
            self._status.all_connected = False
            self._status.any_connected = False
            self._status.pending_user_action = False
            return

        connected = [r for r in results if r.status == InstallStatus.CONNECTED]
        pending = [r for r in results if r.requires_user_action]

        self._status.all_connected = len(connected) == len(results)
        self._status.any_connected = len(connected) > 0
        self._status.pending_user_action = len(pending) > 0
        self._status.timestamp = time.time()

    def _notify_status_change(self) -> None:
        """Notify callback of status change."""
        if self._on_status_change:
            try:
                self._on_status_change(self._status)
            except Exception as e:
                logger.warning("Status change callback error: %s", e)


# Convenience functions

def install_extension(
    mode: InstallMode = InstallMode.AUTO,
    wait_for_connection: bool = True,
    timeout: float = 30.0,
) -> InstallationStatus:
    """Install browser extension with default settings.

    Args:
        mode: Installation mode to use.
        wait_for_connection: Whether to wait for extension to connect.
        timeout: Connection timeout in seconds.

    Returns:
        Installation status.
    """
    installer = ExtensionInstaller(mode=mode)
    status = installer.install_for_all_browsers()

    if wait_for_connection and status.any_connected is False:
        installer.verify_all_connections(timeout=timeout)

    return installer.status


def get_extension_status(tab_server_url: Optional[str] = None) -> dict:
    """Get current extension connection status.

    Args:
        tab_server_url: URL of the tab server.

    Returns:
        Status dictionary with connected browsers.
    """
    import urllib.request
    import urllib.error
    import json

    resolved_tab_server_url = tab_server_url or resolve_tab_server_base_url()

    try:
        with urllib.request.urlopen(f"{resolved_tab_server_url}/api/status", timeout=2) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as e:
        logger.debug("Failed to get status: %s", e)

    return {"connected_browsers": [], "error": "Tab server not responding"}
