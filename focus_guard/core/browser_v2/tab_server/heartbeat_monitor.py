"""Extension heartbeat monitor for tamper detection.

Runs a background thread that periodically checks whether the browser
extension is still sending data.  When the extension goes silent for
longer than the configured threshold the monitor:

1. Logs an ``extension_disconnected`` audit event.
2. Sends an email alert (if email is configured).
3. Exposes the current status via ``get_status()``.

This addresses vulnerability **8.2.1** — a user disabling or
uninstalling the extension is detected within seconds.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# How often the monitor thread checks (seconds)
_CHECK_INTERVAL = 10

# How long without a heartbeat before we consider the extension disconnected
_DISCONNECT_THRESHOLD = 30.0

# Minimum interval between repeated alerts for the same browser (seconds)
_ALERT_COOLDOWN = 300  # 5 minutes


class HeartbeatMonitor:
    """Monitors browser extension connectivity and raises alerts on disconnect.

    The monitor reads heartbeat timestamps from ``TabStorage`` and fires
    alerts when a previously-connected browser goes silent.
    """

    def __init__(
        self,
        check_interval: float = _CHECK_INTERVAL,
        disconnect_threshold: float = _DISCONNECT_THRESHOLD,
        alert_cooldown: float = _ALERT_COOLDOWN,
    ) -> None:
        self._check_interval = check_interval
        self._disconnect_threshold = disconnect_threshold
        self._alert_cooldown = alert_cooldown

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Track per-browser state
        self._known_browsers: Dict[str, _BrowserState] = {}
        self._lock = threading.Lock()

        # Counters
        self._total_disconnect_events = 0
        self._started_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the background monitor thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._started_at = time.time()
        self._thread = threading.Thread(
            target=self._run,
            name="HeartbeatMonitor",
            daemon=True,
        )
        self._thread.start()
        logger.info("Heartbeat monitor started (interval=%ss, threshold=%ss)",
                     self._check_interval, self._disconnect_threshold)

    def stop(self) -> None:
        """Stop the monitor thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Heartbeat monitor stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def _run(self) -> None:
        """Background loop that checks heartbeats."""
        while not self._stop_event.is_set():
            try:
                self._check_heartbeats()
            except Exception:
                logger.exception("Error in heartbeat monitor check")
            self._stop_event.wait(self._check_interval)

    def _check_heartbeats(self) -> None:
        """Check all known browsers for heartbeat staleness."""
        try:
            from .storage import get_tab_storage
            storage = get_tab_storage()
        except Exception:
            return

        snapshot = storage.get_snapshot()
        now = time.time()

        with self._lock:
            for browser_status in snapshot.browsers:
                browser_key = (
                    browser_status.browser.value
                    if hasattr(browser_status.browser, "value")
                    else str(browser_status.browser)
                )

                if browser_key not in self._known_browsers:
                    self._known_browsers[browser_key] = _BrowserState(browser_key)

                state = self._known_browsers[browser_key]
                was_connected = state.connected
                is_connected = browser_status.connected
                last_hb = browser_status.last_heartbeat or 0

                state.last_heartbeat = last_hb
                state.connected = is_connected

                # Transition: connected → disconnected
                if was_connected and not is_connected:
                    silent_seconds = now - last_hb if last_hb else 0
                    if now - state.last_alert_time > self._alert_cooldown:
                        self._fire_disconnect_alert(browser_key, silent_seconds)
                        state.last_alert_time = now
                        state.disconnect_count += 1
                        self._total_disconnect_events += 1

                # Transition: disconnected → connected (recovery)
                if not was_connected and is_connected and state.disconnect_count > 0:
                    self._fire_reconnect_event(browser_key)

    # ------------------------------------------------------------------
    # Alert actions
    # ------------------------------------------------------------------
    def _fire_disconnect_alert(self, browser: str, silent_seconds: float) -> None:
        """Fire an alert when a browser extension disconnects."""
        logger.warning(
            "ALERT: Browser extension '%s' disconnected (silent for %.0fs). "
            "Extension may have been disabled or uninstalled.",
            browser,
            silent_seconds,
        )

        # Audit log
        try:
            from .audit_logger import get_audit_logger
            get_audit_logger().log_event(
                event_type="extension_disconnected",
                domain="",
                details={
                    "browser": browser,
                    "silent_seconds": round(silent_seconds, 1),
                    "message": f"Browser extension '{browser}' stopped sending heartbeats. "
                               f"It may have been disabled, uninstalled, or the browser was closed.",
                },
            )
        except Exception:
            logger.debug("Could not write audit log for disconnect alert")

        # Email alert
        self._send_email_alert(browser, silent_seconds)

    def _fire_reconnect_event(self, browser: str) -> None:
        """Log when a browser extension reconnects after a disconnect."""
        logger.info("Browser extension '%s' reconnected.", browser)
        try:
            from .audit_logger import get_audit_logger
            get_audit_logger().log_event(
                event_type="extension_reconnected",
                domain="",
                details={"browser": browser},
            )
        except Exception:
            pass

    def _send_email_alert(self, browser: str, silent_seconds: float) -> None:
        """Send an email alert about extension disconnect (best-effort)."""
        try:
            from focus_guard.deployment.config import DeploymentConfig
            config = DeploymentConfig.load()
            if not config.email.is_configured():
                return

            import smtplib
            from email.mime.text import MIMEText

            subject = f"[FocusGuard ALERT] Browser extension disconnected — {browser}"
            body = (
                f"The FocusGuard browser extension for {browser} has stopped sending "
                f"heartbeats (silent for {silent_seconds:.0f} seconds).\n\n"
                f"This may indicate the extension was disabled, uninstalled, or the "
                f"browser was closed.\n\n"
                f"Machine: {config.machine_name}\n"
                f"User: {config.user_name}\n"
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = config.email.sender_email
            msg["To"] = ", ".join(config.email.recipients)

            with smtplib.SMTP(config.email.smtp_server, config.email.smtp_port) as server:
                if config.email.use_tls:
                    server.starttls()
                server.login(config.email.smtp_username, config.email.smtp_password)
                server.send_message(msg)

            logger.info("Sent extension disconnect email alert for %s", browser)
        except Exception as e:
            logger.debug("Could not send email alert: %s", e)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def get_status(self) -> Dict:
        """Get current monitor status for diagnostics."""
        with self._lock:
            browsers = {}
            for key, state in self._known_browsers.items():
                browsers[key] = {
                    "connected": state.connected,
                    "last_heartbeat": state.last_heartbeat,
                    "disconnect_count": state.disconnect_count,
                    "last_alert_time": state.last_alert_time,
                }
            return {
                "running": self.is_running,
                "started_at": self._started_at,
                "total_disconnect_events": self._total_disconnect_events,
                "browsers": browsers,
            }


class _BrowserState:
    """Internal per-browser tracking state."""

    __slots__ = (
        "browser",
        "connected",
        "last_heartbeat",
        "disconnect_count",
        "last_alert_time",
    )

    def __init__(self, browser: str) -> None:
        self.browser = browser
        self.connected = False
        self.last_heartbeat = 0.0
        self.disconnect_count = 0
        self.last_alert_time = 0.0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[HeartbeatMonitor] = None


def get_heartbeat_monitor() -> HeartbeatMonitor:
    """Get or create the singleton HeartbeatMonitor."""
    global _instance
    if _instance is None:
        _instance = HeartbeatMonitor()
    return _instance


def reset_heartbeat_monitor() -> None:
    """Stop and reset the singleton (for testing)."""
    global _instance
    if _instance is not None:
        _instance.stop()
    _instance = None
