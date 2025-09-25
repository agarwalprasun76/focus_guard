"""
Enhanced Activity Monitor with comprehensive idle detection and usage tracking.

This module provides the EnhancedActivityMonitor class that integrates:
- Cross-platform idle detection
- Active usage tracking with idle filtering
- Usage session management
- Real-time activity monitoring
- Daily usage summaries
"""

import time
import threading
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
import logging

from focus_guard.core.activity.models import WindowInfo, ActivityEvent
from focus_guard.core.activity.idle_detector import IdleDetector, IdleConfiguration, IdleEvent, IdleState
from focus_guard.core.activity.usage_tracker import UsageTracker, UsageSession, DailyUsageSummary
from focus_guard.core.activity.monitor import ActivityMonitor

logger = logging.getLogger(__name__)


class EnhancedActivityMonitor:
    """
    Enhanced activity monitor with comprehensive idle detection and usage tracking.
    
    This class provides:
    - Real-time activity monitoring with idle detection
    - Active usage session tracking
    - Idle period filtering and statistics
    - Daily usage summaries and analytics
    - Configurable idle thresholds and callbacks
    """
    
    def __init__(self, 
                 idle_config: Optional[IdleConfiguration] = None,
                 session_timeout: float = 30.0,
                 polling_interval: float = 5.0):
        """
        Initialize the enhanced activity monitor.
        
        Args:
            idle_config: Configuration for idle detection thresholds
            session_timeout: Seconds of inactivity before ending a session
            polling_interval: Seconds between activity checks
        """
        # Core components
        self.idle_detector = IdleDetector(idle_config)
        self.usage_tracker = UsageTracker(self.idle_detector, session_timeout)
        self.activity_monitor = ActivityMonitor(idle_config)
        
        # Configuration
        self.polling_interval = polling_interval
        self.session_timeout = session_timeout
        
        # State tracking
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Callbacks
        self.activity_callbacks: List[Callable[[WindowInfo], None]] = []
        self.session_callbacks: List[Callable[[UsageSession], None]] = []
        self.idle_callbacks: List[Callable[[IdleEvent], None]] = []
        
        # Statistics
        self.monitoring_start_time: Optional[datetime] = None
        self.total_monitoring_time = 0.0
        self.activity_events_count = 0
        
        # Setup internal callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Setup internal callbacks for component integration."""
        # Forward idle events to our callbacks
        self.idle_detector.add_state_change_callback(self._on_idle_state_change)
        
        # Forward session events to our callbacks
        self.usage_tracker.add_session_callback(self._on_session_complete)
    
    def _on_idle_state_change(self, event: IdleEvent):
        """Handle idle state changes and forward to callbacks."""
        logger.debug(f"Idle state changed: {event.previous_state.value} -> {event.current_state.value}")
        
        # Notify callbacks
        for callback in self.idle_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in idle callback: {e}")
    
    def _on_session_complete(self, session: UsageSession):
        """Handle completed sessions and forward to callbacks."""
        logger.debug(f"Session completed: {session.app_name} - {session.active_duration:.1f}s active")
        
        # Notify callbacks
        for callback in self.session_callbacks:
            try:
                callback(session)
            except Exception as e:
                logger.error(f"Error in session callback: {e}")
    
    def start_monitoring(self):
        """Start comprehensive activity monitoring."""
        if self._monitoring:
            logger.warning("Monitoring is already running")
            return
        
        with self._lock:
            self._monitoring = True
            self.monitoring_start_time = datetime.now()
        
        # Start component monitoring
        self.idle_detector.start_monitoring()
        self.usage_tracker.start_tracking()
        
        # Start main monitoring loop
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("Enhanced activity monitoring started")
    
    def stop_monitoring(self):
        """Stop activity monitoring and cleanup."""
        if not self._monitoring:
            return
        
        with self._lock:
            self._monitoring = False
            if self.monitoring_start_time:
                self.total_monitoring_time += (
                    datetime.now() - self.monitoring_start_time
                ).total_seconds()
        
        # Stop component monitoring
        self.usage_tracker.stop_tracking()
        self.idle_detector.stop_monitoring()
        
        # Wait for monitoring thread to finish
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        
        logger.info("Enhanced activity monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop that tracks activity and updates usage."""
        logger.debug("Starting monitoring loop")
        
        while self._monitoring:
            try:
                # Get current active window
                window_info = self.activity_monitor.get_active_window()
                
                if window_info and not self.idle_detector.is_idle():
                    # Track activity if user is active
                    self.usage_tracker.track_activity(window_info)
                    self.activity_events_count += 1
                    
                    # Notify activity callbacks
                    for callback in self.activity_callbacks:
                        try:
                            callback(window_info)
                        except Exception as e:
                            logger.error(f"Error in activity callback: {e}")
                
                time.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.polling_interval)
        
        logger.debug("Monitoring loop stopped")
    
    def get_current_usage_session(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current active usage session.
        
        Returns:
            Optional[Dict[str, Any]]: Current session info, or None if no active session
        """
        return self.usage_tracker.get_current_session_info()
    
    def is_user_active(self) -> bool:
        """
        Check if user is currently active (not idle).
        
        Returns:
            bool: True if user is currently active
        """
        return self.idle_detector.is_active()
    
    def get_idle_time_seconds(self) -> float:
        """
        Get current system idle time in seconds.
        
        Returns:
            float: Current idle time in seconds
        """
        return self.idle_detector.get_idle_time_seconds()
    
    def get_idle_state(self) -> IdleState:
        """
        Get current idle state.
        
        Returns:
            IdleState: Current idle state (ACTIVE, SHORT_IDLE, MEDIUM_IDLE, LONG_IDLE)
        """
        return self.idle_detector.get_current_state()
    
    def get_daily_summary(self, date: str = None) -> Optional[DailyUsageSummary]:
        """
        Get daily usage summary for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format, or today if None
            
        Returns:
            Optional[DailyUsageSummary]: Daily summary, or None if no data
        """
        return self.usage_tracker.get_daily_summary(date)
    
    def get_usage_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get comprehensive usage statistics for the last N days.
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Dict[str, Any]: Comprehensive usage statistics
        """
        return self.usage_tracker.get_usage_statistics(days)
    
    def get_idle_statistics(self) -> Dict[str, Any]:
        """
        Get idle detection statistics.
        
        Returns:
            Dict[str, Any]: Idle detection statistics
        """
        return self.idle_detector.get_statistics()
    
    def get_recent_sessions(self, hours: int = 24) -> List[UsageSession]:
        """
        Get recent usage sessions from the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List[UsageSession]: Recent usage sessions
        """
        return self.usage_tracker.get_recent_sessions(hours)
    
    def get_recent_idle_periods(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent idle periods from the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List[Dict[str, Any]]: Recent idle periods
        """
        return self.idle_detector.get_recent_idle_periods(hours)
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """
        Get overall monitoring statistics.
        
        Returns:
            Dict[str, Any]: Monitoring statistics
        """
        current_monitoring_time = 0.0
        if self._monitoring and self.monitoring_start_time:
            current_monitoring_time = (
                datetime.now() - self.monitoring_start_time
            ).total_seconds()
        
        total_time = self.total_monitoring_time + current_monitoring_time
        
        return {
            'monitoring_active': self._monitoring,
            'monitoring_start_time': self.monitoring_start_time.isoformat() if self.monitoring_start_time else None,
            'total_monitoring_time': total_time,
            'activity_events_count': self.activity_events_count,
            'polling_interval': self.polling_interval,
            'session_timeout': self.session_timeout,
            'events_per_hour': (self.activity_events_count / (total_time / 3600)) if total_time > 0 else 0
        }
    
    def add_activity_callback(self, callback: Callable[[WindowInfo], None]):
        """
        Add a callback for activity events.
        
        Args:
            callback: Function to call when activity is detected
        """
        self.activity_callbacks.append(callback)
    
    def remove_activity_callback(self, callback: Callable[[WindowInfo], None]):
        """
        Remove an activity callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.activity_callbacks:
            self.activity_callbacks.remove(callback)
    
    def add_session_callback(self, callback: Callable[[UsageSession], None]):
        """
        Add a callback for completed sessions.
        
        Args:
            callback: Function to call when sessions are completed
        """
        self.session_callbacks.append(callback)
    
    def remove_session_callback(self, callback: Callable[[UsageSession], None]):
        """
        Remove a session callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.session_callbacks:
            self.session_callbacks.remove(callback)
    
    def add_idle_callback(self, callback: Callable[[IdleEvent], None]):
        """
        Add a callback for idle state changes.
        
        Args:
            callback: Function to call when idle state changes
        """
        self.idle_callbacks.append(callback)
    
    def remove_idle_callback(self, callback: Callable[[IdleEvent], None]):
        """
        Remove an idle state callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.idle_callbacks:
            self.idle_callbacks.remove(callback)
    
    def reset_statistics(self):
        """Reset all statistics and tracking data."""
        self.idle_detector.reset_statistics()
        self.usage_tracker.clear_old_data(days_to_keep=0)  # Clear all data
        
        with self._lock:
            self.activity_events_count = 0
            self.total_monitoring_time = 0.0
            if self._monitoring:
                self.monitoring_start_time = datetime.now()
        
        logger.info("Enhanced activity monitor statistics reset")
    
    def configure_idle_thresholds(self, 
                                short_idle: float = None,
                                medium_idle: float = None, 
                                long_idle: float = None,
                                sensitivity: float = None):
        """
        Update idle detection thresholds.
        
        Args:
            short_idle: Short idle threshold in seconds
            medium_idle: Medium idle threshold in seconds
            long_idle: Long idle threshold in seconds
            sensitivity: Sensitivity multiplier for thresholds
        """
        config = self.idle_detector.config
        
        if short_idle is not None:
            config.short_idle_threshold = short_idle
        if medium_idle is not None:
            config.medium_idle_threshold = medium_idle
        if long_idle is not None:
            config.long_idle_threshold = long_idle
        if sensitivity is not None:
            config.sensitivity = sensitivity
        
        logger.info(f"Updated idle thresholds: short={config.short_idle_threshold}s, "
                   f"medium={config.medium_idle_threshold}s, long={config.long_idle_threshold}s, "
                   f"sensitivity={config.sensitivity}")
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of all monitoring components.
        
        Returns:
            Dict[str, Any]: Complete status information
        """
        return {
            'monitoring': self.get_monitoring_statistics(),
            'idle_detection': self.get_idle_statistics(),
            'current_session': self.get_current_usage_session(),
            'usage_stats': self.get_usage_statistics(days=1),
            'recent_sessions_count': len(self.get_recent_sessions(hours=1)),
            'recent_idle_periods_count': len(self.get_recent_idle_periods(hours=1))
        }
