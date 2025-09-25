"""
Browser Activity Logger for Focus Guard.

This module provides functionality to log browser tab activity
with precise timestamps for correlation with application activity.
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any, Union

from focus_guard.core.activity.models import WindowInfo, ActivityEvent
from focus_guard.core.activity.browser.tab_monitor import BrowserTabMonitor
from focus_guard.core.domain.models import URL, Domain


class BrowserActivityLogger:
    """
    Logs browser tab activity with precise timestamps.
    
    This class provides functionality to:
    1. Monitor and log browser tab activity
    2. Store logs with precise timestamps for correlation with application activity
    3. Manage log rotation and cleanup
    4. Support correlation with application activity
    """
    
    def __init__(self, 
                 interval_seconds: int = 5, 
                 log_dir: Optional[str] = None,
                 tab_monitor: Optional[BrowserTabMonitor] = None):
        """
        Initialize the browser activity logger.
        
        Args:
            interval_seconds: Sampling interval in seconds
            log_dir: Directory to store log files (defaults to %LOCALAPPDATA%/FocusGuard)
            tab_monitor: Optional BrowserTabMonitor instance to use
        """
        self.interval = interval_seconds
        self.tab_monitor = tab_monitor or BrowserTabMonitor()
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
        self.logger = logging.getLogger("browser_activity_logger")
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
        tab_log = self.log_dir / f"browser_activity_{today_str}.log"
        debug_log = self.log_dir / f"browser_debug_{today_str}.log"
        return tab_log, debug_log
    
    def get_current_log_path(self) -> Path:
        """
        Get the path for the current day's browser activity log file.
        
        Returns:
            Path: Path to the current log file
        """
        # Check if we need to rotate logs
        now = datetime.now()
        if (now - self._last_rotation_check).total_seconds() > 3600:  # Check once per hour
            self._current_tab_log, self._current_debug_log = self._get_current_log_paths()
            self._last_rotation_check = now
            
        return self._current_tab_log
    
    def log_tab_activity(self, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """
        Log the current browser tab activity.
        
        Args:
            timestamp: Optional ISO format timestamp to use (for synchronization)
            
        Returns:
            Dict[str, Any]: Tab activity data that was logged
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
        
        # Get active tab info using the tab monitor
        tabs = self.tab_monitor.get_all_tabs()
        active_tab = self.tab_monitor.get_active_tab()
        
        # Create tab activity data
        tab_activity = {
            'timestamp': timestamp,
            'active_tab': active_tab,
            'all_tabs': tabs,
            'tab_count': len(tabs)
        }
        
        # Write to log file
        try:
            log_path = self.get_current_log_path()
            
            # Log active tab info
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} | ")
                
                if active_tab:
                    f.write(f"Active Tab: {active_tab.get('title', 'Unknown')} | ")
                    f.write(f"URL: {active_tab.get('url', 'Unknown')} | ")
                    f.write(f"Browser: {active_tab.get('browser', 'Unknown')}")
                else:
                    f.write("No active browser tab")
                
                f.write("\n")
                
            # Also write to JSON format for easier parsing
            json_log_path = log_path.with_suffix('.json')
            self._append_to_json_log(json_log_path, tab_activity)
            
            self.logger.debug(f"Logged tab activity: {len(tabs)} tabs, active: {active_tab.get('title', 'None') if active_tab else 'None'}")
        except Exception as e:
            self.logger.error(f"Error logging tab activity: {e}")
        
        return tab_activity
    
    def _append_to_json_log(self, json_path: Path, tab_activity: Dict[str, Any]):
        """
        Append tab activity data to JSON log file.
        
        Args:
            json_path: Path to JSON log file
            tab_activity: Tab activity data to append
        """
        try:
            # Read existing data if file exists
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)
                except json.JSONDecodeError:
                    log_data = {"tab_activities": []}
            else:
                log_data = {"tab_activities": []}
            
            # Append new activity
            log_data["tab_activities"].append(tab_activity)
            
            # Write back to file
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error appending to JSON log: {e}")
    
    def _monitoring_loop(self):
        """Main monitoring loop that runs in a separate thread."""
        self.logger.info(f"Browser tab monitoring started with {self.interval}s interval")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Log current tab activity with precise timestamp
                timestamp = datetime.now().isoformat()
                self.log_tab_activity(timestamp)
                
                # Calculate sleep time to maintain consistent interval
                elapsed = time.time() - start_time
                sleep_time = max(0.1, self.interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Error in browser tab monitoring: {e}")
                time.sleep(1)  # Sleep briefly to avoid tight error loops
    
    def start(self):
        """Start the browser tab monitoring in a separate thread."""
        if self.running:
            self.logger.warning("Browser tab monitoring is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("Browser tab monitoring thread started")
    
    def stop(self):
        """Stop the browser tab monitoring."""
        if not self.running:
            self.logger.warning("Browser tab monitoring is not running")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
            self.logger.info("Browser tab monitoring stopped")
    
    def get_available_logs(self) -> List[Path]:
        """
        Get a list of available browser activity log files.
        
        Returns:
            List[Path]: List of paths to log files
        """
        return sorted(self.log_dir.glob("browser_activity_*.log"))
    
    def get_log_for_date(self, date_str: str) -> Optional[Path]:
        """
        Get the browser activity log file for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Optional[Path]: Path to the log file if it exists, None otherwise
        """
        log_path = self.log_dir / f"browser_activity_{date_str}.log"
        return log_path if log_path.exists() else None
    
    def clean_old_logs(self, days_to_keep: int = 30):
        """
        Remove browser activity logs older than the specified number of days.
        
        Args:
            days_to_keep: Number of days of logs to keep
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_file in self.log_dir.glob("browser_activity_*.log"):
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


# Singleton instance
_browser_logger_instance = None

def get_browser_activity_logger(**kwargs) -> BrowserActivityLogger:
    """
    Get the singleton browser activity logger instance.
    
    Args:
        **kwargs: Arguments to pass to the BrowserActivityLogger constructor
        
    Returns:
        BrowserActivityLogger: The singleton instance
    """
    global _browser_logger_instance
    if _browser_logger_instance is None:
        _browser_logger_instance = BrowserActivityLogger(**kwargs)
    return _browser_logger_instance


def log_tab_activity(timestamp: Optional[str] = None) -> Dict[str, Any]:
    """
    Log the current browser tab activity.
    
    Args:
        timestamp: Optional ISO format timestamp to use (for synchronization)
        
    Returns:
        Dict[str, Any]: Tab activity data that was logged
    """
    logger = get_browser_activity_logger()
    return logger.log_tab_activity(timestamp)


def start_browser_activity_logging(interval_seconds: int = 5, **kwargs):
    """
    Start browser activity logging.
    
    Args:
        interval_seconds: Sampling interval in seconds
        **kwargs: Additional arguments to pass to the BrowserActivityLogger constructor
    """
    logger = get_browser_activity_logger(interval_seconds=interval_seconds, **kwargs)
    logger.start()


def stop_browser_activity_logging():
    """Stop browser activity logging."""
    if _browser_logger_instance is not None:
        _browser_logger_instance.stop()
