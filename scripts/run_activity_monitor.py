#!/usr/bin/env python
"""
Focus Guard - Standalone Activity Monitor

This script runs the EnhancedActivityLogger as a standalone service for logging
user activity. It can operate independently without browser extension, but is
designed to integrate seamlessly when the extension becomes available.

Usage:
    python scripts/run_activity_monitor.py [--interval SECONDS] [--verbose]
    python scripts/run_activity_monitor.py --summary [--date YYYY-MM-DD]
    python scripts/run_activity_monitor.py --stats [--days N]

Data Storage:
    - SQLite database: %LOCALAPPDATA%/FocusGuard/usage.db
    - Text logs: %LOCALAPPDATA%/FocusGuard/activity_YYYY-MM-DD.log
"""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from focus_guard.core.activity.enhanced_logger import EnhancedActivityLogger
from focus_guard.core.activity.idle_detector import IdleConfiguration, IdleEvent, IdleState
from focus_guard.core.activity.models import WindowInfo


class ActivityMonitorRunner:
    """
    Standalone runner for the Enhanced Activity Logger.
    
    Provides:
    - Console output for real-time monitoring
    - Graceful shutdown handling
    - Browser extension integration hooks (for future use)
    - Status reporting
    """
    
    def __init__(self, 
                 interval_seconds: int = 5,
                 verbose: bool = False,
                 log_dir: Optional[str] = None):
        """
        Initialize the activity monitor runner.
        
        Args:
            interval_seconds: How often to sample activity (default: 5s)
            verbose: Enable verbose console output
            log_dir: Custom log directory (default: %LOCALAPPDATA%/FocusGuard)
        """
        self.interval = interval_seconds
        self.verbose = verbose
        self.running = False
        
        # Configure idle detection thresholds
        idle_config = IdleConfiguration(
            short_idle_threshold=30.0,   # 30 seconds - brief pause
            medium_idle_threshold=120.0,  # 2 minutes - short break
            long_idle_threshold=300.0,    # 5 minutes - away from computer
            sensitivity=1.0
        )
        
        # Initialize the enhanced logger
        self.logger = EnhancedActivityLogger(
            interval_seconds=interval_seconds,
            log_dir=log_dir,
            idle_config=idle_config
        )
        
        # Track statistics for console display
        self.start_time: Optional[datetime] = None
        self.last_window: Optional[str] = None
        self.activity_count = 0
        
        # Browser extension integration placeholder
        self.browser_extension_connected = False
        self.tab_server_url: Optional[str] = None
        
        # Register callbacks for real-time monitoring
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Set up callbacks for activity and idle events."""
        self.logger.add_activity_callback(self._on_activity)
        self.logger.add_idle_callback(self._on_idle_change)
    
    def _on_activity(self, window_info: WindowInfo):
        """Handle activity events - called when active window is detected."""
        self.activity_count += 1
        
        # Build display string
        app_display = window_info.app_name
        title_display = window_info.window_title[:50] + "..." if len(window_info.window_title) > 50 else window_info.window_title
        
        # Check if window changed
        current_window = f"{window_info.app_name}|{window_info.window_title}"
        window_changed = current_window != self.last_window
        self.last_window = current_window
        
        if self.verbose or window_changed:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Color coding for different app types (ANSI colors)
            if self._is_browser(window_info.app_name):
                app_color = "\033[94m"  # Blue for browsers
                if window_info.domain:
                    app_display = f"{window_info.app_name} [{window_info.domain}]"
            elif self._is_productivity_app(window_info.app_name):
                app_color = "\033[92m"  # Green for productivity
            else:
                app_color = "\033[93m"  # Yellow for other
            
            reset_color = "\033[0m"
            
            if window_changed:
                print(f"[{timestamp}] {app_color}▶ {app_display}{reset_color}: {title_display}")
            elif self.verbose:
                print(f"[{timestamp}]   {app_display}: {title_display}")
    
    def _on_idle_change(self, event: IdleEvent):
        """Handle idle state changes."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        state_colors = {
            IdleState.ACTIVE: "\033[92m",      # Green
            IdleState.SHORT_IDLE: "\033[93m",  # Yellow
            IdleState.MEDIUM_IDLE: "\033[91m", # Red
            IdleState.LONG_IDLE: "\033[95m",   # Magenta
        }
        
        color = state_colors.get(event.current_state, "")
        reset = "\033[0m"
        
        if event.current_state == IdleState.ACTIVE:
            print(f"[{timestamp}] {color}◉ User returned - active{reset}")
        else:
            idle_duration = event.idle_duration or 0
            print(f"[{timestamp}] {color}○ Idle: {event.current_state.value} ({idle_duration:.0f}s){reset}")
    
    def _is_browser(self, app_name: str) -> bool:
        """Check if application is a web browser."""
        browsers = ["chrome", "firefox", "msedge", "edge", "opera", "safari", "brave"]
        return any(b in app_name.lower() for b in browsers)
    
    def _is_productivity_app(self, app_name: str) -> bool:
        """Check if application is a productivity app."""
        productivity_apps = [
            "code", "windsurf", "visual studio", "pycharm", "intellij",
            "word", "excel", "powerpoint", "outlook", "teams",
            "notepad", "sublime", "atom", "vim", "emacs",
            "terminal", "powershell", "cmd"
        ]
        return any(p in app_name.lower() for p in productivity_apps)
    
    def start(self):
        """Start the activity monitor."""
        if self.running:
            print("Activity monitor is already running")
            return
        
        self.running = True
        self.start_time = datetime.now()
        
        # Start the logger
        self.logger.start()
        
        # Print startup banner
        self._print_banner()
    
    def stop(self):
        """Stop the activity monitor."""
        if not self.running:
            return
        
        self.running = False
        self.logger.stop()
        
        # Print summary
        self._print_summary()
    
    def _print_banner(self):
        """Print startup banner with configuration info."""
        print("\n" + "=" * 60)
        print("  Focus Guard - Activity Monitor")
        print("=" * 60)
        print(f"  Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Sampling interval: {self.interval} seconds")
        print(f"  Log directory: {self.logger.log_dir}")
        print(f"  Database: {self.logger.database.db_path}")
        print()
        print("  Idle thresholds:")
        print("    - Short idle: 30s (brief pause)")
        print("    - Medium idle: 2min (short break)")
        print("    - Long idle: 5min (away)")
        print()
        
        # Browser extension status
        if self.browser_extension_connected:
            print("  \033[92m✓ Browser extension connected\033[0m")
        else:
            print("  \033[93m○ Browser extension not connected\033[0m")
            print("    (URL/domain tracking limited to window titles)")
        
        print()
        print("  Press Ctrl+C to stop...")
        print("=" * 60 + "\n")
    
    def _print_summary(self):
        """Print session summary on shutdown."""
        if not self.start_time:
            return
        
        duration = datetime.now() - self.start_time
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        print("\n" + "=" * 60)
        print("  Session Summary")
        print("=" * 60)
        print(f"  Duration: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        print(f"  Activity samples: {self.activity_count}")
        
        # Get daily summary from database
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            summary = self.logger.get_daily_summary(today)
            
            if summary['sessions_count'] > 0:
                print(f"\n  Today's Statistics:")
                print(f"    Sessions: {summary['sessions_count']}")
                print(f"    Active time: {summary['total_active_time']/60:.1f} minutes")
                
                if summary['top_applications']:
                    print(f"\n  Top Applications:")
                    for i, app in enumerate(summary['top_applications'][:5], 1):
                        print(f"    {i}. {app['app_name']}: {app['total_time']/60:.1f} min")
                
                if summary['top_domains']:
                    print(f"\n  Top Domains:")
                    for i, domain in enumerate(summary['top_domains'][:5], 1):
                        print(f"    {i}. {domain['domain']}: {domain['total_time']/60:.1f} min")
        except Exception as e:
            print(f"  (Could not load summary: {e})")
        
        print("=" * 60 + "\n")
    
    def get_status(self) -> dict:
        """Get current status for external queries."""
        return {
            'running': self.running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'activity_count': self.activity_count,
            'browser_extension_connected': self.browser_extension_connected,
            'logger_status': self.logger.get_status()
        }
    
    # =========================================================================
    # Browser Extension Integration Hooks
    # =========================================================================
    
    def connect_browser_extension(self, tab_server_url: str = "http://localhost:58392"):
        """
        Connect to browser extension tab server.
        
        This method will be called when browser extension integration is ready.
        For now, it's a placeholder that can be enabled later.
        
        Args:
            tab_server_url: URL of the tab server (default: http://localhost:5000)
        """
        self.tab_server_url = tab_server_url
        # TODO: Implement actual connection when extension is deployed
        # self.browser_extension_connected = True
        print(f"[INFO] Browser extension integration placeholder - URL: {tab_server_url}")
    
    def on_tab_update(self, tab_data: dict):
        """
        Handle tab update from browser extension.
        
        This method will receive tab data when the browser extension is connected.
        
        Args:
            tab_data: Dictionary with tab information (url, title, domain, etc.)
        """
        # TODO: Implement when extension is ready
        # This will allow enriching activity data with actual URLs
        pass


def print_daily_summary(date: str = None, log_dir: str = None):
    """Print daily usage summary report."""
    from datetime import datetime, timedelta
    
    logger = EnhancedActivityLogger(log_dir=log_dir)
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    summary = logger.get_daily_summary(date)
    
    print("\n" + "=" * 60)
    print("  DAILY USAGE SUMMARY")
    print("=" * 60)
    print(f"  Date: {summary['date']}")
    print(f"  Sessions: {summary['sessions_count']}")
    print(f"  Active time: {summary['total_active_time']/60:.1f} minutes ({summary['total_active_time']/3600:.2f} hours)")
    print(f"  Idle time: {summary['total_idle_time']/60:.1f} minutes")
    
    if summary['top_applications']:
        print("\n  Top Applications:")
        for i, app in enumerate(summary['top_applications'][:10], 1):
            mins = app['total_time'] / 60
            print(f"    {i:2}. {app['app_name']:<30} {mins:6.1f} min")
    
    if summary['top_domains']:
        print("\n  Top Domains:")
        for i, domain in enumerate(summary['top_domains'][:10], 1):
            mins = domain['total_time'] / 60
            print(f"    {i:2}. {domain['domain']:<30} {mins:6.1f} min")
    
    print("=" * 60 + "\n")


def print_usage_statistics(days: int = 7, log_dir: str = None):
    """Print usage statistics for the last N days."""
    from datetime import datetime, timedelta
    import sqlite3
    
    logger = EnhancedActivityLogger(log_dir=log_dir)
    db_path = logger.database.db_path
    
    print("\n" + "=" * 60)
    print(f"  USAGE STATISTICS - Last {days} Days")
    print("=" * 60)
    
    # Query database directly for multi-day stats
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Overall stats
        cursor.execute('''
            SELECT 
                COUNT(*) as sessions_count,
                SUM(active_duration) as total_active_time,
                SUM(total_duration - active_duration) as total_idle_time,
                COUNT(DISTINCT DATE(start_time)) as days_with_data
            FROM usage_sessions 
            WHERE DATE(start_time) >= ?
        ''', (cutoff_date,))
        
        stats = cursor.fetchone()
        
        total_active = stats['total_active_time'] or 0
        total_idle = stats['total_idle_time'] or 0
        sessions = stats['sessions_count'] or 0
        days_with_data = stats['days_with_data'] or 1
        
        print(f"  Period: Last {days} days ({days_with_data} days with data)")
        print(f"  Total sessions: {sessions}")
        print(f"  Total active time: {total_active/3600:.2f} hours")
        print(f"  Average daily active: {(total_active/days_with_data)/3600:.2f} hours")
        
        # Top apps
        cursor.execute('''
            SELECT app_name, SUM(active_duration) as total_time
            FROM usage_sessions 
            WHERE DATE(start_time) >= ?
            GROUP BY app_name
            ORDER BY total_time DESC
            LIMIT 10
        ''', (cutoff_date,))
        
        top_apps = cursor.fetchall()
        
        if top_apps:
            print("\n  Top Applications:")
            for i, app in enumerate(top_apps, 1):
                hours = app['total_time'] / 3600
                print(f"    {i:2}. {app['app_name']:<30} {hours:6.2f} hrs")
        
        # Top domains
        cursor.execute('''
            SELECT domain, SUM(active_duration) as total_time
            FROM usage_sessions 
            WHERE DATE(start_time) >= ? AND domain IS NOT NULL
            GROUP BY domain
            ORDER BY total_time DESC
            LIMIT 10
        ''', (cutoff_date,))
        
        top_domains = cursor.fetchall()
        
        if top_domains:
            print("\n  Top Domains:")
            for i, domain in enumerate(top_domains, 1):
                hours = domain['total_time'] / 3600
                print(f"    {i:2}. {domain['domain']:<30} {hours:6.2f} hrs")
        
        # Daily breakdown
        cursor.execute('''
            SELECT 
                DATE(start_time) as date,
                SUM(active_duration) as active_time,
                COUNT(*) as sessions
            FROM usage_sessions 
            WHERE DATE(start_time) >= ?
            GROUP BY DATE(start_time)
            ORDER BY date DESC
        ''', (cutoff_date,))
        
        daily_data = cursor.fetchall()
        
        if daily_data:
            print("\n  Daily Breakdown:")
            print("    Date         Active Time    Sessions")
            print("    " + "-" * 40)
            for day in daily_data:
                hours = day['active_time'] / 3600
                print(f"    {day['date']}   {hours:6.2f} hrs      {day['sessions']:3}")
    
    print("=" * 60 + "\n")


def main():
    """Main entry point for the activity monitor."""
    parser = argparse.ArgumentParser(
        description="Focus Guard Activity Monitor - Track application usage with idle detection"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=5,
        help="Sampling interval in seconds (default: 5)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output (show all samples, not just window changes)"
    )
    parser.add_argument(
        "--log-dir", "-l",
        type=str,
        default=None,
        help="Custom log directory (default: %%LOCALAPPDATA%%/FocusGuard)"
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Show daily usage summary and exit"
    )
    parser.add_argument(
        "--date", "-d",
        type=str,
        default=None,
        help="Date for summary report (YYYY-MM-DD format, default: today)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show usage statistics for multiple days and exit"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days for statistics (default: 7)"
    )
    
    args = parser.parse_args()
    
    # Handle summary/stats modes (no monitoring, just report)
    if args.summary:
        print_daily_summary(args.date, args.log_dir)
        return
    
    if args.stats:
        print_usage_statistics(args.days, args.log_dir)
        return
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Path(args.log_dir or ".") / "activity_monitor.log" if args.log_dir else "activity_monitor.log"),
        ]
    )
    
    # Suppress verbose library logs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Create and start the monitor
    runner = ActivityMonitorRunner(
        interval_seconds=args.interval,
        verbose=args.verbose,
        log_dir=args.log_dir
    )
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print("\n\nShutting down...")
        runner.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start monitoring
    runner.start()
    
    # Keep running until interrupted
    try:
        while runner.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        runner.stop()


if __name__ == "__main__":
    main()
