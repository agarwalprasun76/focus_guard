#!/usr/bin/env python3
"""
Test script for idle detection and usage tracking integration.

This script demonstrates the enhanced activity monitoring system with:
- Real-time idle detection
- Active usage tracking with idle filtering
- Usage session management
- Daily usage summaries
"""

import time
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add the focus_guard module to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from focus_guard.core.activity.idle_detector import IdleDetector, IdleConfiguration, IdleEvent
from focus_guard.core.activity.usage_tracker import UsageTracker, UsageSession
from focus_guard.core.activity.models import WindowInfo
from focus_guard.core.domain.domain_utils_new import create_url_from_string


class ActivityMonitorDemo:
    """Demonstration of the enhanced activity monitoring system."""
    
    def __init__(self):
        # Configure idle detection with shorter thresholds for demo
        config = IdleConfiguration(
            short_idle_threshold=10.0,  # 10 seconds for demo
            medium_idle_threshold=30.0,  # 30 seconds
            long_idle_threshold=60.0,   # 1 minute
            polling_interval=2.0        # Check every 2 seconds
        )
        
        self.idle_detector = IdleDetector(config)
        self.usage_tracker = UsageTracker(self.idle_detector, session_timeout=15.0)
        
        # Add callbacks for demonstration
        self.idle_detector.add_state_change_callback(self._on_idle_state_change)
        self.usage_tracker.add_session_callback(self._on_session_complete)
        
        self.demo_running = False
    
    def _on_idle_state_change(self, event: IdleEvent):
        """Handle idle state changes for demonstration."""
        print(f"\n[IDLE] State changed: {event.previous_state.value} -> {event.current_state.value}")
        print(f"       Idle time: {event.idle_duration:.1f}s, Active duration: {event.active_duration:.1f}s")
    
    def _on_session_complete(self, session: UsageSession):
        """Handle completed sessions for demonstration."""
        print(f"\n[SESSION] Completed: {session.app_name}")
        print(f"          Duration: {session.total_duration:.1f}s total, {session.active_duration:.1f}s active")
        print(f"          Idle periods: {len(session.idle_periods)}")
        if session.domain:
            print(f"          Domain: {session.domain}")
    
    def start_demo(self):
        """Start the activity monitoring demonstration."""
        print("=== Focus Guard Activity Monitoring Demo ===")
        print("This demo shows idle detection and usage tracking in real-time.")
        print("Try switching between applications or going idle to see the system in action.\n")
        
        # Start monitoring systems
        self.idle_detector.start_monitoring()
        self.usage_tracker.start_tracking()
        self.demo_running = True
        
        print("Monitoring started. Press Ctrl+C to stop and see results.\n")
        
        try:
            # Simulate some activity tracking
            self._simulate_activity()
            
            # Keep running until interrupted
            while self.demo_running:
                self._print_status()
                time.sleep(5.0)
                
        except KeyboardInterrupt:
            print("\n\nDemo interrupted by user.")
        finally:
            self._stop_demo()
    
    def _simulate_activity(self):
        """Simulate some application activity for demonstration."""
        print("[DEMO] Simulating application activity...\n")
        
        # Simulate Chrome browsing
        chrome_window = WindowInfo(
            app_name="chrome.exe",
            window_title="Focus Guard - Google Chrome",
            pid="1234",
            url=create_url_from_string("https://github.com/focus-guard/focus-guard"),
            domain=create_url_from_string("https://github.com").domain
        )
        self.usage_tracker.track_activity(chrome_window)
        
        time.sleep(2)
        
        # Simulate VS Code
        vscode_window = WindowInfo(
            app_name="Code.exe",
            window_title="activity_monitor.py - Visual Studio Code",
            pid="5678"
        )
        self.usage_tracker.track_activity(vscode_window)
        
        time.sleep(2)
        
        # Back to Chrome with different domain
        youtube_window = WindowInfo(
            app_name="chrome.exe",
            window_title="Python Tutorial - YouTube",
            pid="1234",
            url=create_url_from_string("https://www.youtube.com/watch?v=example"),
            domain=create_url_from_string("https://www.youtube.com").domain
        )
        self.usage_tracker.track_activity(youtube_window)
    
    def _print_status(self):
        """Print current status of the monitoring systems."""
        print("\n" + "="*60)
        print(f"Status Update - {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        # Idle detector statistics
        idle_stats = self.idle_detector.get_statistics()
        print(f"Idle Detection:")
        print(f"  Current State: {idle_stats['current_state']}")
        print(f"  Current Idle Time: {idle_stats['current_idle_time']:.1f}s")
        print(f"  Total Active Time: {idle_stats['total_active_time']:.1f}s")
        print(f"  Total Idle Time: {idle_stats['total_idle_time']:.1f}s")
        print(f"  Active Percentage: {idle_stats['active_percentage']:.1f}%")
        print(f"  Idle Periods: {idle_stats['idle_periods_count']}")
        
        # Current session info
        current_session = self.usage_tracker.get_current_session_info()
        if current_session:
            print(f"\nCurrent Session:")
            print(f"  App: {current_session['app_name']}")
            print(f"  Duration: {current_session['current_duration']:.1f}s")
            if current_session['domain']:
                print(f"  Domain: {current_session['domain']}")
            print(f"  Idle Periods: {current_session['idle_periods_count']}")
        else:
            print(f"\nNo active session")
        
        # Usage statistics
        usage_stats = self.usage_tracker.get_usage_statistics(days=1)
        print(f"\nUsage Statistics (Today):")
        print(f"  Total Active Time: {usage_stats['total_active_time']:.1f}s")
        print(f"  Total Sessions: {usage_stats['total_sessions']}")
        print(f"  Sessions per Day: {usage_stats['sessions_per_day']:.1f}")
        
        if usage_stats['top_applications']:
            print(f"  Top Applications:")
            for app, time_spent in list(usage_stats['top_applications'].items())[:3]:
                print(f"    {app}: {time_spent:.1f}s")
        
        if usage_stats['top_domains']:
            print(f"  Top Domains:")
            for domain, time_spent in list(usage_stats['top_domains'].items())[:3]:
                print(f"    {domain}: {time_spent:.1f}s")
    
    def _stop_demo(self):
        """Stop the demonstration and show final results."""
        print("\n" + "="*60)
        print("STOPPING DEMO - FINAL RESULTS")
        print("="*60)
        
        # Stop monitoring
        self.usage_tracker.stop_tracking()
        self.idle_detector.stop_monitoring()
        self.demo_running = False
        
        # Show final statistics
        self._print_final_results()
    
    def _print_final_results(self):
        """Print comprehensive final results."""
        print("\nFINAL IDLE DETECTION STATISTICS:")
        idle_stats = self.idle_detector.get_statistics()
        for key, value in idle_stats.items():
            print(f"  {key}: {value}")
        
        print(f"\nRECENT IDLE PERIODS:")
        recent_periods = self.idle_detector.get_recent_idle_periods(hours=1)
        for i, period in enumerate(recent_periods[-5:], 1):  # Show last 5
            duration = period['duration']
            print(f"  {i}. {duration:.1f}s idle ({period['max_state']})")
        
        print(f"\nCOMPLETED SESSIONS:")
        recent_sessions = self.usage_tracker.get_recent_sessions(hours=1)
        for i, session in enumerate(recent_sessions, 1):
            print(f"  {i}. {session.app_name}: {session.active_duration:.1f}s active "
                  f"({session.total_duration:.1f}s total)")
            if session.domain:
                print(f"      Domain: {session.domain}")
        
        print(f"\nDAILY SUMMARY:")
        today = datetime.now().strftime('%Y-%m-%d')
        daily_summary = self.usage_tracker.get_daily_summary(today)
        if daily_summary:
            summary_dict = daily_summary.to_dict()
            print(f"  Date: {summary_dict['date']}")
            print(f"  Total Active Time: {summary_dict['total_active_time']:.1f}s")
            print(f"  Sessions: {summary_dict['sessions_count']}")
            print(f"  Applications: {len(summary_dict['applications'])}")
            print(f"  Domains: {len(summary_dict['domains'])}")
        else:
            print("  No daily summary available")


def main():
    """Main function to run the activity monitoring demo."""
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick test mode
        print("Running quick integration test...")
        demo = ActivityMonitorDemo()
        
        # Test idle detection
        print(f"Platform detector: {demo.idle_detector.platform_detector.__class__.__name__}")
        print(f"Current idle time: {demo.idle_detector.get_idle_time_seconds():.1f}s")
        print(f"Is idle: {demo.idle_detector.is_idle()}")
        print(f"Is active: {demo.idle_detector.is_active()}")
        
        # Test usage tracking
        demo.usage_tracker.start_tracking()
        demo._simulate_activity()
        time.sleep(1)
        demo.usage_tracker.stop_tracking()
        
        print("Quick test completed successfully!")
        return
    
    # Full interactive demo
    demo = ActivityMonitorDemo()
    demo.start_demo()


if __name__ == "__main__":
    main()
