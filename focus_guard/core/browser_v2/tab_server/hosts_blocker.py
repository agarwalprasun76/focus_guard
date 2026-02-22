"""Hosts-file blocking for network-layer domain blocking.

Writes blocked domains to the Windows hosts file, redirecting them to
127.0.0.1.  This provides defense-in-depth that covers ALL browsers and
applications, not just those with the FocusGuard extension installed.

Addresses vulnerability **8.2.2** — using an alternative browser to
bypass the extension.

Requirements:
- Admin/elevated privileges to write to the hosts file.
- The hosts file entries are tagged with a FocusGuard marker comment
  so they can be cleanly added/removed without affecting other entries.

Usage:
    from focus_guard.core.browser_v2.tab_server.hosts_blocker import get_hosts_blocker
    blocker = get_hosts_blocker()
    blocker.sync_blocked_domains()  # Reads from DomainConfigManager
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

# Marker comments used to delimit FocusGuard entries in the hosts file
_MARKER_BEGIN = "# >>> FocusGuard Blocked Domains — DO NOT EDIT THIS SECTION <<<"
_MARKER_END = "# <<< FocusGuard Blocked Domains — END >>>"

# Default hosts file path
if os.name == "nt":
    _HOSTS_PATH = Path(r"C:\Windows\System32\drivers\etc\hosts")
else:
    _HOSTS_PATH = Path("/etc/hosts")


class HostsBlocker:
    """Manages blocked domain entries in the system hosts file.

    All FocusGuard entries are placed between marker comments so they
    can be atomically replaced without disturbing user/system entries.
    """

    def __init__(self, hosts_path: Optional[Path] = None) -> None:
        self._hosts_path = hosts_path or _HOSTS_PATH
        self._lock = threading.Lock()
        self._last_sync_time: float = 0.0
        self._last_domain_count: int = 0
        self._enabled: bool = True
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def hosts_path(self) -> Path:
        return self._hosts_path

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        if not value:
            self.remove_all_entries()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def sync_blocked_domains(self) -> bool:
        """Read blocked domains from DomainConfigManager and update hosts file.

        Returns True if the hosts file was updated.
        """
        if not self._enabled:
            return False

        try:
            domains = self._get_blocked_domains()
            return self._write_entries(domains)
        except Exception as e:
            logger.error("Failed to sync blocked domains to hosts file: %s", e)
            return False

    def _get_blocked_domains(self) -> Set[str]:
        """Collect all domains that should be blocked at the network layer."""
        domains: Set[str] = set()

        try:
            from focus_guard.core.domain.domain_config_manager import (
                get_domain_config_manager,
                CATEGORY_TO_ENUM,
            )
            mgr = get_domain_config_manager()

            blocked_cats = mgr.get_blocked_categories()
            always_allowed = mgr.get_always_allowed_domains()
            system_whitelist = mgr.get_system_whitelist()

            for cat, cat_domains in mgr.get_domain_categories().items():
                enum_cat = CATEGORY_TO_ENUM.get(cat, cat.upper())
                if enum_cat in blocked_cats:
                    for d in cat_domains:
                        d_lower = d.lower()
                        # Don't block domains that are always-allowed or system
                        if d_lower not in always_allowed and d_lower not in system_whitelist:
                            domains.add(d_lower)
                            # Also add www. variant
                            if not d_lower.startswith("www."):
                                domains.add(f"www.{d_lower}")
        except Exception as e:
            logger.warning("Could not read blocked domains from config: %s", e)

        return domains

    def _write_entries(self, domains: Set[str]) -> bool:
        """Write domain entries to the hosts file between markers.

        Returns True if the file was modified.
        """
        if not domains:
            return self.remove_all_entries()

        with self._lock:
            try:
                # Read current hosts file
                current_content = self._read_hosts_file()

                # Remove existing FocusGuard section
                clean_content = self._strip_focusguard_section(current_content)

                # Build new FocusGuard section
                sorted_domains = sorted(domains)
                lines = [
                    "",
                    _MARKER_BEGIN,
                    f"# Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"# Domains: {len(sorted_domains)}",
                ]
                for d in sorted_domains:
                    lines.append(f"127.0.0.1    {d}")
                lines.append(_MARKER_END)
                lines.append("")

                new_section = "\n".join(lines)
                new_content = clean_content.rstrip("\n") + "\n" + new_section

                # Write back
                self._write_hosts_file(new_content)
                self._last_sync_time = time.time()
                self._last_domain_count = len(sorted_domains)
                logger.info(
                    "Updated hosts file with %d blocked domains", len(sorted_domains)
                )
                return True

            except PermissionError:
                logger.warning(
                    "Cannot write to hosts file (no admin privileges): %s",
                    self._hosts_path,
                )
                return False
            except Exception as e:
                logger.error("Failed to update hosts file: %s", e)
                return False

    def remove_all_entries(self) -> bool:
        """Remove all FocusGuard entries from the hosts file."""
        with self._lock:
            try:
                current_content = self._read_hosts_file()
                clean_content = self._strip_focusguard_section(current_content)

                if clean_content != current_content:
                    self._write_hosts_file(clean_content)
                    self._last_domain_count = 0
                    logger.info("Removed all FocusGuard entries from hosts file")
                    return True
                return False
            except PermissionError:
                logger.warning("Cannot write to hosts file (no admin privileges)")
                return False
            except Exception as e:
                logger.error("Failed to clean hosts file: %s", e)
                return False

    def get_current_entries(self) -> List[str]:
        """Return list of domains currently blocked in the hosts file."""
        try:
            content = self._read_hosts_file()
            in_section = False
            domains = []
            for line in content.splitlines():
                if _MARKER_BEGIN in line:
                    in_section = True
                    continue
                if _MARKER_END in line:
                    in_section = False
                    continue
                if in_section and line.strip() and not line.strip().startswith("#"):
                    parts = line.split()
                    if len(parts) >= 2:
                        domains.append(parts[1])
            return domains
        except Exception:
            return []

    # ------------------------------------------------------------------
    # File I/O helpers
    # ------------------------------------------------------------------

    def _read_hosts_file(self) -> str:
        """Read the hosts file content."""
        if not self._hosts_path.exists():
            return ""
        return self._hosts_path.read_text(encoding="utf-8", errors="replace")

    def _write_hosts_file(self, content: str) -> None:
        """Write content to the hosts file."""
        self._hosts_path.write_text(content, encoding="utf-8")

    def _strip_focusguard_section(self, content: str) -> str:
        """Remove the FocusGuard marker section from hosts file content."""
        lines = content.splitlines()
        result = []
        in_section = False
        for line in lines:
            if _MARKER_BEGIN in line:
                in_section = True
                # Remove blank line before marker if present
                if result and result[-1].strip() == "":
                    result.pop()
                continue
            if _MARKER_END in line:
                in_section = False
                continue
            if not in_section:
                result.append(line)
        return "\n".join(result)

    # ------------------------------------------------------------------
    # Periodic sync (background thread)
    # ------------------------------------------------------------------

    def start_periodic_sync(self, interval_seconds: float = 300) -> None:
        """Start a background thread that periodically syncs blocked domains.

        This catches cases where the config changes or the hosts file
        is tampered with.
        """
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            return
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._sync_loop,
            args=(interval_seconds,),
            name="HostsBlockerSync",
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info("Hosts blocker periodic sync started (interval=%ss)", interval_seconds)

    def stop_periodic_sync(self) -> None:
        """Stop the periodic sync thread."""
        self._stop_event.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None

    def _sync_loop(self, interval: float) -> None:
        """Background loop for periodic hosts file sync."""
        # Initial sync
        self.sync_blocked_domains()
        while not self._stop_event.is_set():
            self._stop_event.wait(interval)
            if self._stop_event.is_set():
                break
            try:
                self.sync_blocked_domains()
            except Exception:
                logger.exception("Error in hosts blocker sync loop")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Get current blocker status for diagnostics."""
        return {
            "enabled": self._enabled,
            "hosts_path": str(self._hosts_path),
            "hosts_writable": os.access(self._hosts_path, os.W_OK),
            "last_sync_time": self._last_sync_time,
            "blocked_domain_count": self._last_domain_count,
            "current_entries": len(self.get_current_entries()),
            "periodic_sync_running": (
                self._monitor_thread is not None and self._monitor_thread.is_alive()
            ),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[HostsBlocker] = None


def get_hosts_blocker(hosts_path: Optional[Path] = None) -> HostsBlocker:
    """Get or create the singleton HostsBlocker."""
    global _instance
    if _instance is None:
        _instance = HostsBlocker(hosts_path=hosts_path)
    return _instance


def reset_hosts_blocker() -> None:
    """Stop and reset the singleton (for testing)."""
    global _instance
    if _instance is not None:
        _instance.stop_periodic_sync()
        _instance.remove_all_entries()
    _instance = None
