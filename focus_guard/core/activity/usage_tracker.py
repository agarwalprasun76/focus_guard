"""
Enhanced usage tracking system with idle period filtering and active duration calculation.

This module provides comprehensive usage tracking that filters out idle periods
and calculates accurate active usage time for applications and websites.
"""

import time
import threading
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from focus_guard.core.activity.models import WindowInfo, ActivityEvent
from focus_guard.core.activity.idle_detector import IdleDetector, IdleEvent, IdleState

logger = logging.getLogger(__name__)


@dataclass
class UsageSession:
    """Represents a continuous usage session for an application."""
    app_name: str
    window_title: str
    domain: Optional[str] = None
    url: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_duration: float = 0.0  # Total time including idle
    active_duration: float = 0.0  # Active time excluding idle periods
    idle_periods: List[Dict[str, Any]] = field(default_factory=list)
    is_browser: bool = False
    
    def add_idle_period(self, start_time: datetime, end_time: datetime):
        """Add an idle period to this session."""
        duration = (end_time - start_time).total_seconds()
        self.idle_periods.append({
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration
        })
    
    def calculate_active_duration(self) -> float:
        """Calculate active duration by subtracting idle periods."""
        total_idle = sum(period['duration'] for period in self.idle_periods)
        self.active_duration = max(0.0, self.total_duration - total_idle)
        return self.active_duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            'app_name': self.app_name,
            'window_title': self.window_title,
            'domain': self.domain,
            'url': self.url,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_duration': self.total_duration,
            'active_duration': self.active_duration,
            'idle_periods_count': len(self.idle_periods),
            'total_idle_time': sum(p['duration'] for p in self.idle_periods),
            'is_browser': self.is_browser
        }


@dataclass
class DailyUsageSummary:
    """Summary of usage for a specific day."""
    date: str  # YYYY-MM-DD format
    total_active_time: float = 0.0
    total_idle_time: float = 0.0
    sessions_count: int = 0
    applications: Dict[str, float] = field(default_factory=dict)  # app_name -> active_time
    domains: Dict[str, float] = field(default_factory=dict)  # domain -> active_time
    categories: Dict[str, float] = field(default_factory=dict)  # category -> active_time
    
    def add_session(self, session: UsageSession):
        """Add a session to the daily summary."""
        self.sessions_count += 1
        self.total_active_time += session.active_duration
        
        # Add to applications
        if session.app_name not in self.applications:
            self.applications[session.app_name] = 0.0
        self.applications[session.app_name] += session.active_duration
        
        # Add to domains if available
        if session.domain:
            if session.domain not in self.domains:
                self.domains[session.domain] = 0.0
            self.domains[session.domain] += session.active_duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary for serialization."""
        return {
            'date': self.date,
            'total_active_time': self.total_active_time,
            'total_idle_time': self.total_idle_time,
            'sessions_count': self.sessions_count,
            'applications': dict(sorted(self.applications.items(), key=lambda x: x[1], reverse=True)),
            'domains': dict(sorted(self.domains.items(), key=lambda x: x[1], reverse=True)),
            'categories': dict(sorted(self.categories.items(), key=lambda x: x[1], reverse=True))
        }


class UsageTracker:
    """
    Enhanced usage tracking system with idle period filtering.
    
    This class provides:
    - Active usage session tracking
    - Idle period detection and filtering
    - Application and domain usage statistics
    - Daily usage summaries
    - Real-time usage monitoring
    """
    
    def __init__(self, idle_detector: IdleDetector, session_timeout: float = 30.0):
        """
        Initialize the usage tracker.
        
        Args:
            idle_detector: IdleDetector instance for idle state monitoring
            session_timeout: Seconds of inactivity before ending a session
        """
        self.idle_detector = idle_detector
        self.session_timeout = session_timeout
        
        # Current state
        self.current_session: Optional[UsageSession] = None
        self.last_activity_time = datetime.now()
        self.current_idle_start: Optional[datetime] = None
        
        # Session storage
        self.completed_sessions: List[UsageSession] = []
        self.daily_summaries: Dict[str, DailyUsageSummary] = {}
        
        # Callbacks
        self.session_callbacks: List[Callable[[UsageSession], None]] = []
        
        # Threading
        self._tracking = False
        self._track_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Register idle state callback
        self.idle_detector.add_state_change_callback(self._on_idle_state_change)
        
    def start_tracking(self):
        """Start usage tracking."""
        if self._tracking:
            return
        
        self._tracking = True
        self._track_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._track_thread.start()
        logger.info("Usage tracking started")
    
    def stop_tracking(self):
        """Stop usage tracking."""
        self._tracking = False
        if self._track_thread:
            self._track_thread.join(timeout=1.0)
        
        # End current session if active
        if self.current_session:
            self._end_current_session()
        
        logger.info("Usage tracking stopped")
    
    def track_activity(self, window_info: WindowInfo):
        """
        Track activity for a specific window.
        
        Args:
            window_info: Information about the active window
        """
        with self._lock:
            now = datetime.now()
            self.last_activity_time = now
            
            # Check if we need to start a new session
            if self._should_start_new_session(window_info):
                if self.current_session:
                    self._end_current_session()
                self._start_new_session(window_info, now)
            
            # Update current session if active
            if self.current_session and not self.idle_detector.is_idle():
                self._update_current_session(now)
    
    def _should_start_new_session(self, window_info: WindowInfo) -> bool:
        """Check if we should start a new session for the given window."""
        if not self.current_session:
            return True
        
        # Different application
        if self.current_session.app_name != window_info.app_name:
            return True
        
        # Different domain for browsers
        if window_info.domain and self.current_session.domain != window_info.domain:
            return True
        
        # Session timeout
        time_since_last = (datetime.now() - self.last_activity_time).total_seconds()
        if time_since_last > self.session_timeout:
            return True
        
        return False
    
    def _start_new_session(self, window_info: WindowInfo, start_time: datetime):
        """Start a new usage session."""
        self.current_session = UsageSession(
            app_name=window_info.app_name,
            window_title=window_info.window_title,
            domain=window_info.domain,
            url=str(window_info.url) if window_info.url else None,
            start_time=start_time,
            is_browser=self._is_browser(window_info.app_name)
        )
        logger.debug(f"Started new session: {window_info.app_name} - {window_info.domain or 'N/A'}")
    
    def _update_current_session(self, current_time: datetime):
        """Update the current session with new activity."""
        if not self.current_session:
            return
        
        self.current_session.total_duration = (
            current_time - self.current_session.start_time
        ).total_seconds()
    
    def _end_current_session(self):
        """End the current usage session."""
        if not self.current_session:
            return
        
        now = datetime.now()
        self.current_session.end_time = now
        self.current_session.total_duration = (
            now - self.current_session.start_time
        ).total_seconds()
        
        # Calculate active duration
        self.current_session.calculate_active_duration()
        
        # Only save sessions with meaningful duration (> 5 seconds active time)
        if self.current_session.active_duration > 5.0:
            self.completed_sessions.append(self.current_session)
            self._update_daily_summary(self.current_session)
            
            # Notify callbacks
            for callback in self.session_callbacks:
                try:
                    callback(self.current_session)
                except Exception as e:
                    logger.error(f"Error in session callback: {e}")
            
            logger.debug(f"Ended session: {self.current_session.app_name} - "
                        f"Active: {self.current_session.active_duration:.1f}s")
        
        self.current_session = None
    
    def _on_idle_state_change(self, event: IdleEvent):
        """Handle idle state changes."""
        with self._lock:
            if event.current_state == IdleState.ACTIVE:
                # End of idle period
                if self.current_idle_start and self.current_session:
                    self.current_session.add_idle_period(
                        self.current_idle_start, 
                        event.timestamp
                    )
                self.current_idle_start = None
            else:
                # Start of idle period
                if event.previous_state == IdleState.ACTIVE:
                    self.current_idle_start = event.timestamp
    
    def _update_daily_summary(self, session: UsageSession):
        """Update daily summary with completed session."""
        date_str = session.start_time.strftime('%Y-%m-%d')
        
        if date_str not in self.daily_summaries:
            self.daily_summaries[date_str] = DailyUsageSummary(date=date_str)
        
        self.daily_summaries[date_str].add_session(session)
    
    def _tracking_loop(self):
        """Main tracking loop that runs in a separate thread."""
        while self._tracking:
            try:
                # Check for session timeout
                if self.current_session:
                    time_since_last = (datetime.now() - self.last_activity_time).total_seconds()
                    if time_since_last > self.session_timeout:
                        with self._lock:
                            self._end_current_session()
                
                time.sleep(5.0)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error in usage tracking loop: {e}")
                time.sleep(5.0)
    
    def _is_browser(self, app_name: str) -> bool:
        """Check if an application is a web browser."""
        browsers = ["chrome", "firefox", "msedge", "opera", "safari", "brave"]
        return any(browser in app_name.lower() for browser in browsers)
    
    def add_session_callback(self, callback: Callable[[UsageSession], None]):
        """Add a callback to be called when sessions are completed."""
        self.session_callbacks.append(callback)
    
    def remove_session_callback(self, callback: Callable[[UsageSession], None]):
        """Remove a session callback."""
        if callback in self.session_callbacks:
            self.session_callbacks.remove(callback)
    
    def get_current_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current active session."""
        with self._lock:
            if not self.current_session:
                return None
            
            current_duration = (datetime.now() - self.current_session.start_time).total_seconds()
            return {
                'app_name': self.current_session.app_name,
                'window_title': self.current_session.window_title,
                'domain': self.current_session.domain,
                'start_time': self.current_session.start_time.isoformat(),
                'current_duration': current_duration,
                'idle_periods_count': len(self.current_session.idle_periods),
                'is_browser': self.current_session.is_browser
            }
    
    def get_daily_summary(self, date: str = None) -> Optional[DailyUsageSummary]:
        """
        Get daily usage summary for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format, or today if None
            
        Returns:
            DailyUsageSummary: Summary for the specified date, or None if no data
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        return self.daily_summaries.get(date)
    
    def get_usage_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get usage statistics for the last N days.
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Dict[str, Any]: Comprehensive usage statistics
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        total_active_time = 0.0
        total_sessions = 0
        app_usage = defaultdict(float)
        domain_usage = defaultdict(float)
        
        # Aggregate data from daily summaries
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            if date_str in self.daily_summaries:
                summary = self.daily_summaries[date_str]
                total_active_time += summary.total_active_time
                total_sessions += summary.sessions_count
                
                for app, time_spent in summary.applications.items():
                    app_usage[app] += time_spent
                
                for domain, time_spent in summary.domains.items():
                    domain_usage[domain] += time_spent
            
            current_date += timedelta(days=1)
        
        return {
            'period': f"{start_date} to {end_date}",
            'total_active_time': total_active_time,
            'total_sessions': total_sessions,
            'average_daily_active_time': total_active_time / days,
            'top_applications': dict(sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:10]),
            'top_domains': dict(sorted(domain_usage.items(), key=lambda x: x[1], reverse=True)[:10]),
            'sessions_per_day': total_sessions / days
        }
    
    def get_recent_sessions(self, hours: int = 24) -> List[UsageSession]:
        """
        Get recent usage sessions from the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List[UsageSession]: Recent sessions
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            session for session in self.completed_sessions
            if session.start_time >= cutoff_time
        ]
    
    def clear_old_data(self, days_to_keep: int = 30):
        """
        Clear old usage data to manage memory usage.
        
        Args:
            days_to_keep: Number of days of data to retain
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Clear old sessions
        self.completed_sessions = [
            session for session in self.completed_sessions
            if session.start_time >= cutoff_date
        ]
        
        # Clear old daily summaries
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
        old_dates = [
            date for date in self.daily_summaries.keys()
            if date < cutoff_date_str
        ]
        for date in old_dates:
            del self.daily_summaries[date]
        
        logger.info(f"Cleared usage data older than {days_to_keep} days")
