"""
Windows Service wrapper for Focus Guard Activity Monitor.

This module provides functionality to run the activity monitor as a Windows service
that starts automatically and runs in the background.
"""

import os
import sys
import time
import logging
import threading
import ctypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Windows-specific imports
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    import win32api
    import win32con
    import win32ts
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

from focus_guard.deployment.config import DeploymentConfig
from focus_guard.deployment.email_reporter import EmailReporter
from focus_guard.deployment.runtime_startup import RuntimeHandles
from focus_guard.deployment.runtime_startup import RuntimeStartupError
from focus_guard.deployment.runtime_startup import RuntimeStartupOrchestrator

logger = logging.getLogger(__name__)


def is_user_logged_in() -> bool:
    """Check if a user is currently logged in to the console."""
    try:
        if HAS_WIN32:
            # Get active console session
            session_id = win32ts.WTSGetActiveConsoleSessionId()
            if session_id == 0xFFFFFFFF:
                return False
            return True
        return True  # Assume logged in if we can't check
    except Exception:
        return True


def is_workstation_locked() -> bool:
    """Check if the workstation is locked."""
    try:
        # This is a heuristic - check if the foreground window is the lock screen
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        
        if hwnd == 0:
            return True
        
        # Get window class name
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        
        # Lock screen class names
        lock_classes = ['Windows.UI.Core.CoreWindow', 'LockScreenBackstopFrame']
        return class_name.value in lock_classes
    except Exception:
        return False


class ActivityMonitorService:
    """
    Activity monitor that can run as a Windows service or standalone process.
    
    Features:
    - Background activity monitoring
    - Scheduled email reports (hourly/daily)
    - Pause when user not logged in or workstation locked
    - Protected log storage
    """
    
    def __init__(self, config: Optional[DeploymentConfig] = None):
        """
        Initialize the activity monitor service.
        
        Args:
            config: Deployment configuration, or None to load from default location
        """
        self.config = config or DeploymentConfig.load()
        self.running = False
        self.paused = False
        
        # Initialize components
        self.email_reporter = EmailReporter(self.config)
        self.logger_instance = None
        
        # Scheduling
        self.last_hourly_report: Optional[datetime] = None
        self.last_daily_report: Optional[datetime] = None
        self.last_cleanup: Optional[datetime] = None
        
        # Threading
        self.monitor_thread: Optional[threading.Thread] = None
        self.scheduler_thread: Optional[threading.Thread] = None

        # Runtime dependency orchestration (tab server/admin gateway)
        self.runtime_handles: Optional[RuntimeHandles] = None
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for the service."""
        log_dir = self.config.storage.get_data_directory() / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"service_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def _get_database_path(self) -> Path:
        """Get the path to the usage database."""
        return self.config.storage.get_data_directory() / 'usage.db'
    
    def start(self):
        """Start the activity monitor service."""
        if self.running:
            logger.warning("Service is already running")
            return
        
        logger.info(f"Starting FocusGuard Activity Monitor on {self.config.machine_name}")

        orchestrator = self._build_runtime_orchestrator()
        try:
            self.runtime_handles = orchestrator.start()
            logger.info(
                "Runtime dependencies ready (tab=%s:%d, admin=%s:%d)",
                self.runtime_handles.tab_server_host,
                self.runtime_handles.tab_server_port,
                self.runtime_handles.admin_gateway_host,
                self.runtime_handles.admin_gateway_port,
            )
        except RuntimeStartupError as exc:
            diagnostics = {}
            try:
                diagnostics = orchestrator.collect_diagnostics()
            except Exception as diag_exc:  # noqa: BLE001
                logger.warning("Could not collect runtime diagnostics after startup failure: %s", diag_exc)

            strict_mode = os.getenv("FOCUS_GUARD_STRICT_RUNTIME_STARTUP", "0").strip().lower() in {
                "1",
                "true",
                "yes",
            }
            if strict_mode:
                logger.error("Runtime startup failed in strict mode: %s", exc)
                if diagnostics:
                    logger.error("Runtime diagnostics snapshot: %s", diagnostics)
                raise
            logger.warning(
                "Runtime startup degraded: %s. Continuing activity monitor start in non-strict mode.",
                exc,
            )
            if diagnostics:
                logger.warning("Runtime diagnostics snapshot: %s", diagnostics)
            self.runtime_handles = None

        self.running = True
        
        # Start the activity logger
        self._start_activity_logger()
        
        # Start the scheduler thread for reports
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Service started successfully")
    
    def stop(self):
        """Stop the activity monitor service."""
        if not self.running:
            return
        
        logger.info("Stopping FocusGuard Activity Monitor")
        self.running = False
        
        # Stop the activity logger
        if self.logger_instance:
            self.logger_instance.stop()

        # Stop managed runtime dependencies (best-effort)
        if self.runtime_handles is not None:
            try:
                self._build_runtime_orchestrator().stop(self.runtime_handles)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error stopping managed runtime dependencies: %s", exc)
            finally:
                self.runtime_handles = None
        
        # Wait for threads to finish
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5.0)
        
        logger.info("Service stopped")

    def _build_runtime_orchestrator(self) -> RuntimeStartupOrchestrator:
        """Build runtime orchestrator from deployment config + environment overrides."""
        admin_host = os.getenv("FOCUS_GUARD_ADMIN_GATEWAY_HOST", "127.0.0.1").strip() or "127.0.0.1"

        admin_port_raw = os.getenv("FOCUS_GUARD_ADMIN_GATEWAY_PORT", "58393").strip()
        try:
            admin_port = int(admin_port_raw)
        except ValueError:
            admin_port = 58393

        start_admin_gateway = os.getenv("FOCUS_GUARD_START_ADMIN_GATEWAY", "1").strip().lower() in {
            "1",
            "true",
            "yes",
        }

        return RuntimeStartupOrchestrator(
            tab_server_host=self.config.tab_server_host,
            tab_server_port=self.config.tab_server_port,
            admin_gateway_host=admin_host,
            admin_gateway_port=admin_port,
            start_admin_gateway=start_admin_gateway,
            logger=logger,
        )
    
    def _start_activity_logger(self):
        """Initialize and start the activity logger."""
        try:
            # Import here to avoid circular imports
            from focus_guard.core.activity.enhanced_logger import EnhancedActivityLogger
            from focus_guard.core.activity.idle_detector import IdleConfiguration
            
            # Configure idle detection
            idle_config = IdleConfiguration(
                short_idle_threshold=float(self.config.monitoring.idle_threshold_short),
                medium_idle_threshold=float(self.config.monitoring.idle_threshold_medium),
                long_idle_threshold=float(self.config.monitoring.idle_threshold_long)
            )
            
            # Create logger with protected data directory
            data_dir = self.config.storage.get_data_directory()
            
            self.logger_instance = EnhancedActivityLogger(
                interval_seconds=self.config.monitoring.sampling_interval,
                log_dir=str(data_dir),
                idle_config=idle_config
            )
            
            self.logger_instance.start()
            logger.info(f"Activity logger started with {self.config.monitoring.sampling_interval}s interval")
            
        except Exception as e:
            logger.error(f"Failed to start activity logger: {e}")
    
    def _scheduler_loop(self):
        """Background loop for scheduling reports and maintenance tasks."""
        # Handle send_on_start option - send initial reports immediately
        schedule = self.config.reporting.schedule
        if schedule.send_on_start:
            logger.info("send_on_start enabled - sending initial reports")
            db_path = self._get_database_path()
            if db_path.exists():
                if schedule.hourly_enabled:
                    try:
                        self.email_reporter.send_hourly_report(db_path)
                        self.last_hourly_report = datetime.now()
                        logger.info("Initial hourly report sent")
                    except Exception as e:
                        logger.error(f"Failed to send initial hourly report: {e}")
                
                if schedule.daily_enabled:
                    try:
                        today = datetime.now().strftime('%Y-%m-%d')
                        self.email_reporter.send_daily_report(db_path, today)
                        self.last_daily_report = datetime.now()
                        logger.info("Initial daily report sent")
                    except Exception as e:
                        logger.error(f"Failed to send initial daily report: {e}")
        
        while self.running:
            try:
                now = datetime.now()
                
                # Check if we should pause
                if self.config.monitoring.pause_when_locked:
                    if is_workstation_locked() or not is_user_logged_in():
                        if not self.paused:
                            logger.info("Pausing monitoring - user not active")
                            self.paused = True
                            if self.logger_instance:
                                self.logger_instance.stop()
                    else:
                        if self.paused:
                            logger.info("Resuming monitoring - user active")
                            self.paused = False
                            self._start_activity_logger()
                
                # Check for hourly report
                if self.config.reporting.hourly_report:
                    if self._should_send_hourly_report(now):
                        db_path = self._get_database_path()
                        if db_path.exists():
                            self.email_reporter.send_hourly_report(db_path)
                            self.last_hourly_report = now
                
                # Check for daily report (send at midnight or early morning)
                if self.config.reporting.daily_report:
                    if self._should_send_daily_report(now):
                        db_path = self._get_database_path()
                        if db_path.exists():
                            # Send report for yesterday
                            yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
                            self.email_reporter.send_daily_report(db_path, yesterday)
                            self.last_daily_report = now
                
                # Check for cleanup
                if self._should_run_cleanup(now):
                    self._cleanup_old_data()
                    self.last_cleanup = now
                
                # Sleep for a minute before next check
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def _should_send_hourly_report(self, now: datetime) -> bool:
        """Check if it's time to send an hourly report using ScheduleConfig."""
        schedule = self.config.reporting.schedule
        
        if not schedule.hourly_enabled:
            return False

        try:
            interval_minutes = max(1, int(schedule.get_hourly_interval_minutes()))
        except Exception:
            interval_minutes = max(1, int(getattr(schedule, 'hourly_interval_hours', 1) or 1) * 60)

        if self.last_hourly_report is None:
            # First run sends immediately unless send_on_start already did it.
            return True

        minutes_since = (now - self.last_hourly_report).total_seconds() / 60
        return minutes_since >= interval_minutes
    
    def _should_send_daily_report(self, now: datetime) -> bool:
        """Check if it's time to send a daily report using ScheduleConfig."""
        schedule = self.config.reporting.schedule
        
        if not schedule.daily_enabled:
            return False
        
        # Check if we're at the right hour and minute window
        if now.hour != schedule.daily_hour:
            return False
        
        target_minute = schedule.daily_minute
        grace = schedule.grace_period_minutes
        if not (target_minute <= now.minute < target_minute + grace):
            return False
        
        if self.last_daily_report is None:
            # First run at the right time
            return True
        
        # Ensure at least 23 hours since last daily report
        hours_since = (now - self.last_daily_report).total_seconds() / 3600
        return hours_since >= 23
    
    def _should_run_cleanup(self, now: datetime) -> bool:
        """Check if it's time to run cleanup."""
        if self.last_cleanup is None:
            return True
        
        # Run cleanup once per day
        hours_since = (now - self.last_cleanup).total_seconds() / 3600
        return hours_since >= 24
    
    def _cleanup_old_data(self):
        """Clean up old log files and database records."""
        try:
            data_dir = self.config.storage.get_data_directory()
            retention_days = self.config.storage.log_retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Clean old log files
            log_patterns = ['activity_*.log', 'service_*.log']
            for pattern in log_patterns:
                for log_file in data_dir.glob(pattern):
                    try:
                        # Extract date from filename
                        date_str = log_file.stem.split('_')[-1]
                        file_date = datetime.strptime(date_str, '%Y-%m-%d')
                        
                        if file_date < cutoff_date:
                            log_file.unlink()
                            logger.debug(f"Deleted old log file: {log_file}")
                    except Exception:
                        pass
            
            # Clean database if logger is available
            if self.logger_instance:
                self.logger_instance.cleanup_old_data(retention_days)
            
            logger.info(f"Cleanup completed - removed data older than {retention_days} days")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if HAS_WIN32:
    class FocusGuardWindowsService(win32serviceutil.ServiceFramework):
        """Windows Service implementation for Focus Guard."""
        
        _svc_name_ = "FocusGuardMonitor"
        _svc_display_name_ = "Focus Guard Activity Monitor"
        _svc_description_ = "Monitors application usage and sends activity reports"
        
        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.service = ActivityMonitorService()
        
        def SvcStop(self):
            """Handle service stop request."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            self.service.stop()
        
        def SvcDoRun(self):
            """Main service entry point."""
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.service.start()
            
            # Wait for stop signal
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)


def run_as_service():
    """Run as a Windows service."""
    if not HAS_WIN32:
        print("Windows service support requires pywin32. Install with: pip install pywin32")
        return
    
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FocusGuardWindowsService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(FocusGuardWindowsService)


def run_standalone(config: Optional[DeploymentConfig] = None):
    """Run as a standalone process (not as a service)."""
    import signal
    
    service = ActivityMonitorService(config)
    
    def signal_handler(signum, frame):
        print("\nShutting down...")
        service.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    service.start()
    
    print("Focus Guard Activity Monitor running. Press Ctrl+C to stop.")
    
    try:
        while service.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
