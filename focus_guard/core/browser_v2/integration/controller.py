"""Integration controller for browser_v2 stack.

This module orchestrates installer strategies, tab server lifecycle, and telemetry
pipelines. It provides the main entry point for browser extension integration.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any

from ..tab_server import (
    TabServerRunner,
    ServerState,
    get_tab_server_runner,
    get_tab_storage,
    get_blocking_manager,
    TabInfo,
    BrowserFamily,
    TabsSnapshot,
)
from ..installer import (
    ExtensionInstaller,
    InstallMode,
    InstallationStatus,
    BrowserInfo,
    detect_browsers,
)

logger = logging.getLogger(__name__)


@dataclass
class BrowserIntegrationConfig:
    """Configuration surface for browser_v2 integration.

    Attributes:
        tab_server_host: Host address for the tab server.
        tab_server_port: Port for the tab server.
        auto_start: Whether to auto-start the tab server when initialized.
        install_mode: Installation mode for extensions.
        verify_connection_timeout: Timeout for verifying extension connections.
        enable_blocking: Whether to enable URL blocking.
    """

    tab_server_host: str = "127.0.0.1"
    tab_server_port: int = 5000
    auto_start: bool = True
    install_mode: InstallMode = InstallMode.AUTO
    verify_connection_timeout: float = 30.0
    enable_blocking: bool = True

    @property
    def tab_server_url(self) -> str:
        """Get the full tab server URL."""
        return f"http://{self.tab_server_host}:{self.tab_server_port}"


@dataclass
class IntegrationStatus:
    """Current status of the browser integration."""

    initialized: bool = False
    tab_server_running: bool = False
    tab_server_state: str = "stopped"
    connected_browsers: List[str] = field(default_factory=list)
    total_tabs: int = 0
    installation_status: Optional[InstallationStatus] = None
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "initialized": self.initialized,
            "tab_server_running": self.tab_server_running,
            "tab_server_state": self.tab_server_state,
            "connected_browsers": self.connected_browsers,
            "total_tabs": self.total_tabs,
            "installation_status": (
                self.installation_status.to_dict()
                if self.installation_status
                else None
            ),
            "last_updated": self.last_updated,
        }


class BrowserIntegrationController:
    """Entry point coordinating browser_v2 installer + tab server.

    This controller manages the complete browser integration lifecycle:
    - Starting and monitoring the tab server
    - Installing browser extensions
    - Tracking extension connections
    - Providing tab data and blocking decisions
    """

    def __init__(
        self,
        config: Optional[BrowserIntegrationConfig] = None,
        on_status_change: Optional[Callable[[IntegrationStatus], None]] = None,
    ) -> None:
        """Initialize the controller.

        Args:
            config: Configuration options.
            on_status_change: Optional callback for status updates.
        """
        self._config = config or BrowserIntegrationConfig()
        self._on_status_change = on_status_change
        self._initialized = False

        # Components (lazy initialization)
        self._server_runner: Optional[TabServerRunner] = None
        self._installer: Optional[ExtensionInstaller] = None

        # External integration hooks
        self._blocking_checker: Optional[Callable[[str, str], Any]] = None
        self._event_handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    @property
    def config(self) -> BrowserIntegrationConfig:
        """Return the active configuration."""
        return self._config

    @property
    def is_initialized(self) -> bool:
        """Check if the controller is initialized."""
        return self._initialized

    def initialize(self) -> bool:
        """Initialize the browser integration stack.

        This starts the tab server and prepares the installer.

        Returns:
            True if initialization succeeded.
        """
        if self._initialized:
            logger.debug("Already initialized")
            return True

        logger.info("Initializing browser_v2 integration")

        try:
            # Initialize tab server runner
            self._server_runner = get_tab_server_runner(
                host=self._config.tab_server_host,
                port=self._config.tab_server_port,
            )

            # Initialize installer
            self._installer = ExtensionInstaller(
                tab_server_url=self._config.tab_server_url,
                mode=self._config.install_mode,
            )

            # Auto-start tab server if configured
            if self._config.auto_start:
                if not self.ensure_tab_server():
                    logger.warning("Failed to start tab server during initialization")

            self._initialized = True
            self._notify_status_change()
            logger.info("Browser integration initialized successfully")
            return True

        except Exception as e:
            logger.exception("Failed to initialize browser integration: %s", e)
            return False

    def ensure_tab_server(self) -> bool:
        """Ensure the tab server is running.

        Returns:
            True if server is running.
        """
        if self._server_runner is None:
            self._server_runner = get_tab_server_runner(
                host=self._config.tab_server_host,
                port=self._config.tab_server_port,
            )

        if self._server_runner.is_running:
            return True

        return self._server_runner.start()

    def stop_tab_server(self) -> bool:
        """Stop the tab server.

        Returns:
            True if server stopped successfully.
        """
        if self._server_runner is None:
            return True
        return self._server_runner.stop()

    def install_extension(self, browser_family: Optional[str] = None) -> InstallationStatus:
        """Install extension for browser(s).

        Args:
            browser_family: Optional specific browser family (chrome, edge).
                If None, installs for all detected browsers.

        Returns:
            Installation status.
        """
        if self._installer is None:
            self._installer = ExtensionInstaller(
                tab_server_url=self._config.tab_server_url,
                mode=self._config.install_mode,
            )

        # Ensure tab server is running first
        self.ensure_tab_server()

        if browser_family:
            # Install for specific browser
            browsers = self._installer.detect_browsers()
            for browser in browsers:
                if browser.family == browser_family:
                    self._installer.install_for_browser(browser)
                    break
        else:
            # Install for all browsers
            self._installer.install_for_all_browsers()

        self._notify_status_change()
        return self._installer.status

    def verify_connections(self, timeout: Optional[float] = None) -> bool:
        """Verify extension connections.

        Args:
            timeout: Optional timeout override.

        Returns:
            True if all extensions are connected.
        """
        if self._installer is None:
            return False

        timeout = timeout or self._config.verify_connection_timeout
        result = self._installer.verify_all_connections(timeout=timeout)
        self._notify_status_change()
        return result

    def get_status(self) -> IntegrationStatus:
        """Get current integration status.

        Returns:
            Current status information.
        """
        storage = get_tab_storage()
        snapshot = storage.get_snapshot()

        server_state = "stopped"
        server_running = False
        if self._server_runner:
            server_state = self._server_runner.state.value
            server_running = self._server_runner.is_running

        connected = [
            b.browser.value if hasattr(b.browser, "value") else str(b.browser)
            for b in snapshot.browsers
            if b.connected
        ]

        return IntegrationStatus(
            initialized=self._initialized,
            tab_server_running=server_running,
            tab_server_state=server_state,
            connected_browsers=connected,
            total_tabs=len(snapshot.tabs),
            installation_status=self._installer.status if self._installer else None,
            last_updated=time.time(),
        )

    def get_tabs(self) -> TabsSnapshot:
        """Get current tab snapshot.

        Returns:
            Snapshot of all browser tabs.
        """
        storage = get_tab_storage()
        return storage.get_snapshot()

    def get_active_tab(self) -> Optional[TabInfo]:
        """Get the currently active tab.

        Returns:
            Active tab info or None.
        """
        storage = get_tab_storage()
        return storage.get_active_tab()

    def is_browser_connected(self, browser_family: str) -> bool:
        """Check if a browser extension is connected.

        Args:
            browser_family: Browser family to check (chrome, edge).

        Returns:
            True if connected.
        """
        storage = get_tab_storage()
        try:
            family = BrowserFamily(browser_family)
            return storage.is_browser_connected(family)
        except ValueError:
            return False

    def close_tab(
        self,
        tab_id: str,
        browser: str,
        reason: str = "blocked",
    ) -> bool:
        """Queue a command to close a tab.

        Args:
            tab_id: ID of the tab to close.
            browser: Browser name.
            reason: Reason for closing.

        Returns:
            True if command was queued.
        """
        # This would queue a command for the extension to process
        # Implementation depends on the command queue in tab server
        logger.info("Queueing close_tab command: tab=%s, browser=%s, reason=%s", 
                    tab_id, browser, reason)
        # TODO: Wire to command queue when tab server context is accessible
        return True

    def set_blocking_checker(
        self,
        checker: Callable[[str, str], Any],
    ) -> None:
        """Set external blocking checker.

        Args:
            checker: Callback that takes (url, domain) and returns blocking decision.
        """
        self._blocking_checker = checker
        blocking_manager = get_blocking_manager()
        blocking_manager.set_external_checker(checker)

    def add_event_handler(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Add handler for extension events.

        Args:
            event_type: Event type to handle (tab_created, tab_updated, etc.).
            handler: Callback function.
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def shutdown(self) -> None:
        """Shut down managed resources gracefully."""
        logger.info("Shutting down browser integration")

        if self._server_runner:
            self._server_runner.stop()

        self._initialized = False
        self._notify_status_change()

    def _notify_status_change(self) -> None:
        """Notify callback of status change."""
        if self._on_status_change:
            try:
                status = self.get_status()
                self._on_status_change(status)
            except Exception as e:
                logger.warning("Status change callback error: %s", e)


# Global singleton
_controller_instance: Optional[BrowserIntegrationController] = None


def get_browser_integration(
    config: Optional[BrowserIntegrationConfig] = None,
) -> BrowserIntegrationController:
    """Get the global BrowserIntegrationController singleton.

    Args:
        config: Optional configuration (only used on first call).

    Returns:
        The controller instance.
    """
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = BrowserIntegrationController(config=config)
    return _controller_instance


def initialize_browser_integration(
    config: Optional[BrowserIntegrationConfig] = None,
    install_extensions: bool = False,
) -> BrowserIntegrationController:
    """Initialize browser integration with optional extension installation.

    Args:
        config: Optional configuration.
        install_extensions: Whether to install extensions after initialization.

    Returns:
        Initialized controller.
    """
    controller = get_browser_integration(config)
    controller.initialize()

    if install_extensions:
        controller.install_extension()

    return controller
