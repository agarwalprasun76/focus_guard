"""
Focus Guard - Activity Monitoring Quick Start

This example demonstrates how to use the Focus Guard activity monitoring features
to track user activity, detect idle time, and collect usage statistics.
"""
import time
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Demonstrate basic usage of the activity monitoring features."""
    from focus_guard.core.activity.idle_detector import IdleConfiguration
    from focus_guard.core.activity.enhanced_monitor import EnhancedActivityMonitor
    
    print("Focus Guard - Activity Monitoring Quick Start\n" + "="*50)
    
    # Configure idle detection thresholds (in seconds)
    idle_config = IdleConfiguration(
        short_idle_threshold=30,    # 30 seconds
        medium_idle_threshold=300,  # 5 minutes
        long_idle_threshold=1800    # 30 minutes
    )
    
    # Create the activity monitor
    monitor = EnhancedActivityMonitor(
        idle_config=idle_config,
        session_timeout=300,      # 5 minutes of inactivity ends a session
        polling_interval=1.0      # Check activity every second
    )
    
    # Define callbacks
    def on_activity(window_info):
        print(f"\nActivity detected: {window_info.app_name} - {window_info.window_title}")
    
    def on_idle(event):
        print(f"\nIdle state changed: {event.previous_state.name} → {event.current_state.name}")
    
    def on_session_complete(session):
        print(f"\nSession completed: {session.app_name} - "
              f"Active: {session.active_duration:.1f}s, "
              f"Total: {session.total_duration:.1f}s")
    
    # Register callbacks
    monitor.add_activity_callback(on_activity)
    monitor.add_idle_callback(on_idle)
    monitor.add_session_callback(on_session_complete)
    
    # Start monitoring
    print("\nStarting activity monitoring... (press Ctrl+C to stop)")
    monitor.start_monitoring()
    
    try:
        # Run for 5 minutes, printing status every 30 seconds
        for i in range(10):
            time.sleep(30)
            
            # Get current status
            idle_time = monitor.get_idle_time_seconds()
            current_session = monitor.get_current_usage_session()
            
            print("\n" + "-"*50)
            print(f"Status after {(i+1)*30} seconds:")
            print(f"Current idle time: {idle_time:.1f} seconds")
            print(f"Current state: {monitor.get_idle_state().name}")
            
            if current_session:
                print(f"Current app: {current_session['app_name']}")
                print(f"Active time: {current_session['active_duration']:.1f} seconds")
            
            # Print daily summary
            today = datetime.now().strftime("%Y-%m-%d")
            daily = monitor.get_daily_summary(today)
            if daily:
                print(f"\nToday's usage:")
                print(f"- Active time: {daily.total_active_time/60:.1f} minutes")
                print(f"- Sessions: {daily.session_count}")
                print(f"- Active apps: {', '.join(k for k in daily.app_usage.keys())}")
            
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
    finally:
        # Always stop monitoring to clean up resources
        monitor.stop_monitoring()
        
        # Print final statistics
        stats = monitor.get_usage_statistics(days=1)
        print("\n" + "="*50)
        print("Final Statistics:")
        print(f"Total active time: {stats['total_active_time']/60:.1f} minutes")
        print(f"Total sessions: {stats['total_sessions']}")
        print(f"Most used apps: {', '.join(f'{k} ({v/60:.1f} min)' for k, v in stats['app_usage'].items())}")

if __name__ == "__main__":
    main()
