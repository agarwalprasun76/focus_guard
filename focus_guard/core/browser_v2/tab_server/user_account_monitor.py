"""New user account detection for bypass prevention.

Periodically enumerates Windows user accounts and alerts if a new
account appears that wasn't present at the last check.  A new account
could be used to bypass per-user FocusGuard settings.

Addresses vulnerability **8.11.1** — creating a new user account to bypass.

Usage:
    from focus_guard.core.browser_v2.tab_server.user_account_monitor import get_user_account_monitor
    monitor = get_user_account_monitor()
    monitor.start()
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_CHECK_INTERVAL = 300  # 5 minutes


class UserAccountMonitor:
    """Monitors for new Windows user account creation."""

    def __init__(
        self,
        check_interval: float = _CHECK_INTERVAL,
        state_dir: Optional[Path] = None,
    ) -> None:
        self._check_interval = check_interval
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._known_users: Set[str] = set()
        self._new_user_alerts: List[Dict] = []
        self._started_at: Optional[float] = None

        if state_dir is None:
            pd = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
            state_dir = Path(pd) / "FocusGuard"
        self._state_file = state_dir / "known_users.json"

        self._load_known_users()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._started_at = time.time()
        # Snapshot current users on start
        current = self._enumerate_users()
        if not self._known_users:
            self._known_users = current
            self._save_known_users()
        self._thread = threading.Thread(
            target=self._run, name="UserAccountMonitor", daemon=True
        )
        self._thread.start()
        logger.info("User account monitor started (%d known users)", len(self._known_users))

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._stop_event.wait(self._check_interval)
            if self._stop_event.is_set():
                break
            try:
                self._check()
            except Exception:
                logger.exception("Error in user account monitor")

    def _check(self) -> None:
        current = self._enumerate_users()
        new_users = current - self._known_users

        if new_users:
            for user in new_users:
                logger.warning("NEW USER ACCOUNT DETECTED: %s", user)
                alert = {
                    "username": user,
                    "detected_at": time.time(),
                }
                self._new_user_alerts.append(alert)
                self._fire_alert(user)

            # Update known users
            self._known_users = current
            self._save_known_users()

    # ------------------------------------------------------------------
    # User enumeration
    # ------------------------------------------------------------------

    @staticmethod
    def _enumerate_users() -> Set[str]:
        """Get set of local user account names."""
        users: Set[str] = set()

        if os.name != "nt":
            # Unix: read /etc/passwd
            try:
                with open("/etc/passwd", "r") as f:
                    for line in f:
                        parts = line.strip().split(":")
                        if len(parts) >= 3:
                            uid = int(parts[2])
                            if uid >= 1000 or uid == 0:
                                users.add(parts[0])
            except Exception:
                pass
            return users

        # Windows: use net user or wmic
        try:
            import subprocess
            result = subprocess.run(
                ["net", "user"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                in_users = False
                for line in result.stdout.splitlines():
                    if line.startswith("---"):
                        in_users = True
                        continue
                    if in_users:
                        if line.strip() == "" or line.startswith("The command"):
                            break
                        # net user outputs up to 3 usernames per line
                        for name in line.split():
                            name = name.strip()
                            if name:
                                users.add(name)
        except Exception as e:
            logger.debug("Could not enumerate users via net user: %s", e)

        return users

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_known_users(self) -> None:
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                self._known_users = set(data.get("users", []))
                logger.debug("Loaded %d known users", len(self._known_users))
        except Exception as e:
            logger.debug("Could not load known users: %s", e)

    def _save_known_users(self) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "users": sorted(self._known_users),
                "last_updated": time.time(),
            }
            self._state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Could not save known users: %s", e)

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def _fire_alert(self, username: str) -> None:
        try:
            from .audit_logger import get_audit_logger
            get_audit_logger().log_event(
                event_type="new_user_account_detected",
                domain="",
                details={
                    "username": username,
                    "message": f"New Windows user account '{username}' detected. "
                               f"FocusGuard may not be configured for this account.",
                },
            )
        except Exception:
            pass

        # Email alert
        try:
            from focus_guard.deployment.config import DeploymentConfig
            import smtplib
            from email.mime.text import MIMEText

            config = DeploymentConfig.load()
            if not config.email.is_configured():
                return

            subject = f"[FocusGuard ALERT] New user account: {username}"
            body = (
                f"A new Windows user account was detected on this machine.\n\n"
                f"Username: {username}\n"
                f"Machine: {config.machine_name}\n"
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"FocusGuard may not be active for this account. "
                f"Please verify the installation.\n"
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
        except Exception as e:
            logger.debug("Could not send new user alert email: %s", e)

    def get_status(self) -> dict:
        return {
            "running": self.is_running,
            "started_at": self._started_at,
            "known_users": sorted(self._known_users),
            "known_user_count": len(self._known_users),
            "new_user_alerts": self._new_user_alerts[-10:],
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[UserAccountMonitor] = None


def get_user_account_monitor() -> UserAccountMonitor:
    global _instance
    if _instance is None:
        _instance = UserAccountMonitor()
    return _instance


def reset_user_account_monitor() -> None:
    global _instance
    if _instance is not None:
        _instance.stop()
    _instance = None
