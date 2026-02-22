"""Tab server process runner and lifecycle management."""

from __future__ import annotations

import logging
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from focus_guard.core.tab_server_endpoint import DEFAULT_TAB_SERVER_HOST
from focus_guard.core.tab_server_endpoint import DEFAULT_TAB_SERVER_PORT

logger = logging.getLogger(__name__)


class ServerState(str, Enum):
    """States of the tab server process."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServerStatus:
    """Status information for the tab server."""

    state: ServerState
    port: int
    pid: Optional[int] = None
    uptime_seconds: float = 0.0
    error_message: Optional[str] = None
    last_health_check: Optional[float] = None


class TabServerRunner:
    """Manages the tab server process lifecycle.

    Handles starting, stopping, health monitoring, and auto-restart of the
    tab server process.
    """

    def __init__(
        self,
        host: str = DEFAULT_TAB_SERVER_HOST,
        port: int = DEFAULT_TAB_SERVER_PORT,
        auto_restart: bool = True,
        health_check_interval: float = 10.0,
        on_state_change: Optional[Callable[[ServerState], None]] = None,
        use_persistent_blocking: bool = True,
        blocking_config_path: Optional[Path] = None,
    ) -> None:
        """Initialize the server runner.

        Args:
            host: Host address to bind to.
            port: Port to listen on.
            auto_restart: Whether to auto-restart on crash.
            health_check_interval: Seconds between health checks.
            on_state_change: Optional callback for state changes.
            use_persistent_blocking: Use CoreBlockingAdapter for persistent rules.
            blocking_config_path: Path to blocking config file (if persistent).
        """
        self._host = host
        self._port = port
        self._auto_restart = auto_restart
        self._health_check_interval = health_check_interval
        self._on_state_change = on_state_change
        self._use_persistent_blocking = use_persistent_blocking
        self._blocking_config_path = blocking_config_path

        self._state = ServerState.STOPPED
        self._server_thread: Optional[threading.Thread] = None
        self._health_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._start_time: Optional[float] = None
        self._last_health_check: Optional[float] = None
        self._error_message: Optional[str] = None
        self._lock = threading.Lock()

        # Server instance (when running in-process)
        self._server: Optional[object] = None
        
        # Core blocking adapter (for persistent blocking)
        self._core_blocking_adapter: Optional[object] = None

    @property
    def state(self) -> ServerState:
        """Get current server state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._state == ServerState.RUNNING

    def get_status(self) -> ServerStatus:
        """Get detailed server status."""
        with self._lock:
            uptime = 0.0
            if self._start_time and self._state == ServerState.RUNNING:
                uptime = time.time() - self._start_time

            return ServerStatus(
                state=self._state,
                port=self._port,
                uptime_seconds=uptime,
                error_message=self._error_message,
                last_health_check=self._last_health_check,
            )

    def start(self) -> bool:
        """Start the tab server.

        Returns:
            True if server started successfully.
        """
        with self._lock:
            if self._state in (ServerState.RUNNING, ServerState.STARTING):
                logger.debug("Server already running or starting")
                return True

            self._set_state(ServerState.STARTING)
            self._shutdown_event.clear()
            self._error_message = None

        try:
            # Check if port is available
            if not self._is_port_available():
                # Port in use - check if it's our server
                if self._check_health():
                    logger.info("Tab server already running on port %d", self._port)
                    self._set_state(ServerState.RUNNING)
                    self._start_time = time.time()
                    self._start_health_monitor()
                    self._start_heartbeat_monitor()
                    return True
                else:
                    self._set_state(ServerState.ERROR)
                    self._error_message = f"Port {self._port} is in use by another process"
                    return False

            # Start server in background thread
            self._server_thread = threading.Thread(
                target=self._run_server,
                name="TabServerRunner",
                daemon=True,
            )
            self._server_thread.start()

            # Wait for server to be ready
            if not self._wait_for_ready(timeout=5.0):
                self._set_state(ServerState.ERROR)
                self._error_message = "Server failed to start within timeout"
                return False

            self._set_state(ServerState.RUNNING)
            self._start_time = time.time()
            self._start_health_monitor()
            self._start_heartbeat_monitor()
            self._start_security_monitors()
            logger.info("Tab server started on %s:%d", self._host, self._port)
            return True

        except Exception as e:
            logger.exception("Failed to start tab server: %s", e)
            self._set_state(ServerState.ERROR)
            self._error_message = str(e)
            return False

    def stop(self) -> bool:
        """Stop the tab server.

        Returns:
            True if server stopped successfully.
        """
        with self._lock:
            if self._state == ServerState.STOPPED:
                return True

            self._set_state(ServerState.STOPPING)

        self._shutdown_event.set()

        # Stop heartbeat monitor
        try:
            from .heartbeat_monitor import get_heartbeat_monitor
            get_heartbeat_monitor().stop()
        except Exception:
            pass

        # Stop security monitors
        self._stop_security_monitors()

        # Stop health monitor
        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=2.0)

        # Stop server
        if self._server:
            try:
                self._server.shutdown()
            except Exception as e:
                logger.warning("Error shutting down server: %s", e)

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5.0)

        self._server = None
        self._server_thread = None
        self._health_thread = None
        self._start_time = None
        self._set_state(ServerState.STOPPED)
        logger.info("Tab server stopped")
        return True

    def restart(self) -> bool:
        """Restart the tab server."""
        self.stop()
        time.sleep(0.5)
        return self.start()

    def _run_server(self) -> None:
        """Run the HTTP server (called in background thread)."""
        from .server import TabServer, TabServerContext
        from .storage import get_tab_storage
        from .blocking import get_blocking_manager

        storage = get_tab_storage()
        blocking = get_blocking_manager()

        def health_provider() -> dict:
            status = self.get_status()
            return {
                "status": "healthy" if status.state == ServerState.RUNNING else "unhealthy",
                "uptime_seconds": status.uptime_seconds,
                "connected_browsers": len(storage.get_connected_browsers()),
            }

        def tabs_provider():
            return storage.get_snapshot()

        def command_handler(request):
            from .api_models import CommandResult
            # Placeholder - will be wired to actual command processing
            logger.info("Received command: %s", request.action)
            return CommandResult(
                success=True,
                action=request.action,
                message="Command queued",
            )

        def tabs_updater(data: dict) -> None:
            """Process tab update from extension."""
            from .api_models import TabInfo, BrowserFamily
            
            # Extract browser info
            browser_info = data.get("browser", {})
            browser_name = browser_info.get("name", "").lower() if isinstance(browser_info, dict) else str(browser_info).lower()
            
            if "edge" in browser_name:
                browser = BrowserFamily.EDGE
            elif "chrome" in browser_name:
                browser = BrowserFamily.CHROME
            else:
                browser = BrowserFamily.CHROME

            # Convert tabs
            raw_tabs = data.get("tabs", [])
            tabs = []
            for raw_tab in raw_tabs:
                try:
                    tab = TabInfo(
                        id=str(raw_tab.get("id", "")),
                        url=raw_tab.get("url", ""),
                        title=raw_tab.get("title", ""),
                        browser=browser,
                        window_id=str(raw_tab.get("windowId", "")) if raw_tab.get("windowId") else None,
                        active=raw_tab.get("active", False),
                        incognito=raw_tab.get("incognito", False),
                    )
                    tabs.append(tab)
                except Exception as e:
                    logger.warning("Failed to parse tab: %s", e)

            # Update storage
            storage.update_tabs(tabs, browser)
            logger.debug("Updated %d tabs for %s", len(tabs), browser.value)

        # Always enable classification-based blocking on the in-memory BlockingManager
        # This ensures classification works regardless of persistent blocking mode
        try:
            from .classification_blocker import setup_classification_blocking, get_classification_blocker
            setup_classification_blocking()
            classification_blocker = get_classification_blocker()
            logger.info("Classification-based blocking enabled")
        except Exception as e:
            logger.warning("Could not enable classification-based blocking: %s", e)
            classification_blocker = None

        # Set up blocking based on persistence mode
        if self._use_persistent_blocking:
            # Try to use CoreBlockingAdapter for persistent rules
            try:
                from ..integration.adapters import CoreBlockingAdapter
                
                self._core_blocking_adapter = CoreBlockingAdapter(
                    config_path=self._blocking_config_path
                )
                if self._core_blocking_adapter.initialize():
                    logger.info("Using CoreBlockingAdapter for persistent blocking")
                    
                    def blocking_checker(url: str, domain: str, title: str = "", tab_id: int = None):
                        # First check persistent blocking rules
                        decision = self._core_blocking_adapter.should_block(url, domain)
                        if decision.should_block:
                            return decision
                        # Fall back to classification-based blocking (with title/tab_id for search context)
                        if classification_blocker is not None:
                            return classification_blocker.check_blocking(url, domain, title, tab_id)
                        return decision
                    
                    def rules_provider():
                        return self._core_blocking_adapter.get_rules_as_list()
                    
                    def rule_adder(domain: str, reason: str) -> None:
                        self._core_blocking_adapter.add_blocked_domain(domain, reason)
                        logger.info("Added persistent blocking rule for %s: %s", domain, reason)
                    
                    def rule_remover(domain: str) -> None:
                        self._core_blocking_adapter.remove_blocked_domain(domain)
                        logger.info("Removed persistent blocking rule for %s", domain)
                else:
                    logger.warning("CoreBlockingAdapter init failed, falling back to in-memory")
                    self._use_persistent_blocking = False
                    self._core_blocking_adapter = None
            except ImportError as e:
                logger.warning("Could not import CoreBlockingAdapter: %s, using in-memory", e)
                self._use_persistent_blocking = False
                self._core_blocking_adapter = None
        
        # Fall back to in-memory blocking if persistent not available
        if not self._use_persistent_blocking or self._core_blocking_adapter is None:
            def blocking_checker(url: str, domain: str, title: str = "", tab_id: int = None):
                # Use classification blocker if available (with title/tab_id for search context)
                if classification_blocker is not None:
                    return classification_blocker.check_blocking(url, domain, title, tab_id)
                return blocking.should_block(url, domain)

            def rules_provider():
                return [{"domain": r.domain, "reason": r.reason} for r in blocking.get_rules()]

            def rule_adder(domain: str, reason: str) -> None:
                from .blocking import BlockingRule
                blocking.add_rule(BlockingRule(domain=domain, reason=reason))
                logger.info("Added blocking rule for %s: %s", domain, reason)

            def rule_remover(domain: str) -> None:
                blocking.remove_rule(domain)
                logger.info("Removed blocking rule for %s", domain)

        context = TabServerContext(
            health_provider=health_provider,
            tabs_provider=tabs_provider,
            command_handler=command_handler,
            tabs_updater=tabs_updater,
            blocking_checker=blocking_checker,
            rules_provider=rules_provider,
            rule_adder=rule_adder,
            rule_remover=rule_remover,
        )

        try:
            self._server = TabServer((self._host, self._port), context)
            logger.debug("Server created, starting serve_forever")
            self._server.serve_forever()
        except Exception as e:
            if not self._shutdown_event.is_set():
                logger.exception("Server error: %s", e)
                self._error_message = str(e)
                self._set_state(ServerState.ERROR)

    def _wait_for_ready(self, timeout: float) -> bool:
        """Wait for server to be ready to accept connections."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._check_health():
                return True
            time.sleep(0.1)
        return False

    def _check_health(self) -> bool:
        """Check if server is responding to health checks."""
        import urllib.request
        import urllib.error

        try:
            url = f"http://{self._host}:{self._port}/api/health"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                self._last_health_check = time.time()
                return response.status == 200
        except (urllib.error.URLError, OSError):
            return False

    def _is_port_available(self) -> bool:
        """Check if the port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self._host, self._port))
                return True
        except OSError:
            return False

    def _start_heartbeat_monitor(self) -> None:
        """Start the extension heartbeat monitor (detects extension removal)."""
        try:
            from .heartbeat_monitor import get_heartbeat_monitor
            monitor = get_heartbeat_monitor()
            if not monitor.is_running:
                monitor.start()
        except Exception as e:
            logger.warning("Could not start heartbeat monitor: %s", e)

    def _start_health_monitor(self) -> None:
        """Start the health monitoring thread."""
        if self._health_thread and self._health_thread.is_alive():
            return

        self._health_thread = threading.Thread(
            target=self._health_monitor_loop,
            name="TabServerHealthMonitor",
            daemon=True,
        )
        self._health_thread.start()

    def _health_monitor_loop(self) -> None:
        """Background loop for health monitoring."""
        consecutive_failures = 0
        max_failures = 3

        while not self._shutdown_event.is_set():
            self._shutdown_event.wait(self._health_check_interval)
            if self._shutdown_event.is_set():
                break

            if self._state != ServerState.RUNNING:
                continue

            if self._check_health():
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                logger.warning(
                    "Health check failed (%d/%d)",
                    consecutive_failures,
                    max_failures,
                )

                if consecutive_failures >= max_failures:
                    logger.error("Server unresponsive, attempting restart")
                    if self._auto_restart:
                        self._set_state(ServerState.ERROR)
                        self._error_message = "Server became unresponsive"
                        # Attempt restart
                        self.stop()
                        time.sleep(1.0)
                        if self.start():
                            consecutive_failures = 0
                        else:
                            logger.error("Failed to restart server")

    def _start_security_monitors(self) -> None:
        """Start all Section 8 security monitors (best-effort)."""
        # Hosts-file blocker (8.2.2)
        try:
            from .hosts_blocker import get_hosts_blocker
            blocker = get_hosts_blocker()
            blocker.sync_blocked_domains()
            blocker.start_periodic_sync(interval_seconds=300)
            logger.info("Hosts blocker started")
        except Exception as e:
            logger.debug("Hosts blocker not started: %s", e)

        # Incognito/InPrivate policy (8.5.1)
        try:
            from .incognito_policy import get_incognito_policy_manager
            results = get_incognito_policy_manager().apply_policies()
            for browser, success, msg in results:
                logger.info("Incognito policy %s: %s (%s)", browser, "applied" if success else "skipped", msg)
        except Exception as e:
            logger.debug("Incognito policy not applied: %s", e)

        # Secure storage ACLs (8.6.1)
        try:
            from .secure_storage import get_secure_data_dir, enforce_acls
            data_dir = get_secure_data_dir()
            enforce_acls(data_dir)
        except Exception as e:
            logger.debug("Secure storage ACLs not set: %s", e)

        # VPN/proxy detector (8.8.1)
        try:
            from .vpn_proxy_detector import get_vpn_proxy_detector
            get_vpn_proxy_detector().start_monitoring(interval_seconds=120)
            logger.info("VPN/proxy detector started")
        except Exception as e:
            logger.debug("VPN/proxy detector not started: %s", e)

        # Clock monitor (8.10.1)
        try:
            from .clock_monitor import get_clock_monitor
            get_clock_monitor().start()
            logger.info("Clock monitor started")
        except Exception as e:
            logger.debug("Clock monitor not started: %s", e)

        # User account monitor (8.11.1)
        try:
            from .user_account_monitor import get_user_account_monitor
            get_user_account_monitor().start()
            logger.info("User account monitor started")
        except Exception as e:
            logger.debug("User account monitor not started: %s", e)

    def _stop_security_monitors(self) -> None:
        """Stop all Section 8 security monitors (best-effort)."""
        for stop_fn_path in [
            (".hosts_blocker", "get_hosts_blocker", "stop_periodic_sync"),
            (".vpn_proxy_detector", "get_vpn_proxy_detector", "stop_monitoring"),
            (".clock_monitor", "get_clock_monitor", "stop"),
            (".user_account_monitor", "get_user_account_monitor", "stop"),
        ]:
            try:
                mod = __import__(
                    f"focus_guard.core.browser_v2.tab_server{stop_fn_path[0]}",
                    fromlist=[stop_fn_path[1]],
                )
                instance = getattr(mod, stop_fn_path[1])()
                getattr(instance, stop_fn_path[2])()
            except Exception:
                pass

    def _set_state(self, new_state: ServerState) -> None:
        """Update state and notify callback."""
        old_state = self._state
        self._state = new_state
        if old_state != new_state and self._on_state_change:
            try:
                self._on_state_change(new_state)
            except Exception as e:
                logger.warning("State change callback error: %s", e)


# Global singleton
_runner_instance: Optional[TabServerRunner] = None
_runner_lock = threading.Lock()


def get_tab_server_runner(
    host: str = DEFAULT_TAB_SERVER_HOST,
    port: int = DEFAULT_TAB_SERVER_PORT,
) -> TabServerRunner:
    """Get the global TabServerRunner singleton."""
    global _runner_instance
    if _runner_instance is None:
        with _runner_lock:
            if _runner_instance is None:
                _runner_instance = TabServerRunner(host=host, port=port)
    return _runner_instance
