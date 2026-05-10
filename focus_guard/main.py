"""
Focus Guard — Unified Entry Point

Single entry point for the FocusGuard application. Starts all components:
  1. System tray (PyQt5) — main thread
  2. Tab server (HTTP API) — daemon thread
  3. Admin gateway (FastAPI/uvicorn) — daemon thread
  4. Activity monitor — daemon thread (via coordinator)
  5. Email reporter — scheduled via coordinator

Works both as a Python script and as a frozen PyInstaller .exe.
"""

import asyncio
import ctypes
import logging
import os
import sqlite3
import signal
import socket
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from focus_guard.core.tab_server_endpoint import DEFAULT_TAB_SERVER_HOST
from focus_guard.core.tab_server_endpoint import DEFAULT_TAB_SERVER_PORT
from focus_guard.core.tab_server_endpoint import resolve_tab_server_endpoint
from focus_guard.core.extension_constants import CHROME_STORE_URL, EDGE_STORE_URL


# ---------------------------------------------------------------------------
# Path helpers (frozen-exe aware)
# ---------------------------------------------------------------------------

def get_app_root() -> Path:
    """Return the application root directory.

    When running as a frozen PyInstaller exe, this is the directory
    containing the .exe.  Otherwise it is the repository root
    (two levels up from this file: focus_guard/main.py → repo root).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """Return the data directory (C:\\ProgramData\\FocusGuard)."""
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    path = Path(program_data) / "FocusGuard"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_dir() -> Path:
    """Return the log directory."""
    path = get_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(verbose: bool = False) -> None:
    """Configure application-wide logging with rotation."""
    log_dir = get_log_dir()
    log_file = log_dir / "focus_guard.log"

    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Rotating file handler: 10 MB max, keep 5 backups
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(fmt))

    # Console handler (visible when running from terminal / debug)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(level)
    # Clear any existing handlers (e.g. from imports that call basicConfig)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)


logger: Optional[logging.Logger] = None  # set after setup_logging()


def cleanup_old_logs(max_age_days: int = 30) -> None:
    """Delete log files older than *max_age_days* from the log directory."""
    log_dir = get_log_dir()
    cutoff = time.time() - (max_age_days * 86400)
    for f in log_dir.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            try:
                f.unlink()
                if logger:
                    logger.info("Deleted old log file: %s", f.name)
            except Exception as e:
                if logger:
                    logger.warning("Could not delete old log %s: %s", f.name, e)


# ---------------------------------------------------------------------------
# Admin check
# ---------------------------------------------------------------------------

def is_admin() -> bool:
    """Return True if the current process has administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def request_admin_elevation() -> None:
    """Re-launch the current process with admin privileges (UAC prompt)."""
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = " ".join(sys.argv[1:])
    else:
        executable = sys.executable
        params = f'"{Path(__file__)}" ' + " ".join(sys.argv[1:])

    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, params, None, 1
    )
    sys.exit(0)


# ---------------------------------------------------------------------------
# Single-instance guard
# ---------------------------------------------------------------------------

_mutex_handle = None


def ensure_single_instance() -> bool:
    """Prevent multiple instances using a Windows named mutex.

    Returns True if this is the only instance, False if another is running.
    """
    global _mutex_handle
    try:
        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(
            None, False, "Global\\FocusGuardMutex"
        )
        last_error = ctypes.windll.kernel32.GetLastError()
        if last_error == 183:  # ERROR_ALREADY_EXISTS
            return False
        return True
    except Exception:
        return True  # proceed if we can't check


# ---------------------------------------------------------------------------
# Tab server thread
# ---------------------------------------------------------------------------

def start_tab_server(
    host: str = DEFAULT_TAB_SERVER_HOST,
    port: int = DEFAULT_TAB_SERVER_PORT,
) -> object:
    """Start the browser_v2 tab server in a daemon thread.

    Returns the TabServerRunner instance.
    """
    from focus_guard.core.browser_v2.tab_server.runner import TabServerRunner

    runner = TabServerRunner(
        host=host,
        port=port,
        auto_restart=True,
        health_check_interval=10.0,
    )

    success = runner.start()
    if success:
        logger.info("Tab server started on %s:%d", host, port)
    else:
        logger.error("Tab server failed to start on %s:%d", host, port)

    return runner


def _resolve_tab_server_endpoint_from_config() -> tuple[str, int]:
    """Resolve tab server endpoint from deployment config with safe defaults."""
    return resolve_tab_server_endpoint()


def _is_local_port_available(host: str, port: int) -> bool:
    """Return True when the host/port can be bound by this process."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def _is_focusguard_tab_server_running(host: str, port: int) -> bool:
    """Best-effort check for an already-running FocusGuard tab server on host/port."""
    try:
        with urlopen(f"http://{host}:{port}/api/health", timeout=1.0) as resp:
            if resp.status != 200:
                return False
            payload = resp.read().decode("utf-8", errors="ignore")
            return "healthy" in payload.lower()
    except (URLError, TimeoutError, OSError, ValueError):
        return False


def _resolve_non_conflicting_tab_server_endpoint(host: str, port: int) -> tuple[str, int, bool]:
    """Resolve endpoint, avoiding clashes; returns (host, port, changed_from_config)."""
    if _is_local_port_available(host, port) or _is_focusguard_tab_server_running(host, port):
        return host, port, False

    for candidate_port in range(port + 1, port + 51):
        if _is_local_port_available(host, candidate_port):
            return host, candidate_port, True

    return host, port, False


def _persist_tab_server_endpoint(host: str, port: int) -> None:
    """Persist endpoint into deployment_config.json so components stay in sync."""
    try:
        from focus_guard.deployment.config import DeploymentConfig

        cfg = DeploymentConfig.load()
        if cfg.tab_server_host == host and cfg.tab_server_port == port:
            return
        cfg.tab_server_host = host
        cfg.tab_server_port = port
        if cfg.save():
            logger.info("Persisted tab-server endpoint to deployment config: %s:%d", host, port)
        else:
            logger.warning("Failed to persist tab-server endpoint to deployment config")
    except Exception as exc:
        logger.warning("Could not persist tab-server endpoint to deployment config: %s", exc)


# ---------------------------------------------------------------------------
# Coordinator thread (activity monitor, classification, etc.)
# ---------------------------------------------------------------------------

_coordinator = None
_coordinator_loop = None


def _run_coordinator() -> None:
    """Run the FocusGuardCoordinator in its own asyncio event loop (daemon thread)."""
    global _coordinator, _coordinator_loop

    try:
        from focus_guard.core.config.manager import DefaultConfigurationManager
        from focus_guard.core.coordinator.focus_guard_coordinator import FocusGuardCoordinator

        _coordinator_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_coordinator_loop)

        config_manager = DefaultConfigurationManager()
        _coordinator = FocusGuardCoordinator(config_manager)

        async def _run():
            if not await _coordinator.initialize():
                logger.error("Coordinator failed to initialize")
                return
            if not await _coordinator.start():
                logger.error("Coordinator failed to start")
                await _coordinator.shutdown()
                return
            logger.info("Coordinator is running")

            # Keep alive until the loop is stopped
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                await _coordinator.shutdown()
                logger.info("Coordinator shut down")

        _coordinator_loop.run_until_complete(_run())
    except Exception:
        logger.exception("Coordinator thread crashed")


def start_coordinator() -> threading.Thread:
    """Start the coordinator in a daemon thread."""
    t = threading.Thread(target=_run_coordinator, name="CoordinatorThread", daemon=True)
    t.start()
    logger.info("Coordinator thread started")
    return t


def stop_coordinator() -> None:
    """Gracefully stop the coordinator."""
    global _coordinator, _coordinator_loop
    if _coordinator_loop and _coordinator_loop.is_running():
        # Cancel all tasks in the coordinator loop
        for task in asyncio.all_tasks(_coordinator_loop):
            _coordinator_loop.call_soon_threadsafe(task.cancel)
        # Give it a moment to shut down
        time.sleep(2)
    _coordinator = None
    _coordinator_loop = None


# ---------------------------------------------------------------------------
# Email report scheduler (daemon thread)
# ---------------------------------------------------------------------------

_email_scheduler_running = False


def _has_usage_sessions_table(db_path: Path) -> bool:
    """Return True when *db_path* contains a usage_sessions table."""
    if not db_path.exists() or not db_path.is_file():
        return False
    try:
        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='usage_sessions' LIMIT 1"
            ).fetchone()
        return bool(row)
    except Exception:
        return False


def _get_usage_db_activity_score(db_path: Path) -> Optional[tuple[int, int, int]]:
    """Return an activity score tuple for selecting the best usage DB.

    Score tuple is:
      (has_recent_activity, recent_signal_count, total_signal_count)

    Signals are sourced from usage_sessions plus visible_windows (when present).
    """
    if not _has_usage_sessions_table(db_path):
        return None

    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # usage_sessions is the primary source used by hourly reports.
            total_sessions = int(cursor.execute("SELECT COUNT(*) FROM usage_sessions").fetchone()[0] or 0)
            try:
                recent_sessions = int(
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM usage_sessions
                        WHERE datetime(COALESCE(end_time, start_time)) >= datetime('now', '-6 hours')
                        """
                    ).fetchone()[0]
                    or 0
                )
            except sqlite3.OperationalError:
                # Minimal/legacy schemas used in some tests may omit start/end columns.
                recent_sessions = 0

            total_visible = 0
            recent_visible = 0
            has_visible_windows = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='visible_windows' LIMIT 1"
            ).fetchone()
            if has_visible_windows:
                total_visible = int(cursor.execute("SELECT COUNT(*) FROM visible_windows").fetchone()[0] or 0)
                try:
                    recent_visible = int(
                        cursor.execute(
                            """
                            SELECT COUNT(*)
                            FROM visible_windows
                            WHERE datetime(timestamp) >= datetime('now', '-6 hours')
                            """
                        ).fetchone()[0]
                        or 0
                    )
                except sqlite3.OperationalError:
                    recent_visible = 0

            recent_signal_count = recent_sessions + recent_visible
            total_signal_count = total_sessions + total_visible
            has_recent_activity = 1 if recent_signal_count > 0 else 0
            return (has_recent_activity, recent_signal_count, total_signal_count)
    except Exception:
        return None


def _resolve_usage_db_path(config) -> Optional[Path]:
    """Resolve the best usage.db path for report generation.

    We prefer configured storage, but fall back to LOCALAPPDATA where
    non-service activity logger runs commonly write usage telemetry.
    """
    candidates: list[Path] = []

    try:
        candidates.append(config.storage.get_data_directory() / "usage.db")
    except Exception:
        pass

    local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
    if local_appdata:
        candidates.append(Path(local_appdata) / "FocusGuard" / "usage.db")

    seen: set[str] = set()
    best_path: Optional[Path] = None
    best_score: Optional[tuple[int, int, int]] = None
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)

        score = _get_usage_db_activity_score(candidate)
        if score is None:
            continue

        if best_score is None or score > best_score:
            best_score = score
            best_path = candidate

    return best_path


def _email_scheduler_loop() -> None:
    """Background loop that sends scheduled hourly/daily email reports.

    Mirrors the scheduling logic from ``ActivityMonitorService._scheduler_loop``
    but runs inside the tray-app process so reports are sent even when
    FocusGuard is not installed as a Windows service.
    """
    global _email_scheduler_running

    try:
        from datetime import datetime, timedelta
        from focus_guard.deployment.config import DeploymentConfig
        from focus_guard.deployment.email_reporter import EmailReporter

        config = DeploymentConfig.load()
        if not config.email.enabled or not config.email.is_configured():
            logger.info("Email not configured — report scheduler disabled")
            return

        reporter = EmailReporter(config)
        schedule = config.reporting.schedule
        active_db_path: Optional[Path] = None
        try:
            interval_minutes = max(1, int(schedule.get_hourly_interval_minutes()))
        except Exception:
            interval_minutes = max(1, int(getattr(schedule, "hourly_interval_hours", 1) or 1) * 60)

        last_hourly: Optional[datetime] = None
        last_daily: Optional[datetime] = None

        _email_scheduler_running = True
        logger.info(
            "Email report scheduler started (hourly=%s, every=%d min, daily=%s)",
            schedule.hourly_enabled,
            interval_minutes,
            schedule.daily_enabled,
        )

        while _email_scheduler_running:
            try:
                now = datetime.now()

                db_path = _resolve_usage_db_path(config)
                if db_path != active_db_path:
                    active_db_path = db_path
                    if active_db_path:
                        logger.info("Email scheduler using usage DB: %s", active_db_path)
                    else:
                        logger.warning(
                            "Email scheduler could not find a valid usage DB (usage_sessions table missing)"
                        )

                # --- Hourly report ---
                if schedule.hourly_enabled and db_path:
                    try:
                        interval_minutes = max(1, int(schedule.get_hourly_interval_minutes()))
                    except Exception:
                        interval_minutes = max(1, int(getattr(schedule, "hourly_interval_hours", 1) or 1) * 60)

                    minutes_ok = (
                        last_hourly is None
                        or (now - last_hourly).total_seconds() / 60 >= interval_minutes
                    )
                    if minutes_ok:
                        try:
                            reporter.send_hourly_report(db_path)
                            last_hourly = now
                        except Exception as exc:
                            logger.error("Hourly report failed: %s", exc)

                # --- Daily report ---
                if schedule.daily_enabled and db_path:
                    if now.hour == schedule.daily_hour:
                        target_min = schedule.daily_minute
                        grace = schedule.grace_period_minutes
                        in_window = target_min <= now.minute < target_min + grace
                        days_ok = (
                            last_daily is None
                            or (now - last_daily).total_seconds() / 3600 >= 23
                        )
                        if in_window and days_ok:
                            try:
                                yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
                                reporter.send_daily_report(db_path, yesterday)
                                last_daily = now
                            except Exception as exc:
                                logger.error("Daily report failed: %s", exc)

                time.sleep(60)
            except Exception as exc:
                logger.error("Email scheduler tick error: %s", exc)
                time.sleep(60)
    except Exception:
        logger.exception("Email scheduler thread crashed")


def start_email_scheduler() -> threading.Thread:
    """Start the email report scheduler in a daemon thread."""
    t = threading.Thread(target=_email_scheduler_loop, name="EmailSchedulerThread", daemon=True)
    t.start()
    logger.info("Email scheduler thread started")
    return t


def stop_email_scheduler() -> None:
    """Signal the email scheduler to stop."""
    global _email_scheduler_running
    _email_scheduler_running = False


# ---------------------------------------------------------------------------
# Activity logger (EnhancedActivityLogger — writes usage.db)
# ---------------------------------------------------------------------------

_activity_logger_instance = None


def start_activity_logger() -> None:
    """Start the EnhancedActivityLogger so app usage is written to usage.db.

    This is the same logger that ``ActivityMonitorService`` starts when running
    as a Windows service.  In the tray-app flow (``main()``) the coordinator
    only polls window info for event-bus events but does **not** persist
    per-tick samples.  Starting the enhanced logger here closes that gap so
    both the admin portal App Activity view and email reports have data.
    """
    global _activity_logger_instance

    try:
        from focus_guard.core.activity.enhanced_logger import EnhancedActivityLogger
        from focus_guard.core.activity.idle_detector import IdleConfiguration

        # Use deployment config for sampling interval; let EnhancedActivityLogger
        # pick its default log_dir (LOCALAPPDATA/FocusGuard on Windows) so the DB
        # stays in the same location the tab server and email reporter look for it.
        sampling_interval = 5
        try:
            from focus_guard.deployment.config import DeploymentConfig
            cfg = DeploymentConfig.load()
            sampling_interval = cfg.monitoring.sampling_interval
        except Exception:
            pass

        _activity_logger_instance = EnhancedActivityLogger(
            interval_seconds=sampling_interval,
        )
        _activity_logger_instance.start()
        logger.info(
            "Activity logger started (interval=%ds, db=%s)",
            sampling_interval,
            _activity_logger_instance.database.db_path,
        )
    except Exception:
        logger.exception("Failed to start activity logger")


def stop_activity_logger() -> None:
    """Stop the EnhancedActivityLogger."""
    global _activity_logger_instance
    if _activity_logger_instance is not None:
        try:
            _activity_logger_instance.stop()
        except Exception:
            logger.exception("Error stopping activity logger")
        _activity_logger_instance = None


# ---------------------------------------------------------------------------
# Admin gateway (in-process uvicorn, daemon thread)
# ---------------------------------------------------------------------------

_admin_gw_server = None  # uvicorn.Server instance

_ADMIN_GATEWAY_PORT = 58393


def _start_admin_gateway(tab_server_host: str, tab_server_port: int) -> Optional[callable]:
    """Start the admin gateway (FastAPI) via uvicorn in a daemon thread.

    Returns a shutdown callable, or None if startup failed.
    """
    global _admin_gw_server

    try:
        import uvicorn
        from focus_guard.core.admin_gateway.app import create_app
    except Exception:
        logger.warning("uvicorn or admin_gateway not available — admin UI disabled")
        return None

    # In a frozen PyInstaller exe with console=False, sys.stdout/stderr are
    # None.  Uvicorn's logging formatter calls sys.stderr.isatty() which
    # crashes with AttributeError.  Patch them to devnull before configuring.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    # Tell the admin gateway where the tab server lives
    os.environ["FOCUS_GUARD_TAB_SERVER_BASE_URL"] = (
        f"http://{tab_server_host}:{tab_server_port}"
    )

    port = _ADMIN_GATEWAY_PORT

    # Check if port is already in use (another admin gateway running)
    if not _is_local_port_available("127.0.0.1", port):
        logger.info("Admin gateway port %d already in use — assuming external instance", port)
        return None

    app = create_app()

    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        log_config=None,  # Disable uvicorn's own logging config to avoid isatty issues
    )
    _admin_gw_server = uvicorn.Server(config)

    def _run():
        try:
            _admin_gw_server.run()
        except Exception:
            logger.exception("Admin gateway thread crashed")

    t = threading.Thread(target=_run, name="AdminGatewayThread", daemon=True)
    t.start()
    logger.info("Admin gateway starting on 127.0.0.1:%d", port)

    # Wait briefly for it to become ready
    for _ in range(30):
        time.sleep(0.5)
        try:
            resp = urlopen(f"http://127.0.0.1:{port}/admin/health", timeout=1)
            if resp.status == 200:
                logger.info("Admin gateway ready on 127.0.0.1:%d", port)
                break
        except Exception:
            pass
    else:
        logger.warning("Admin gateway did not become healthy within 15 s")

    def _shutdown():
        global _admin_gw_server
        if _admin_gw_server is not None:
            logger.info("Shutting down admin gateway…")
            _admin_gw_server.should_exit = True
            _admin_gw_server = None

    return _shutdown


# ---------------------------------------------------------------------------
# System tray (runs on main thread)
# ---------------------------------------------------------------------------

def run_tray(
    tab_server_runner,
    coordinator_thread,
    qt_app=None,
    *,
    show_post_first_run_checklist: bool = False,
) -> None:
    """Launch the PyQt5 system tray application on the main thread.

    If *qt_app* is provided (created earlier for the wizard), reuse it.
    Otherwise create a new QApplication.
    """
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox
    from PyQt5.QtGui import QIcon, QPixmap
    from PyQt5.QtCore import QTimer

    app = qt_app or QApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        logger.error("System tray is not available")
        QMessageBox.critical(None, "Focus Guard", "System tray is not available.")
        sys.exit(1)

    app.setQuitOnLastWindowClosed(False)

    # --- Icon ---
    icon = _load_icon()
    tray = QSystemTrayIcon(icon, parent=None)
    tray.setToolTip("Focus Guard — AI-powered productivity management")

    # --- Context menu ---
    menu = QMenu()

    status_action = QAction("Status: Starting…")
    status_action.setEnabled(False)
    menu.addAction(status_action)
    menu.addSeparator()

    # Settings
    settings_action = QAction("Settings…")
    settings_action.triggered.connect(lambda: _open_settings_dialog(tray))
    menu.addAction(settings_action)

    # Extension links sub-menu
    ext_menu = menu.addMenu("Install Extension")
    edge_action = QAction("Microsoft Edge (Store)")
    edge_action.triggered.connect(
        lambda: _open_url(EDGE_STORE_URL)
    )
    ext_menu.addAction(edge_action)

    chrome_action = QAction("Google Chrome (Store)")
    chrome_action.triggered.connect(
        lambda: _open_url(CHROME_STORE_URL)
    )
    ext_menu.addAction(chrome_action)
    menu.addSeparator()

    # View logs
    logs_action = QAction("View Logs")
    logs_action.triggered.connect(lambda: _open_path(get_log_dir()))
    menu.addAction(logs_action)

    # View data directory
    data_action = QAction("Open Data Folder")
    data_action.triggered.connect(lambda: _open_path(get_data_dir()))
    menu.addAction(data_action)
    menu.addSeparator()

    # About
    about_action = QAction("About Focus Guard")
    about_action.triggered.connect(lambda: _show_about(tray))
    menu.addAction(about_action)
    menu.addSeparator()

    # Exit
    exit_action = QAction("Exit Focus Guard")
    exit_action.triggered.connect(lambda: _shutdown_and_exit(app, tab_server_runner))
    menu.addAction(exit_action)

    tray.setContextMenu(menu)
    tray.show()

    # Show startup notification
    if tray.supportsMessages():
        tray.showMessage(
            "Focus Guard",
            "Focus Guard is running. Right-click the tray icon for options.",
            QSystemTrayIcon.Information,
            3000,
        )

    if show_post_first_run_checklist:

        def _show_first_run_followup():
            try:
                from focus_guard.gui.first_run_post_setup_dialog import (
                    PostFirstRunSetupDialog,
                )

                dlg = PostFirstRunSetupDialog(parent=None, tray_icon=tray)
                dlg.exec_()
            except Exception:
                logger.exception("Post-first-run setup dialog failed")

        QTimer.singleShot(2100, _show_first_run_followup)

    # --- Periodic status update ---
    def _update_status():
        if tab_server_runner and tab_server_runner.is_running:
            try:
                port = tab_server_runner.get_status().port
            except Exception:
                port = "unknown"
            status_action.setText(f"Status: Running (port {port})")
        else:
            status_action.setText("Status: Tab server not running")

    timer = QTimer()
    timer.timeout.connect(_update_status)
    timer.start(5000)
    _update_status()

    # --- Run Qt event loop ---
    sys.exit(app.exec_())


def _get_meipass() -> Optional[Path]:
    """Return the PyInstaller _MEIPASS directory if running frozen, else None."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return None


def _load_icon():
    """Load the application icon, falling back to a generated one."""
    from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QFont

    # Try loading from bundled data (PyInstaller) or source tree
    candidates = []

    # 0. Explicit user-selected tray icon
    if meipass := _get_meipass():
        candidates.append(meipass / "webextension_mv3" / "icons" / "ChatGPT_FocusGuard_v3.png")
        candidates.append(
            meipass
            / "focus_guard"
            / "core"
            / "browser"
            / "extension"
            / "webextension_mv3"
            / "icons"
            / "ChatGPT_FocusGuard_v3.png"
        )

    candidates.append(
        Path(__file__).parent
        / "core"
        / "browser"
        / "extension"
        / "webextension_mv3"
        / "icons"
        / "ChatGPT_FocusGuard_v3.png"
    )

    # 1. Tray-optimized extension icons (typically tighter than .ico artwork)
    if meipass := _get_meipass():
        candidates.append(meipass / "webextension_mv3" / "icons" / "icon16.png")
        candidates.append(meipass / "webextension_mv3" / "icons" / "icon32.png")
        candidates.append(meipass / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3" / "icons" / "icon16.png")
        candidates.append(meipass / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3" / "icons" / "icon32.png")

    candidates.append(
        Path(__file__).parent / "core" / "browser" / "extension" / "webextension_mv3" / "icons" / "icon16.png"
    )
    candidates.append(
        Path(__file__).parent / "core" / "browser" / "extension" / "webextension_mv3" / "icons" / "icon32.png"
    )

    # 2. PyInstaller _MEIPASS — most reliable for frozen onefile builds
    meipass = _get_meipass()
    if meipass:
        candidates.append(meipass / "focus_guard" / "assets" / "icon.ico")
        candidates.append(meipass / "focus_guard" / "assets" / "icon.png")

    # 3. Relative to exe directory (frozen onedir or manual placement)
    candidates.append(get_app_root() / "focus_guard" / "assets" / "icon.ico")
    candidates.append(get_app_root() / "assets" / "icon.ico")

    # 4. Relative to this source file (development mode)
    candidates.append(Path(__file__).parent / "assets" / "icon.ico")

    # 5. Fall back to the extension PNG icons
    candidates.append(
        Path(__file__).parent / "core" / "browser" / "extension"
        / "webextension_mv3" / "icons" / "icon128.png"
    )
    if meipass:
        candidates.append(meipass / "webextension_mv3" / "icons" / "icon128.png")

    for p in candidates:
        if logger:
            logger.debug("Trying icon path: %s (exists=%s)", p, p.exists())
        if p.exists():
            icon = QIcon(str(p))
            if not icon.isNull():
                if logger:
                    logger.info("Loaded tray icon from: %s", p)
                return icon
            elif logger:
                logger.warning("Icon file exists but QIcon is null: %s", p)

    # Generate a visible fallback icon with "FG" text
    if logger:
        logger.warning(
            "No icon file found in any candidate path. "
            "Generating fallback icon. Searched: %s",
            [str(p) for p in candidates],
        )
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(46, 125, 50))  # green background
    painter = QPainter(pixmap)
    painter.setPen(QColor(255, 255, 255))  # white text
    font = QFont("Arial", 22, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x0084, "FG")  # AlignCenter = 0x0084
    painter.end()
    return QIcon(pixmap)


def _open_url(url: str) -> None:
    os.startfile(url)


def _open_path(path: Path) -> None:
    os.startfile(str(path))


def _open_settings_dialog(tray) -> None:
    """Open the settings dialog (re-runs the wizard with current values pre-filled)."""
    from PyQt5.QtWidgets import QMessageBox
    try:
        from focus_guard.gui.first_run_wizard import FirstRunWizard
        icon = tray.icon() if tray else _load_icon()
        wizard = FirstRunWizard(icon=icon, settings_mode=True)
        wizard.setWindowTitle("Focus Guard Settings")

        if wizard.exec_():
            config = wizard.get_config()
            config.save()
            logger.info("Settings saved")
            QMessageBox.information(None, "Focus Guard", "Settings saved successfully.")
    except Exception as e:
        logger.error("Error opening settings: %s", e)
        QMessageBox.warning(None, "Focus Guard", f"Could not open settings:\n{e}")


def _show_about(tray) -> None:
    """Show the About dialog."""
    from PyQt5.QtWidgets import QMessageBox
    _, tab_server_port = _resolve_tab_server_endpoint_from_config()
    QMessageBox.about(
        None,
        "About Focus Guard",
        "<h3>Focus Guard</h3>"
        "<p>AI-powered productivity and screen-time management.</p>"
        "<p><b>Version:</b> 1.0.0 (MVP)</p>"
        "<p><b>Components:</b></p>"
        "<ul>"
        "<li>Activity monitor &amp; classifier</li>"
        "<li>Browser extension (Edge / Chrome)</li>"
        f"<li>Tab server on port {tab_server_port}</li>"
        "<li>Email activity reports</li>"
        "</ul>"
        "<p>&copy; 2026 Prasun &amp; Siyona Agarwal</p>",
    )


def _shutdown_and_exit(app, tab_server_runner) -> None:
    """Gracefully shut down all components and exit."""
    logger.info("User requested exit")
    if tab_server_runner:
        tab_server_runner.stop()
    stop_coordinator()
    app.quit()


# ---------------------------------------------------------------------------
# Autostart registry helper
# ---------------------------------------------------------------------------

def setup_autostart(enable: bool = True) -> None:
    """Add or remove the autostart registry entry."""
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
        )
        if enable:
            if getattr(sys, "frozen", False):
                app_path = f'"{sys.executable}"'
            else:
                app_path = f'"{sys.executable}" "{Path(__file__)}"'
            winreg.SetValueEx(key, "FocusGuard", 0, winreg.REG_SZ, app_path)
        else:
            try:
                winreg.DeleteValue(key, "FocusGuard")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        if logger:
            logger.warning("Could not update autostart registry: %s", e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # 1. Logging first
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    setup_logging(verbose=verbose)

    global logger
    logger = logging.getLogger("focus_guard.main")
    logger.info("=" * 60)
    logger.info("Focus Guard starting (frozen=%s)", getattr(sys, "frozen", False))
    logger.info("App root: %s", get_app_root())
    logger.info("Data dir: %s", get_data_dir())
    logger.info("Log dir:  %s", get_log_dir())
    logger.info("=" * 60)

    # 2. Single-instance check
    if not ensure_single_instance():
        logger.warning("Another instance of Focus Guard is already running. Exiting.")
        # Try to show a message box if possible
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            _app = QApplication(sys.argv)
            QMessageBox.warning(
                None,
                "Focus Guard",
                "Focus Guard is already running.\nCheck the system tray.",
            )
        except Exception:
            pass
        sys.exit(0)

    # 3. Admin check (warn but don't block — some features work without admin)
    if not is_admin():
        logger.warning(
            "Running without administrator privileges. "
            "Some features (protected config, autostart) may not work."
        )

    # 4. Ensure data directories exist
    get_data_dir()
    get_log_dir()

    # 5. First-run wizard (before loading config — wizard creates it)
    from PyQt5.QtWidgets import QApplication
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    from focus_guard.gui.first_run_wizard import is_first_run, run_first_run_wizard

    wizard_config = None
    tab_server_runner = None  # populated in step 8 below
    admin_gw_shutdown = None
    show_post_first_run_checklist = False

    if is_first_run():
        logger.info("First run detected — launching setup wizard")
        wizard_config = run_first_run_wizard(icon=_load_icon())
        show_post_first_run_checklist = wizard_config is not None
        if wizard_config and wizard_config.run_at_startup:
            try:
                setup_autostart(enable=True)
            except Exception as e:
                logger.warning("Could not set up autostart: %s", e)

    # 6. Load deployment config (wizard may have just created it)
    try:
        from focus_guard.deployment.config import DeploymentConfig
        config = DeploymentConfig.load()
        logger.info("Deployment config loaded (machine=%s)", config.machine_name)
    except Exception as e:
        logger.warning("Could not load deployment config: %s — using defaults", e)

    # 7. Set up autostart (if not first run, still ensure it's set)
    if not is_first_run():
        try:
            setup_autostart(enable=True)
        except Exception as e:
            logger.warning("Could not set up autostart: %s", e)

    # 7b. Clean up old logs
    try:
        cleanup_old_logs(max_age_days=30)
    except Exception as e:
        logger.warning("Log cleanup failed: %s", e)

    # 8. Start tab server (daemon thread)
    tab_server_host, tab_server_port = _resolve_tab_server_endpoint_from_config()
    tab_server_host, tab_server_port, endpoint_changed = _resolve_non_conflicting_tab_server_endpoint(
        tab_server_host,
        tab_server_port,
    )
    if endpoint_changed:
        logger.warning(
            "Configured tab-server port was busy; falling back to %s:%d",
            tab_server_host,
            tab_server_port,
        )
        _persist_tab_server_endpoint(tab_server_host, tab_server_port)

    tab_server_runner = start_tab_server(host=tab_server_host, port=tab_server_port)

    # 9. Start admin gateway (FastAPI/uvicorn) in daemon thread
    admin_gw_shutdown = _start_admin_gateway(tab_server_host, tab_server_port)

    # 10. Start coordinator (activity monitor, classification, etc.) in daemon thread
    coordinator_thread = start_coordinator()

    # 10a. Start activity logger (writes usage.db for admin portal + email reports)
    start_activity_logger()

    # 10b. Start email report scheduler (hourly/daily reports) in daemon thread
    email_thread = start_email_scheduler()

    # 11. Run system tray on main thread (blocks until exit)
    try:
        run_tray(
            tab_server_runner,
            coordinator_thread,
            qt_app=qt_app,
            show_post_first_run_checklist=show_post_first_run_checklist,
        )
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        logger.info("Shutting down…")
        stop_email_scheduler()
        stop_activity_logger()
        if admin_gw_shutdown:
            admin_gw_shutdown()
        if tab_server_runner:
            tab_server_runner.stop()
        stop_coordinator()
        logger.info("Focus Guard stopped")


if __name__ == "__main__":
    main()
