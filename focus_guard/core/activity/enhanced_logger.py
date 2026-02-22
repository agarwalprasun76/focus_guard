"""
Enhanced Activity Logger with idle detection and usage tracking integration.

This module extends the basic activity logging with comprehensive idle detection,
active usage tracking, and SQLite database integration for robust data storage.
"""

import os
import sys
import time
import json
import logging
import threading
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any, Union, Callable

from focus_guard.core.activity.models import WindowInfo, ActivityEvent
from focus_guard.core.activity.monitor import ActivityMonitor
from focus_guard.core.activity.idle_detector import IdleDetector, IdleConfiguration, IdleEvent, IdleState
from focus_guard.core.activity.usage_tracker import UsageTracker, UsageSession

logger = logging.getLogger(__name__)


class SQLiteUsageDatabase:
    """SQLite database manager for usage data storage."""
    
    def __init__(self, db_path: str):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Create database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS usage_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL,
                    window_title TEXT,
                    domain TEXT,
                    url TEXT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    total_duration REAL DEFAULT 0,
                    active_duration REAL DEFAULT 0,
                    idle_periods_count INTEGER DEFAULT 0,
                    is_browser BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS idle_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    duration REAL NOT NULL,
                    idle_state TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES usage_sessions (id)
                );
                
                CREATE TABLE IF NOT EXISTS blocking_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT,
                    domain TEXT,
                    url TEXT,
                    block_reason TEXT,
                    block_type TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    duration REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS tab_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    browser TEXT NOT NULL,
                    tab_id TEXT,
                    url TEXT NOT NULL,
                    domain TEXT,
                    title TEXT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    active_duration REAL DEFAULT 0,
                    classification TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS visible_windows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL,
                    window_title TEXT,
                    is_foreground BOOLEAN DEFAULT 0,
                    screen_percent REAL DEFAULT 0,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS activity_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT NOT NULL,
                    window_title TEXT,
                    domain TEXT,
                    url TEXT,
                    is_foreground BOOLEAN DEFAULT 1,
                    sample_seconds REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_visible_windows_timestamp 
                    ON visible_windows(timestamp);
                CREATE INDEX IF NOT EXISTS idx_visible_windows_app 
                    ON visible_windows(app_name, timestamp);
                CREATE INDEX IF NOT EXISTS idx_activity_samples_timestamp
                    ON activity_samples(timestamp);
                CREATE INDEX IF NOT EXISTS idx_activity_samples_app
                    ON activity_samples(app_name, timestamp);
                CREATE INDEX IF NOT EXISTS idx_activity_samples_domain
                    ON activity_samples(domain, timestamp);
                
                CREATE TABLE IF NOT EXISTS app_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    productivity_score REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    total_active_time REAL DEFAULT 0,
                    total_idle_time REAL DEFAULT 0,
                    sessions_count INTEGER DEFAULT 0,
                    top_app TEXT,
                    top_domain TEXT,
                    productivity_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create indexes for performance
                CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON usage_sessions(start_time);
                CREATE INDEX IF NOT EXISTS idx_sessions_app_name ON usage_sessions(app_name);
                CREATE INDEX IF NOT EXISTS idx_sessions_domain ON usage_sessions(domain);
                CREATE INDEX IF NOT EXISTS idx_idle_periods_session ON idle_periods(session_id);
                CREATE INDEX IF NOT EXISTS idx_blocking_events_timestamp ON blocking_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_tab_sessions_start_time ON tab_sessions(start_time);
                CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_summaries(date);
            ''')
    
    def save_session(self, session: UsageSession) -> int:
        """Save a usage session to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usage_sessions 
                (app_name, window_title, domain, url, start_time, end_time, 
                 total_duration, active_duration, idle_periods_count, is_browser)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.app_name,
                session.window_title,
                session.domain,
                session.url,
                session.start_time,
                session.end_time,
                session.total_duration,
                session.active_duration,
                len(session.idle_periods),
                session.is_browser
            ))
            
            session_id = cursor.lastrowid
            
            # Save idle periods
            for idle_period in session.idle_periods:
                cursor.execute('''
                    INSERT INTO idle_periods (session_id, start_time, end_time, duration)
                    VALUES (?, ?, ?, ?)
                ''', (
                    session_id,
                    idle_period['start_time'],
                    idle_period['end_time'],
                    idle_period['duration']
                ))
            
            return session_id
    
    def get_daily_stats(self, date: str) -> Dict[str, Any]:
        """Get daily usage statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get basic stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as sessions_count,
                    SUM(active_duration) as total_active_time,
                    SUM(total_duration - active_duration) as total_idle_time
                FROM usage_sessions 
                WHERE DATE(start_time) = ?
            ''', (date,))
            
            basic_stats = cursor.fetchone()
            
            # Get top applications
            cursor.execute('''
                SELECT app_name, SUM(active_duration) as total_time
                FROM usage_sessions 
                WHERE DATE(start_time) = ?
                GROUP BY app_name
                ORDER BY total_time DESC
                LIMIT 10
            ''', (date,))
            
            top_apps = [dict(row) for row in cursor.fetchall()]
            
            # Get top domains
            cursor.execute('''
                SELECT domain, SUM(active_duration) as total_time
                FROM usage_sessions 
                WHERE DATE(start_time) = ? AND domain IS NOT NULL
                GROUP BY domain
                ORDER BY total_time DESC
                LIMIT 10
            ''', (date,))
            
            top_domains = [dict(row) for row in cursor.fetchall()]
            
            # Get total monitored time (first to last session)
            cursor.execute('''
                SELECT 
                    MIN(start_time) as first_session,
                    MAX(end_time) as last_session
                FROM usage_sessions 
                WHERE DATE(start_time) = ?
            ''', (date,))
            time_range = cursor.fetchone()
            
            total_monitored_time = 0.0
            if time_range['first_session'] and time_range['last_session']:
                try:
                    first = datetime.fromisoformat(time_range['first_session'])
                    last = datetime.fromisoformat(time_range['last_session'])
                    total_monitored_time = (last - first).total_seconds()
                except (ValueError, TypeError):
                    pass
            
            # Get visible windows stats (apps that were on screen)
            cursor.execute('''
                SELECT app_name, 
                       COUNT(*) as sample_count,
                       SUM(CASE WHEN is_foreground = 1 THEN 1 ELSE 0 END) as foreground_count,
                       AVG(screen_percent) as avg_screen_percent
                FROM visible_windows 
                WHERE DATE(timestamp) = ?
                GROUP BY app_name
                ORDER BY sample_count DESC
                LIMIT 15
            ''', (date,))
            
            visible_apps = [dict(row) for row in cursor.fetchall()]
            
            return {
                'date': date,
                'sessions_count': basic_stats['sessions_count'] or 0,
                'total_active_time': basic_stats['total_active_time'] or 0.0,
                'total_idle_time': basic_stats['total_idle_time'] or 0.0,
                'total_monitored_time': total_monitored_time,
                'top_applications': top_apps,
                'top_domains': top_domains,
                'visible_applications': visible_apps
            }
    
    def log_visible_windows(self, windows: List[Dict[str, Any]], foreground_app: str = None):
        """
        Log all currently visible windows.
        
        Args:
            windows: List of visible window dictionaries
            foreground_app: Name of the foreground (active) app
        """
        if not windows:
            return
        
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for window in windows:
                app_name = window.get('app_name', 'unknown')
                is_foreground = 1 if app_name == foreground_app else 0
                screen_percent = window.get('percent', 0) * 100  # Convert to percentage
                
                cursor.execute('''
                    INSERT INTO visible_windows 
                    (app_name, window_title, is_foreground, screen_percent, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    app_name,
                    window.get('window_title', ''),
                    is_foreground,
                    screen_percent,
                    timestamp
                ))
            
            conn.commit()

    def log_activity_sample(self, window_info: WindowInfo, sample_seconds: float):
        """Persist a per-tick foreground activity sample for interval-accurate reporting."""
        if not window_info:
            return

        timestamp = datetime.now().isoformat()
        safe_sample_seconds = float(max(0.0, sample_seconds or 0.0))

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO activity_samples
                (app_name, window_title, domain, url, is_foreground, sample_seconds, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    window_info.app_name,
                    window_info.window_title,
                    str(window_info.domain) if window_info.domain else None,
                    str(window_info.url) if window_info.url else None,
                    1,
                    safe_sample_seconds,
                    timestamp,
                ),
            )
            conn.commit()
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Remove data older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete old visible windows
            cursor.execute('DELETE FROM visible_windows WHERE timestamp < ?', (cutoff_date,))
            cursor.execute('DELETE FROM activity_samples WHERE timestamp < ?', (cutoff_date,))
            
            # Delete old sessions and related data
            cursor.execute('DELETE FROM usage_sessions WHERE start_time < ?', (cutoff_date,))
            cursor.execute('DELETE FROM blocking_events WHERE timestamp < ?', (cutoff_date,))
            cursor.execute('DELETE FROM tab_sessions WHERE start_time < ?', (cutoff_date,))
            
            # Clean up orphaned idle periods
            cursor.execute('''
                DELETE FROM idle_periods 
                WHERE session_id NOT IN (SELECT id FROM usage_sessions)
            ''')
            
            # Vacuum to reclaim space
            cursor.execute('VACUUM')
            
            logger.info(f"Cleaned up database data older than {days_to_keep} days")


class EnhancedActivityLogger:
    """
    Enhanced activity logger with idle detection and usage tracking.
    
    This class provides comprehensive activity monitoring including:
    - Idle detection and filtering
    - Active usage tracking
    - SQLite database storage
    - Real-time usage analytics
    - Application blocking event logging
    """
    
    def __init__(self, 
                 interval_seconds: int = 5,
                 log_dir: Optional[str] = None,
                 idle_config: Optional[IdleConfiguration] = None,
                 activity_monitor: Optional[ActivityMonitor] = None):
        """
        Initialize the enhanced activity logger.
        
        Args:
            interval_seconds: Sampling interval in seconds
            log_dir: Directory to store log files and database
            idle_config: Configuration for idle detection
            activity_monitor: Optional ActivityMonitor instance
        """
        self.interval = interval_seconds
        self.activity_monitor = activity_monitor or ActivityMonitor(idle_config)
        
        # Set up logging directory
        if log_dir is None:
            if sys.platform == "win32":
                log_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'FocusGuard')
            else:
                log_dir = os.path.expanduser('~/.focus_guard')
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        db_path = self.log_dir / 'usage.db'
        self.database = SQLiteUsageDatabase(str(db_path))
        
        # Initialize usage tracker
        self.usage_tracker = UsageTracker(
            self.activity_monitor._idle_detector,
            session_timeout=30.0
        )
        
        # Add session callback to save to database
        self.usage_tracker.add_session_callback(self._on_session_completed)
        
        # Threading
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Statistics
        self.total_logs = 0
        self.last_log_time: Optional[datetime] = None
        
        # Callbacks
        self.activity_callbacks: List[Callable[[WindowInfo], None]] = []
        self.idle_callbacks: List[Callable[[IdleEvent], None]] = []
        
        # Add idle callback
        self.activity_monitor.add_idle_callback(self._on_idle_event)
    
    def start(self):
        """Start the enhanced activity logging."""
        if self.running:
            logger.warning("Activity logger is already running")
            return
        
        self.running = True
        
        # Start idle monitoring
        self.activity_monitor.start_idle_monitoring()
        
        # Start usage tracking
        self.usage_tracker.start_tracking()
        
        # Start activity logging thread
        self.thread = threading.Thread(target=self._logging_loop, daemon=True)
        self.thread.start()
        
        logger.info("Enhanced activity logging started")
    
    def stop(self):
        """Stop the enhanced activity logging."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop components
        self.activity_monitor.stop_idle_monitoring()
        self.usage_tracker.stop_tracking()
        
        # Wait for thread to finish
        if self.thread:
            self.thread.join(timeout=2.0)
        
        logger.info("Enhanced activity logging stopped")
    
    def _logging_loop(self):
        """Main logging loop that runs in a separate thread."""
        while self.running:
            try:
                self._log_current_activity()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in activity logging loop: {e}")
                time.sleep(self.interval)
    
    def _log_current_activity(self):
        """Log current activity if system is active."""
        # Skip logging if system is idle
        if self.activity_monitor.is_idle():
            return
        
        window_info = self.activity_monitor.get_active_window()
        if not window_info:
            return
        
        # Track activity in usage tracker
        self.usage_tracker.track_activity(window_info)

        # Persist canonical per-tick sample so reporting can aggregate any ad-hoc interval
        # without waiting for session closure.
        self.database.log_activity_sample(window_info, float(self.interval))
        
        # Log all visible windows (comprehensive tracking)
        self._log_visible_windows(window_info.app_name if window_info else None)
        
        # Update statistics
        self.total_logs += 1
        self.last_log_time = datetime.now()
        
        # Notify callbacks
        for callback in self.activity_callbacks:
            try:
                callback(window_info)
            except Exception as e:
                logger.error(f"Error in activity callback: {e}")
        
        # Log to traditional text file (for backward compatibility)
        self._write_text_log(window_info)
    
    def _log_visible_windows(self, foreground_app: str = None):
        """
        Log all currently visible windows for comprehensive tracking.
        
        This captures apps that are on screen but not necessarily in focus,
        like a YouTube video playing while working in another app.
        """
        try:
            # Get all visible windows from the platform monitor
            visible_windows = self.activity_monitor.get_visible_windows()
            if visible_windows:
                self.database.log_visible_windows(visible_windows, foreground_app)
        except Exception as e:
            logger.debug(f"Failed to log visible windows: {e}")
    
    def _write_text_log(self, window_info: WindowInfo):
        """Write activity to text log file for backward compatibility."""
        log_file = self.log_dir / f"activity_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} | App: {window_info.app_name} | Title: {window_info.window_title}"
        
        if window_info.domain:
            log_entry += f" | Domain: {window_info.domain}"
        if window_info.url:
            log_entry += f" | URL: {window_info.url}"
        
        log_entry += "\n"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write text log: {e}")
    
    def _on_session_completed(self, session: UsageSession):
        """Handle completed usage session."""
        try:
            # Save to database
            session_id = self.database.save_session(session)
            logger.debug(f"Saved session {session_id}: {session.app_name} - {session.active_duration:.1f}s")
        except Exception as e:
            logger.error(f"Failed to save session to database: {e}")
    
    def _on_idle_event(self, event: IdleEvent):
        """Handle idle state change events."""
        logger.debug(f"Idle state changed: {event.previous_state.value} -> {event.current_state.value}")
        
        # Notify callbacks
        for callback in self.idle_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in idle callback: {e}")
    
    def add_activity_callback(self, callback: Callable[[WindowInfo], None]):
        """Add callback for activity events."""
        self.activity_callbacks.append(callback)
    
    def add_idle_callback(self, callback: Callable[[IdleEvent], None]):
        """Add callback for idle state changes."""
        self.idle_callbacks.append(callback)
    
    def log_blocking_event(self, app_name: str, domain: str = None, url: str = None, 
                          block_reason: str = None, block_type: str = "application"):
        """
        Log an application or website blocking event.
        
        Args:
            app_name: Name of the blocked application
            domain: Domain that was blocked (for websites)
            url: Full URL that was blocked
            block_reason: Reason for blocking
            block_type: Type of block (application, domain, url)
        """
        try:
            with sqlite3.connect(self.database.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO blocking_events 
                    (app_name, domain, url, block_reason, block_type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (app_name, domain, url, block_reason, block_type, datetime.now()))
            
            logger.info(f"Logged blocking event: {block_type} - {app_name or domain}")
        except Exception as e:
            logger.error(f"Failed to log blocking event: {e}")
    
    def get_current_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current active session."""
        return self.usage_tracker.get_current_session_info()
    
    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """Get daily usage summary from database."""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        return self.database.get_daily_stats(date)
    
    def get_usage_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get comprehensive usage statistics."""
        stats = self.usage_tracker.get_usage_statistics(days)
        
        # Add idle detection statistics
        idle_stats = self.activity_monitor.get_idle_statistics()
        stats.update({
            'idle_detection': idle_stats,
            'current_idle_state': idle_stats.get('current_state'),
            'current_idle_time': idle_stats.get('current_idle_time', 0.0)
        })
        
        return stats
    
    def get_recent_sessions(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent usage sessions."""
        sessions = self.usage_tracker.get_recent_sessions(hours)
        return [session.to_dict() for session in sessions]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current logger status and statistics."""
        return {
            'running': self.running,
            'total_logs': self.total_logs,
            'last_log_time': self.last_log_time.isoformat() if self.last_log_time else None,
            'current_session': self.get_current_session_info(),
            'idle_state': self.activity_monitor.get_idle_state().value,
            'idle_time': self.activity_monitor.get_idle_time_seconds(),
            'database_path': str(self.database.db_path),
            'log_directory': str(self.log_dir)
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old log data and database records."""
        # Clean database
        self.database.cleanup_old_data(days_to_keep)
        
        # Clean old text log files
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_file in self.log_dir.glob("activity_*.log"):
            try:
                file_date_str = log_file.stem.replace("activity_", "")
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    logger.debug(f"Deleted old log file: {log_file}")
            except Exception as e:
                logger.warning(f"Failed to process log file {log_file}: {e}")
        
        # Clean usage tracker data
        self.usage_tracker.clear_old_data(days_to_keep)
        
        logger.info(f"Cleaned up activity data older than {days_to_keep} days")


# Singleton instance for backward compatibility
_enhanced_logger_instance: Optional[EnhancedActivityLogger] = None


def get_enhanced_logger(interval_seconds: int = 5,
                       log_dir: Optional[str] = None,
                       idle_config: Optional[IdleConfiguration] = None) -> EnhancedActivityLogger:
    """Get or create the singleton enhanced activity logger instance."""
    global _enhanced_logger_instance
    
    if _enhanced_logger_instance is None:
        _enhanced_logger_instance = EnhancedActivityLogger(
            interval_seconds=interval_seconds,
            log_dir=log_dir,
            idle_config=idle_config
        )
    
    return _enhanced_logger_instance
