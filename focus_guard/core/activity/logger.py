"""
Activity Logger for Focus Guard.

This module provides functionality to log foreground application activity
with precise timestamps for correlation with browser tab activity.
"""

import os
import sys
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any, Union

from focus_guard.core.activity.models import WindowInfo, ActivityEvent
from focus_guard.core.activity.monitor import ActivityMonitor


class ActivityLogger:
    """
    Logs foreground application activity with precise timestamps.
    
    This class provides functionality to:
    1. Monitor and log the currently active application/window
    2. Store logs with precise timestamps for correlation with browser activity
    3. Manage log rotation and cleanup
    4. Support correlation with browser tab activity
    """
    
    def __init__(self, 
                 interval_seconds: int = 5, 
                 log_dir: Optional[str] = None,
                 activity_monitor: Optional[ActivityMonitor] = None):
        """
        Initialize the activity logger.
        
        Args:
            interval_seconds: Sampling interval in seconds
            log_dir: Directory to store log files (defaults to %LOCALAPPDATA%/FocusGuard)
            activity_monitor: Optional ActivityMonitor instance to use
        """
        self.interval = interval_seconds
        self.activity_monitor = activity_monitor or ActivityMonitor()
        self.running = False
        self.thread = None
        
        # Set up logging directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
            self.log_dir = Path(local_appdata) / "FocusGuard"
            
        # Create directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logger
        self.logger = logging.getLogger("activity_logger")
        self._configure_logger()
        
        # Last update time for log rotation check
        self._last_rotation_check = datetime.now()
        
        # Current log paths
        self._current_tab_log, self._current_debug_log = self._get_current_log_paths()
    
    def _configure_logger(self):
        """Configure the logger with appropriate handlers and format."""
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
    
    def _get_current_log_paths(self) -> Tuple[Path, Path]:
        """
        Get the paths for the current day's log files.
        
        Returns:
            Tuple[Path, Path]: Paths to the current tab log and debug log files
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        tab_log = self.log_dir / f"activity_log_{today_str}.log"
        debug_log = self.log_dir / f"focusguard_debug_{today_str}.log"
        return tab_log, debug_log
    
    def get_current_log_path(self) -> Path:
        """
        Get the path for the current day's activity log file.
        
        Returns:
            Path: Path to the current log file
        """
        # Check if we need to rotate logs
        now = datetime.now()
        if (now - self._last_rotation_check).total_seconds() > 3600:  # Check once per hour
            self._current_tab_log, self._current_debug_log = self._get_current_log_paths()
            self._last_rotation_check = now
            
        return self._current_tab_log
    
    def log_activity(self, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """
        Log the current foreground application activity.
        
        Args:
            timestamp: Optional ISO format timestamp to use (for synchronization)
            
        Returns:
            Dict[str, Any]: Activity data that was logged
        """
        # Get current timestamp if not provided
        if not timestamp:
            timestamp = datetime.now().isoformat()
        elif isinstance(timestamp, str):
            # Ensure timestamp is in ISO format
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp = dt.isoformat()
            except ValueError:
                timestamp = datetime.now().isoformat()
        
        # Get active window info using the activity monitor
        window_info = self.activity_monitor.get_active_window()
        
        if not window_info:
            # Create a placeholder window info if none is available
            window_info = WindowInfo(
                app_name='unknown',
                window_title='unknown',
                pid='0',
                timestamp=datetime.now()
            )
        
        # Create activity data dictionary
        activity_data = window_info.to_dict()
        
        # Add timestamp
        activity_data['timestamp'] = timestamp
        
        # Add browser flag
        is_browser = self._is_browser(activity_data['app_name'])
        activity_data['is_browser'] = is_browser
        
        # Write to log file
        try:
            log_path = self.get_current_log_path()
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} | ")
                f.write(f"App: {activity_data['app_name']} | ")
                f.write(f"Title: {activity_data['window_title']} | ")
                f.write(f"PID: {activity_data['pid']}")
                
                if 'url' in activity_data:
                    f.write(f" | URL: {activity_data['url']}")
                if 'domain' in activity_data:
                    f.write(f" | Domain: {activity_data['domain']}")
                
                f.write("\n")
                
            # Also write to JSON format for easier parsing
            json_log_path = log_path.with_suffix('.json')
            self._append_to_json_log(json_log_path, activity_data)
            
            self.logger.debug(f"Logged activity: {activity_data['app_name']} - {activity_data['window_title']}")
        except Exception as e:
            self.logger.error(f"Error logging activity: {e}")
        
        return activity_data
    
    def _append_to_json_log(self, json_path: Path, activity_data: Dict[str, Any]):
        """
        Append activity data to JSON log file.
        
        Args:
            json_path: Path to JSON log file
            activity_data: Activity data to append
        """
        try:
            # Read existing data if file exists
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)
                except json.JSONDecodeError:
                    log_data = {"activities": []}
            else:
                log_data = {"activities": []}
            
            # Append new activity
            log_data["activities"].append(activity_data)
            
            # Write back to file
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error appending to JSON log: {e}")
    
    def _monitoring_loop(self):
        """Main monitoring loop that runs in a separate thread."""
        self.logger.info(f"Activity monitoring started with {self.interval}s interval")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Log current activity with precise timestamp
                timestamp = datetime.now().isoformat()
                self.log_activity(timestamp)
                
                # Calculate sleep time to maintain consistent interval
                elapsed = time.time() - start_time
                sleep_time = max(0.1, self.interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Error in activity monitoring: {e}")
                time.sleep(1)  # Sleep briefly to avoid tight error loops
    
    def start(self):
        """Start the activity monitoring in a separate thread."""
        if self.running:
            self.logger.warning("Activity monitoring is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("Activity monitoring thread started")
    
    def stop(self):
        """Stop the activity monitoring."""
        if not self.running:
            self.logger.warning("Activity monitoring is not running")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
            self.logger.info("Activity monitoring stopped")
    
    def get_available_logs(self) -> List[Path]:
        """
        Get a list of available activity log files.
        
        Returns:
            List[Path]: List of paths to log files
        """
        return sorted(self.log_dir.glob("activity_log_*.log"))
    
    def get_log_for_date(self, date_str: str) -> Optional[Path]:
        """
        Get the activity log file for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Optional[Path]: Path to the log file if it exists, None otherwise
        """
        log_path = self.log_dir / f"activity_log_{date_str}.log"
        return log_path if log_path.exists() else None
    
    def clean_old_logs(self, days_to_keep: int = 30):
        """
        Remove activity logs older than the specified number of days.
        
        Args:
            days_to_keep: Number of days of logs to keep
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_file in self.log_dir.glob("activity_log_*.log"):
            try:
                # Extract date from filename
                date_str = log_file.stem.split('_')[-1]
                log_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                # Remove if older than cutoff
                if log_date < cutoff_date:
                    os.remove(log_file)
                    self.logger.info(f"Removed old log file: {log_file}")
                    
                    # Also remove JSON version if it exists
                    json_file = log_file.with_suffix('.json')
                    if json_file.exists():
                        os.remove(json_file)
                        self.logger.info(f"Removed old JSON log file: {json_file}")
            except (ValueError, IndexError):
                self.logger.warning(f"Could not parse date from log filename: {log_file}")
    
    def _is_browser(self, app_name: str) -> bool:
        """
        Check if an application is a web browser.
        
        Args:
            app_name: Name of the application.
            
        Returns:
            bool: True if the application is a web browser, False otherwise.
        """
        browsers = ["chrome", "firefox", "msedge", "edge", "opera", "safari", "brave"]
        return any(browser in app_name.lower() for browser in browsers)


# Singleton instance
_activity_logger_instance = None

def get_activity_logger(**kwargs) -> ActivityLogger:
    """
    Get the singleton activity logger instance.
    
    Args:
        **kwargs: Arguments to pass to the ActivityLogger constructor
        
    Returns:
        ActivityLogger: The singleton instance
    """
    global _activity_logger_instance
    if _activity_logger_instance is None:
        _activity_logger_instance = ActivityLogger(**kwargs)
    return _activity_logger_instance


def log_activity(timestamp: Optional[str] = None) -> Dict[str, Any]:
    """
    Log the current foreground application activity.
    
    Args:
        timestamp: Optional ISO format timestamp to use (for synchronization)
        
    Returns:
        Dict[str, Any]: Activity data that was logged
    """
    logger = get_activity_logger()
    return logger.log_activity(timestamp)


def start_activity_logging(interval_seconds: int = 5, **kwargs):
    """
    Start activity logging.
    
    Args:
        interval_seconds: Sampling interval in seconds
        **kwargs: Additional arguments to pass to the ActivityLogger constructor
    """
    logger = get_activity_logger(interval_seconds=interval_seconds, **kwargs)
    logger.start()


def stop_activity_logging():
    """Stop activity logging."""
    if _activity_logger_instance is not None:
        _activity_logger_instance.stop()
