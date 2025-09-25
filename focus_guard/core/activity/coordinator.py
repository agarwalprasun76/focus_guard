"""
Activity Logging Coordinator for Focus Guard.

This module coordinates application and browser activity logging,
ensuring proper synchronization and correlation between the two.
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any, Union

from focus_guard.core.activity.logger import (
    ActivityLogger, get_activity_logger,
    start_activity_logging, stop_activity_logging
)
from focus_guard.core.activity.browser.logger import (
    BrowserActivityLogger, get_browser_activity_logger,
    start_browser_activity_logging, stop_browser_activity_logging
)


class ActivityLoggingCoordinator:
    """
    Coordinates application and browser activity logging.
    
    This class provides functionality to:
    1. Start and manage both application and browser activity logging
    2. Ensure synchronized timestamps between the two
    3. Provide a unified interface for activity logging
    4. Support correlation and analysis of the combined logs
    5. Pause and resume logging based on user session state
    """
    
    def __init__(self, 
                 interval_seconds: int = 5, 
                 log_dir: Optional[str] = None):
        """
        Initialize the activity logging coordinator.
        
        Args:
            interval_seconds: Sampling interval in seconds
            log_dir: Directory to store log files (defaults to %LOCALAPPDATA%/FocusGuard)
        """
        self.interval = interval_seconds
        
        # Set up logging directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
            self.log_dir = Path(local_appdata) / "FocusGuard"
            
        # Create directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logger
        self.logger = logging.getLogger("activity_coordinator")
        self._configure_logger()
        
        # Initialize the loggers
        self.activity_logger = get_activity_logger(
            interval_seconds=interval_seconds,
            log_dir=str(self.log_dir)
        )
        
        self.browser_logger = get_browser_activity_logger(
            interval_seconds=interval_seconds,
            log_dir=str(self.log_dir)
        )
        
        # Coordination state
        self.running = False
        self.paused = False
        self.thread = None
    
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
    
    def start(self):
        """Start coordinated activity logging."""
        if self.running:
            self.logger.warning("Activity logging is already running")
            return
        
        self.running = True
        
        # Start the individual loggers
        self.activity_logger.start()
        self.browser_logger.start()
        
        # Start coordination thread
        self.thread = threading.Thread(target=self._coordination_loop)
        self.thread.daemon = True
        self.thread.start()
        
        self.logger.info("Coordinated activity logging started")
    
    def stop(self):
        """Stop coordinated activity logging."""
        if not self.running:
            self.logger.warning("Activity logging is not running")
            return
        
        self.running = False
        self.paused = False
        
        # Stop the individual loggers
        self.activity_logger.stop()
        self.browser_logger.stop()
        
        # Stop coordination thread
        if self.thread:
            self.thread.join(timeout=5.0)
            self.logger.info("Coordination thread stopped")
        
        self.logger.info("Coordinated activity logging stopped")
        
    def pause(self):
        """Pause activity logging (e.g., when user logs out)."""
        if not self.running:
            self.logger.warning("Activity logging is not running, cannot pause")
            return
            
        if self.paused:
            self.logger.info("Activity logging is already paused")
            return
            
        self.paused = True
        self.logger.info("Activity logging paused")
        
    def resume(self):
        """Resume activity logging (e.g., when user logs in)."""
        if not self.running:
            self.logger.warning("Activity logging is not running, cannot resume")
            return
            
        if not self.paused:
            self.logger.info("Activity logging is already running")
            return
            
        self.paused = False
        self.logger.info("Activity logging resumed")
    
    def _coordination_loop(self):
        """Coordination loop that runs in a separate thread."""
        while self.running:
            try:
                # Skip logging if paused
                if not self.paused:
                    # Generate a synchronized timestamp
                    timestamp = datetime.now().isoformat()
                    
                    # Log coordination event
                    self._log_coordination_event(timestamp)
                
                # Sleep for the interval
                time.sleep(self.interval)
            except Exception as e:
                self.logger.error(f"Error in coordination loop: {e}")
                time.sleep(1)  # Sleep briefly before retrying
    
    def _log_coordination_event(self, timestamp: str):
        """
        Log a coordination event with the synchronized timestamp.
        
        Args:
            timestamp: ISO format timestamp for synchronization
        """
        try:
            # Create coordination log path
            today_str = datetime.now().strftime("%Y-%m-%d")
            coord_log = self.log_dir / f"activity_coordination_{today_str}.log"
            
            # Log coordination event
            with open(coord_log, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} | Coordination event\n")
            
            self.logger.debug(f"Logged coordination event at {timestamp}")
        except Exception as e:
            self.logger.error(f"Error logging coordination event: {e}")
    
    def log_snapshot(self, event_type: str = "snapshot", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Take a synchronized snapshot of both application and browser activity.
        
        Args:
            event_type: Type of event for the snapshot
            metadata: Additional metadata for the snapshot
            
        Returns:
            Dict[str, Any]: Combined snapshot data
        """
        # Generate a synchronized timestamp
        timestamp = datetime.now().isoformat()
        
        # Get application and browser activity
        app_activity = self.activity_logger.log_activity(timestamp)
        browser_activity = self.browser_logger.log_tab_activity(timestamp)
        
        # Combine into a snapshot
        snapshot = {
            'timestamp': timestamp,
            'event_type': event_type,
            'app_activity': app_activity,
            'browser_activity': browser_activity,
            'metadata': metadata or {}
        }
        
        # Log the snapshot
        self._log_snapshot(snapshot)
        
        return snapshot
    
    def _log_snapshot(self, snapshot: Dict[str, Any]):
        """
        Log a combined activity snapshot.
        
        Args:
            snapshot: Combined activity snapshot
        """
        try:
            # Create snapshot log path
            today_str = datetime.now().strftime("%Y-%m-%d")
            snapshot_log = self.log_dir / f"activity_snapshot_{today_str}.json"
            
            # Read existing snapshots if file exists
            if snapshot_log.exists():
                try:
                    with open(snapshot_log, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)
                except json.JSONDecodeError:
                    log_data = {"snapshots": []}
            else:
                log_data = {"snapshots": []}
            
            # Append new snapshot
            log_data["snapshots"].append(snapshot)
            
            # Write back to file
            with open(snapshot_log, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"Logged activity snapshot at {snapshot['timestamp']}")
        except Exception as e:
            self.logger.error(f"Error logging snapshot: {e}")
    
    def clean_old_logs(self, days_to_keep: int = 30):
        """
        Remove all activity logs older than the specified number of days.
        
        Args:
            days_to_keep: Number of days of logs to keep
        """
        # Clean application activity logs
        self.activity_logger.clean_old_logs(days_to_keep)
        
        # Clean browser activity logs
        self.browser_logger.clean_old_logs(days_to_keep)
        
        # Clean coordination and snapshot logs
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for pattern in ["activity_coordination_*.log", "activity_snapshot_*.json"]:
            for log_file in self.log_dir.glob(pattern):
                try:
                    # Extract date from filename
                    date_str = log_file.stem.split('_')[-1]
                    log_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    # Remove if older than cutoff
                    if log_date < cutoff_date:
                        os.remove(log_file)
                        self.logger.info(f"Removed old log file: {log_file}")
                except (ValueError, IndexError):
                    self.logger.warning(f"Could not parse date from log filename: {log_file}")


# Singleton instance
_coordinator_instance = None

def get_activity_coordinator(**kwargs) -> ActivityLoggingCoordinator:
    """
    Get the singleton activity logging coordinator instance.
    
    Args:
        **kwargs: Arguments to pass to the ActivityLoggingCoordinator constructor
        
    Returns:
        ActivityLoggingCoordinator: The singleton instance
    """
    global _coordinator_instance
    if _coordinator_instance is None:
        _coordinator_instance = ActivityLoggingCoordinator(**kwargs)
    return _coordinator_instance


def start_coordinated_logging(interval_seconds: int = 5, **kwargs):
    """
    Start coordinated activity logging.
    
    Args:
        interval_seconds: Sampling interval in seconds
        **kwargs: Additional arguments to pass to the ActivityLoggingCoordinator constructor
    """
    coordinator = get_activity_coordinator(interval_seconds=interval_seconds, **kwargs)
    coordinator.start()


def stop_coordinated_logging():
    """Stop coordinated activity logging."""
    if _coordinator_instance is not None:
        _coordinator_instance.stop()


def pause_activity_logging():
    """Pause activity logging (e.g., when user logs out)."""
    coordinator = get_activity_coordinator()
    coordinator.pause()


def resume_activity_logging():
    """Resume activity logging (e.g., when user logs in)."""
    coordinator = get_activity_coordinator()
    coordinator.resume()


def take_activity_snapshot(event_type: str = "snapshot", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Take a synchronized snapshot of both application and browser activity.
    
    Args:
        event_type: Type of event for the snapshot
        metadata: Additional metadata for the snapshot
        
    Returns:
        Dict[str, Any]: Combined snapshot data
    """
    coordinator = get_activity_coordinator()
    return coordinator.log_snapshot(event_type, metadata)
