"""Clock manipulation detection for budget bypass prevention.

Detects if the system clock has been set backwards to reset daily
usage budgets.  Uses monotonic time as a reference to detect jumps.

Addresses vulnerability **8.10.1** — changing system clock to reset budgets.

Detection methods:
1. Compare wall-clock delta vs monotonic-clock delta each check cycle
2. If wall clock jumped backwards by more than threshold, fire alert
3. Persist last-known wall-clock timestamp to detect cross-restart manipulation

Usage:
    from focus_guard.core.browser_v2.tab_server.clock_monitor import get_clock_monitor
    monitor = get_clock_monitor()
    monitor.start()
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# How often to check (seconds)
_CHECK_INTERVAL = 30

# Minimum backwards jump to trigger alert (seconds)
_JUMP_THRESHOLD = 60


class ClockMonitor:
    """Monitors for system clock manipulation."""

    def __init__(
        self,
        check_interval: float = _CHECK_INTERVAL,
        jump_threshold: float = _JUMP_THRESHOLD,
        state_dir: Optional[Path] = None,
    ) -> None:
        self._check_interval = check_interval
        self._jump_threshold = jump_threshold

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Reference points
        self._last_wall: float = time.time()
        self._last_mono: float = time.monotonic()

        # Alerts
        self._jump_count: int = 0
        self._total_backwards_seconds: float = 0.0
        self._started_at: Optional[float] = None

        # Persist last wall-clock to detect cross-restart manipulation
        if state_dir is None:
            import os
            pd = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
            state_dir = Path(pd) / "FocusGuard"
        self._state_file = state_dir / "clock_state.json"
        self._check_persisted_clock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._started_at = time.time()
        self._thread = threading.Thread(
            target=self._run, name="ClockMonitor", daemon=True
        )
        self._thread.start()
        logger.info("Clock monitor started (interval=%ss, threshold=%ss)",
                     self._check_interval, self._jump_threshold)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self._persist_clock()

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
                logger.exception("Error in clock monitor check")

    def _check(self) -> None:
        now_wall = time.time()
        now_mono = time.monotonic()

        wall_delta = now_wall - self._last_wall
        mono_delta = now_mono - self._last_mono

        # If wall clock moved backwards relative to monotonic clock
        drift = wall_delta - mono_delta

        if drift < -self._jump_threshold:
            backwards = abs(drift)
            self._jump_count += 1
            self._total_backwards_seconds += backwards
            logger.warning(
                "CLOCK MANIPULATION DETECTED: wall clock jumped backwards by %.0fs "
                "(jump #%d, total backwards: %.0fs)",
                backwards, self._jump_count, self._total_backwards_seconds,
            )
            self._fire_alert(backwards)

        self._last_wall = now_wall
        self._last_mono = now_mono

        # Periodically persist
        self._persist_clock()

    # ------------------------------------------------------------------
    # Cross-restart detection
    # ------------------------------------------------------------------

    def _persist_clock(self) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "last_wall_time": time.time(),
                "jump_count": self._jump_count,
                "total_backwards_seconds": self._total_backwards_seconds,
            }
            self._state_file.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def _check_persisted_clock(self) -> None:
        """Check if clock was set back between restarts."""
        try:
            if not self._state_file.exists():
                return
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            last_wall = data.get("last_wall_time", 0)
            now = time.time()
            if last_wall > 0 and now < last_wall - self._jump_threshold:
                backwards = last_wall - now
                self._jump_count += 1
                self._total_backwards_seconds += backwards
                logger.warning(
                    "CLOCK MANIPULATION (cross-restart): clock is %.0fs behind "
                    "last known time", backwards,
                )
                self._fire_alert(backwards)
        except Exception as e:
            logger.debug("Could not check persisted clock: %s", e)

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def _fire_alert(self, backwards_seconds: float) -> None:
        try:
            from .audit_logger import get_audit_logger
            get_audit_logger().log_event(
                event_type="clock_manipulation_detected",
                domain="",
                details={
                    "backwards_seconds": round(backwards_seconds, 1),
                    "jump_count": self._jump_count,
                    "total_backwards_seconds": round(self._total_backwards_seconds, 1),
                    "message": f"System clock jumped backwards by {backwards_seconds:.0f}s. "
                               f"Daily budgets may have been reset fraudulently.",
                },
            )
        except Exception:
            pass

    def get_status(self) -> dict:
        return {
            "running": self.is_running,
            "started_at": self._started_at,
            "jump_count": self._jump_count,
            "total_backwards_seconds": self._total_backwards_seconds,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[ClockMonitor] = None


def get_clock_monitor() -> ClockMonitor:
    global _instance
    if _instance is None:
        _instance = ClockMonitor()
    return _instance


def reset_clock_monitor() -> None:
    global _instance
    if _instance is not None:
        _instance.stop()
    _instance = None
