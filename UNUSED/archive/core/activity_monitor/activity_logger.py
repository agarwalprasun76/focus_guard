#!/usr/bin/env python
"""
Activity Logger

This module provides functionality to log foreground application activity
with precise timestamps for correlation with browser tab activity.
"""

import os
import sys
import time
import datetime
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any

# Import activity monitor components
from core.activity_monitor.activity_monitor import ActivityMonitor

# Setup logging
logger = logging.getLogger("activity_logger")


class ActivityLogger:
    """
    Logs foreground application activity with precise timestamps.
    
    This class provides functionality to:
    1. Monitor and log the currently active application/window
    2. Store logs with precise timestamps for correlation with browser activity
    3. Manage log rotation and cleanup
    """
    
    def __init__(self, interval_seconds: int = 5, log_dir: Optional[str] = None):
        """
        Initialize the activity logger.
        
        Args:
            interval_seconds: Sampling interval in seconds
            log_dir: Directory to store log files (defaults to %LOCALAPPDATA%/FocusGuard)
        """
        self.interval = interval_seconds
        self.activity_monitor = ActivityMonitor()
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
        
        # Configure file handler for the logger
        self._configure_logger()
    
    def _configure_logger(self):
        """Configure the logger with appropriate handlers and format."""
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(console_handler)
    
    def get_current_log_path(self) -> Path:
        """
        Get the path for the current day's activity log file.
        
        Returns:
            Path: Path to the current log file
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"activity_log_{today}.log"
    
    def log_activity(self, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """
        Log the current foreground application activity.
        
        Args:
            timestamp: Optional ISO format timestamp to use (for synchronization)
            
        Returns:
            Dict: Activity data that was logged
        """
        # Get current timestamp if not provided
        if not timestamp:
            timestamp = datetime.datetime.now().isoformat()
        
        # Get active window info
        active_window = self.activity_monitor.get_active_window()
        
        if not active_window:
            active_window = {
                'app_name': 'unknown',
                'window_title': 'unknown',
                'pid': 0,
                'percent': 0.0
            }
        
        # Get top windows to determine screen occupation percentage
        top_windows = self.activity_monitor.get_top_windows(top_region=2000)  # Increased region to capture more windows
        screen_percent = 0.0
        
        # Find the active window in top windows to get its percentage
        active_pid = active_window.get('pid', 0)
        active_title = active_window.get('window_title', '').lower()
        active_app = active_window.get('app_name', '').lower()
        
        # Try to match window by PID first
        for window in top_windows:
            if window.get('pid') == active_pid:
                screen_percent = window.get('percent', 0.0)
                break
        
        # If no match by PID, try matching by title and app name
        if screen_percent == 0.0 and active_title and active_app:
            for window in top_windows:
                window_title = window.get('window_title', '').lower()
                window_app = window.get('app_name', '').lower()
                
                if (active_app in window_app or window_app in active_app) and \
                   (active_title in window_title or window_title in active_title):
                    screen_percent = window.get('percent', 0.0)
                    break
        
        # If still no match, use the largest window with the same app name as a fallback
        if screen_percent == 0.0 and active_app:
            max_area = 0
            for window in top_windows:
                window_app = window.get('app_name', '').lower()
                if active_app in window_app or window_app in active_app:
                    area = window.get('area', 0)
                    if area > max_area:
                        max_area = area
                        screen_percent = window.get('percent', 0.0)
        
        # Format log entry with screen occupation percentage
        log_entry = f"{timestamp}|{active_window.get('app_name', 'unknown')}|{active_window.get('window_title', 'unknown')}|{screen_percent:.4f}"
        
        # Write to log file
        log_path = self.get_current_log_path()
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
        
        # Return the activity data
        return {
            'timestamp': timestamp,
            'app_name': active_window.get('app_name', 'unknown'),
            'window_title': active_window.get('window_title', 'unknown'),
            'pid': active_window.get('pid', 0),
            'screen_percent': screen_percent
        }
    
    def _monitoring_loop(self):
        """Main monitoring loop that runs in a separate thread."""
        logger.info(f"Activity monitoring started with {self.interval}s interval")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Log current activity with precise timestamp
                timestamp = datetime.datetime.now().isoformat()
                self.log_activity(timestamp)
                
                # Calculate sleep time to maintain consistent interval
                elapsed = time.time() - start_time
                sleep_time = max(0.1, self.interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in activity monitoring: {e}")
                time.sleep(1)  # Sleep briefly to avoid tight error loops
    
    def start(self):
        """Start the activity monitoring in a separate thread."""
        if self.running:
            logger.warning("Activity monitoring is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Activity monitoring thread started")
    
    def stop(self):
        """Stop the activity monitoring."""
        if not self.running:
            logger.warning("Activity monitoring is not running")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
            logger.info("Activity monitoring stopped")
    
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
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        
        for log_file in self.log_dir.glob("activity_log_*.log"):
            try:
                # Extract date from filename
                date_str = log_file.stem.split('_')[-1]
                log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                
                # Remove if older than cutoff
                if log_date < cutoff_date:
                    os.remove(log_file)
                    logger.info(f"Removed old log file: {log_file}")
            except (ValueError, IndexError):
                logger.warning(f"Could not parse date from log filename: {log_file}")


def main():
    """Main function for standalone execution."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start activity logger
    activity_logger = ActivityLogger(interval_seconds=5)
    
    try:
        logger.info("Starting activity logging...")
        activity_logger.start()
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping activity logging...")
        activity_logger.stop()
        logger.info("Activity logging stopped")
    except Exception as e:
        logger.error(f"Error in activity logging: {e}")
        activity_logger.stop()


if __name__ == "__main__":
    main()
