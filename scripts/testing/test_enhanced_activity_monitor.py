#!/usr/bin/env python3
"""
Test script for the Enhanced Activity Monitor.

This script demonstrates the complete enhanced activity monitoring system with:
- Integrated idle detection and usage tracking
- Real-time activity monitoring
- Session management with idle filtering
- Comprehensive statistics and reporting
"""

import time
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the focus_guard module to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from focus_guard.core.activity.enhanced_monitor import EnhancedActivityMonitor
from focus_guard.core.activity.idle_detector import IdleConfiguration, IdleEvent
from focus_guard.core.activity.usage_tracker import UsageSession
from focus_guard.core.activity.models import WindowInfo


class EnhancedMonitorDemo:
    """Demonstration of the enhanced activity monitoring system."""
    
    def __init__(self):
        # Configure for demo with shorter thresholds
        config = IdleConfiguration(
            short_idle_threshold=5.0,   # 5 seconds for demo
            medium_idle_threshold=15.0, # 15 seconds
            long_idle_threshold=30.0,   # 30 seconds
            polling_interval=1.0        # Check every second
        )
        
        self.monitor = EnhancedActivityMonitor(
            idle_config=config,
            session_timeout=10.0,  # 10 second session timeout for demo
            polling_interval=2.0   # Check activity every 2 seconds
        )
        
        # Add callbacks for demonstration
        self.monitor.add_activity_callback(self._on_activity)
        self.monitor.add_idle_callback(self._on_idle_change)
        self.monitor.add_session_callback(self._on_session_complete)
        
        self.activity_count = 0
        self.session_count = 0
    
    def _on_activity(self, window_info: WindowInfo):
        """Handle activity events."""
        self.activity_count += 1
        if self.activity_count % 5 == 0:  # Print every 5th activity
            print(f"[ACTIVITY #{self.activity_count}] {window_info.app_name}")
            if window_info.domain:
                print(f"             Domain: {window_info.domain}")
    
    def _on_idle_change(self, event: IdleEvent):
        """Handle idle state changes."""
        print(f"[IDLE] {event.previous_state.value} -> {event.current_state.value} "
              f"(idle: {event.idle_duration:.1f}s)")
    
    def _on_session_complete(self, session: UsageSession):
        """Handle completed sessions."""
        self.session_count += 1
        print(f"[SESSION #{self.session_count}] {session.app_name}: "
              f"{session.active_duration:.1f}s active / {session.total_duration:.1f}s total")
        if session.domain:
            print(f"                     Domain: {session.domain}")
    
    def run_quick_test(self):
        """Run a quick functionality test."""
        print("=== Enhanced Activity Monitor Quick Test ===\n")
        
        # Test basic functionality
        print("1. Testing idle detection...")
        idle_time = self.monitor.get_idle_time_seconds()
        idle_state = self.monitor.get_idle_state()
        is_active = self.monitor.is_user_active()
        
        print(f"   Current idle time: {idle_time:.1f}s")
        print(f"   Current idle state: {idle_state.value}")
        print(f"   User is active: {is_active}")
        
        # Test monitoring start/stop
        print("\n2. Testing monitoring lifecycle...")
        self.monitor.start_monitoring()
        print("   Monitoring started")
        
        time.sleep(3)  # Let it run for a few seconds
        
        status = self.monitor.get_comprehensive_status()
        print(f"   Activity events: {status['monitoring']['activity_events_count']}")
        print(f"   Monitoring active: {status['monitoring']['monitoring_active']}")
        
        self.monitor.stop_monitoring()
        print("   Monitoring stopped")
        
        # Test statistics
        print("\n3. Testing statistics...")
        idle_stats = self.monitor.get_idle_statistics()
        monitoring_stats = self.monitor.get_monitoring_statistics()
        
        print(f"   Total active time: {idle_stats['total_active_time']:.1f}s")
        print(f"   Total monitoring time: {monitoring_stats['total_monitoring_time']:.1f}s")
        print(f"   Activity events: {monitoring_stats['activity_events_count']}")
        
        print("\n[SUCCESS] Quick test completed successfully!")
    
    def run_interactive_demo(self):
        """Run an interactive demonstration."""
        print("=== Enhanced Activity Monitor Interactive Demo ===")
        print("This demo shows real-time activity monitoring with idle detection.")
        print("Try switching applications or going idle to see the system in action.")
        print("Press Ctrl+C to stop and see final results.\n")
        
        self.monitor.start_monitoring()
        print("Enhanced monitoring started...\n")
        
        try:
            # Run for demonstration
            start_time = datetime.now()
            last_status_time = start_time
            
            while True:
                current_time = datetime.now()
                
                # Print status every 10 seconds
                if (current_time - last_status_time).total_seconds() >= 10:
                    self._print_status_update()
                    last_status_time = current_time
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\nDemo interrupted by user.")
        finally:
            self._stop_and_show_results()
    
    def _print_status_update(self):
        """Print a status update."""
        print("\n" + "="*50)
        print(f"Status Update - {datetime.now().strftime('%H:%M:%S')}")
        print("="*50)
        
        status = self.monitor.get_comprehensive_status()
        
        # Current state
        print(f"Idle State: {self.monitor.get_idle_state().value}")
        print(f"Idle Time: {self.monitor.get_idle_time_seconds():.1f}s")
        print(f"User Active: {self.monitor.is_user_active()}")
        
        # Current session
        current_session = status['current_session']
        if current_session:
            print(f"Current App: {current_session['app_name']}")
            print(f"Session Duration: {current_session['current_duration']:.1f}s")
            if current_session.get('domain'):
                print(f"Domain: {current_session['domain']}")
        else:
            print("No active session")
        
        # Statistics
        monitoring = status['monitoring']
        print(f"Activity Events: {monitoring['activity_events_count']}")
        print(f"Events/Hour: {monitoring['events_per_hour']:.1f}")
        
        usage = status['usage_stats']
        print(f"Total Active Time Today: {usage['total_active_time']:.1f}s")
        print(f"Sessions Today: {usage['total_sessions']}")
        
        if usage['top_applications']:
            top_app = list(usage['top_applications'].items())[0]
            print(f"Top App: {top_app[0]} ({top_app[1]:.1f}s)")
    
    def _stop_and_show_results(self):
        """Stop monitoring and show final results."""
        print("\n" + "="*60)
        print("FINAL RESULTS")
        print("="*60)
        
        self.monitor.stop_monitoring()
        
        # Get comprehensive final status
        status = self.monitor.get_comprehensive_status()
        
        print(f"\nMONITORING SUMMARY:")
        monitoring = status['monitoring']
        for key, value in monitoring.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
        
        print(f"\nIDLE DETECTION SUMMARY:")
        idle = status['idle_detection']
        print(f"  Current State: {idle['current_state']}")
        print(f"  Total Active Time: {idle['total_active_time']:.1f}s")
        print(f"  Total Idle Time: {idle['total_idle_time']:.1f}s")
        print(f"  Active Percentage: {idle['active_percentage']:.1f}%")
        print(f"  Idle Periods: {idle['idle_periods_count']}")
        
        print(f"\nUSAGE SUMMARY:")
        usage = status['usage_stats']
        print(f"  Total Active Time: {usage['total_active_time']:.1f}s")
        print(f"  Total Sessions: {usage['total_sessions']}")
        print(f"  Average Session Duration: {usage['total_active_time'] / max(1, usage['total_sessions']):.1f}s")
        
        if usage['top_applications']:
            print(f"  Top Applications:")
            for app, time_spent in list(usage['top_applications'].items())[:5]:
                print(f"    {app}: {time_spent:.1f}s")
        
        if usage['top_domains']:
            print(f"  Top Domains:")
            for domain, time_spent in list(usage['top_domains'].items())[:3]:
                print(f"    {domain}: {time_spent:.1f}s")
        
        print(f"\nRECENT ACTIVITY:")
        print(f"  Recent Sessions: {status['recent_sessions_count']}")
        print(f"  Recent Idle Periods: {status['recent_idle_periods_count']}")
        
        # Show recent sessions
        recent_sessions = self.monitor.get_recent_sessions(hours=1)
        if recent_sessions:
            print(f"\nLAST 5 SESSIONS:")
            for i, session in enumerate(recent_sessions[-5:], 1):
                print(f"  {i}. {session.app_name}: {session.active_duration:.1f}s active")
                if session.domain:
                    print(f"     Domain: {session.domain}")
        
        # Show recent idle periods
        recent_idle = self.monitor.get_recent_idle_periods(hours=1)
        if recent_idle:
            print(f"\nLAST 3 IDLE PERIODS:")
            for i, period in enumerate(recent_idle[-3:], 1):
                print(f"  {i}. {period['duration']:.1f}s ({period['max_state']})")
        
        print(f"\nCallback Statistics:")
        print(f"  Activity events processed: {self.activity_count}")
        print(f"  Sessions completed: {self.session_count}")


def main():
    """Main function to run the enhanced activity monitor demo."""
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick test mode
        demo = EnhancedMonitorDemo()
        demo.run_quick_test()
    else:
        # Interactive demo mode
        demo = EnhancedMonitorDemo()
        demo.run_interactive_demo()


if __name__ == "__main__":
    main()
