"""
Session adapter for activity logging.

This module provides an adapter that connects session monitoring events
to activity logging, automatically pausing and resuming logging based
on user session events.
"""

import logging
from typing import Dict, Any, Optional

from core_v2.activity.platform.session_monitor import SessionListener, SessionEvent
from core_v2.activity.platform.windows_session import create_session_monitor
from core_v2.activity.coordinator import (
    get_activity_coordinator, pause_activity_logging, resume_activity_logging
)


class ActivitySessionAdapter(SessionListener):
    """
    Adapter that connects session events to activity logging.
    
    This class listens for session events and automatically pauses/resumes
    activity logging based on user login/logout events.
    """
    
    def __init__(self):
        """Initialize the activity session adapter."""
        self.logger = logging.getLogger("activity_session_adapter")
        self._configure_logger()
        self.session_monitor = create_session_monitor()
        
        if self.session_monitor:
            self.session_monitor.add_listener(self)
        else:
            self.logger.warning("No supported session monitor available")
    
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
    
    def on_session_event(self, event_type: SessionEvent, event_data: Dict[str, Any]) -> None:
        """
        Handle session events by pausing/resuming activity logging.
        
        Args:
            event_type: Type of session event
            event_data: Additional data about the event
        """
        timestamp = event_data.get("timestamp", "unknown")
        
        if event_type == SessionEvent.LOGOUT:
            self.logger.info(f"User logout detected at {timestamp}, pausing activity logging")
            pause_activity_logging()
        elif event_type == SessionEvent.LOGIN:
            self.logger.info(f"User login detected at {timestamp}, resuming activity logging")
            resume_activity_logging()
        elif event_type == SessionEvent.LOCK:
            self.logger.info(f"Workstation lock detected at {timestamp}, pausing activity logging")
            pause_activity_logging()
        elif event_type == SessionEvent.UNLOCK:
            self.logger.info(f"Workstation unlock detected at {timestamp}, resuming activity logging")
            resume_activity_logging()
    
    def start(self):
        """Start session monitoring."""
        if self.session_monitor:
            self.session_monitor.start()
            self.logger.info("Session monitoring started")
        else:
            self.logger.warning("Cannot start session monitoring: no supported monitor available")
    
    def stop(self):
        """Stop session monitoring."""
        if self.session_monitor:
            self.session_monitor.stop()
            self.logger.info("Session monitoring stopped")


# Singleton instance
_adapter_instance = None

def get_activity_session_adapter() -> Optional[ActivitySessionAdapter]:
    """
    Get the singleton activity session adapter instance.
    
    Returns:
        Optional[ActivitySessionAdapter]: The singleton instance, or None if
                                         no supported session monitor is available.
    """
    global _adapter_instance
    if _adapter_instance is None:
        adapter = ActivitySessionAdapter()
        if adapter.session_monitor:
            _adapter_instance = adapter
    return _adapter_instance


def start_session_monitoring():
    """Start session monitoring for activity logging."""
    adapter = get_activity_session_adapter()
    if adapter:
        adapter.start()
        return True
    return False


def stop_session_monitoring():
    """Stop session monitoring for activity logging."""
    global _adapter_instance
    if _adapter_instance:
        _adapter_instance.stop()
        return True
    return False
