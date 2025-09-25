# Activity Monitoring Module

The Activity Monitoring module provides comprehensive tracking of user activity, idle detection, and usage statistics. It's a core component of Focus Guard that helps understand and manage user productivity.

## Core Components

### 1. IdleDetector

Detects user inactivity across different idle states (short, medium, long).

```python
from focus_guard.core.activity.idle_detector import IdleDetector, IdleConfiguration

# Configure idle thresholds (in seconds)
idle_config = IdleConfiguration(
    short_idle_threshold=30,    # 30 seconds
    medium_idle_threshold=300,  # 5 minutes
    long_idle_threshold=1800    # 30 minutes
)

detector = IdleDetector(idle_config)

# Start monitoring
detector.start_monitoring()

# Check current state
print(f"Current idle state: {detector.get_current_state().name}")
print(f"Idle time: {detector.get_idle_time_seconds():.1f} seconds")

# Add callback for state changes
def on_idle_change(event):
    print(f"Idle state changed: {event.previous_state.name} -> {event.current_state.name}")

detector.add_state_change_callback(on_idle_change)

# Stop monitoring when done
detector.stop_monitoring()
```

### 2. UsageTracker

Tracks user activity sessions and provides usage statistics.

```python
from focus_guard.core.activity.usage_tracker import UsageTracker

# Create a tracker with an idle detector
tracker = UsageTracker(idle_detector=detector, session_timeout=300)  # 5-minute session timeout

# Start tracking
tracker.start_tracking()

# Get current session info
current_session = tracker.get_current_session_info()
print(f"Current app: {current_session['app_name']}")
print(f"Active time: {current_session['active_duration']:.1f} seconds")

# Get daily summary
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
daily_summary = tracker.get_daily_summary(today)
print(f"Total active time today: {daily_summary.total_active_time / 3600:.1f} hours")

# Add callback for session completion
def on_session_complete(session):
    print(f"Session completed: {session.app_name} - {session.active_duration:.1f}s active")

tracker.add_session_callback(on_session_complete)

# Stop tracking when done
tracker.stop_tracking()
```

### 3. EnhancedActivityMonitor

Combines idle detection, activity tracking, and usage statistics in one interface.

```python
from focus_guard.core.activity.enhanced_monitor import EnhancedActivityMonitor

# Create monitor with default settings
monitor = EnhancedActivityMonitor(
    idle_config=idle_config,
    session_timeout=300,      # 5 minutes
    polling_interval=1.0      # Check activity every second
)

# Add callbacks
def on_activity(window_info):
    print(f"Activity detected: {window_info.app_name} - {window_info.window_title}")

def on_idle(event):
    print(f"Idle state changed to {event.current_state.name}")

monitor.add_activity_callback(on_activity)
monitor.add_idle_callback(on_idle)

# Start monitoring
monitor.start_monitoring()

# Get usage statistics
stats = monitor.get_usage_statistics(days=7)
print(f"Weekly stats: {stats['total_active_time']/3600:.1f} hours active")

# Stop monitoring when done
monitor.stop_monitoring()
```

## Performance Considerations

1. **Polling Interval**: 
   - Lower values (e.g., 1.0s) provide more accurate tracking but use more CPU
   - Higher values (e.g., 5.0s) reduce CPU usage but may miss short activities

2. **Memory Usage**:
   - The module maintains a history of recent sessions and events
   - Old sessions are automatically cleaned up after 30 days by default
   - Use `reset_statistics()` to clear all tracking data

3. **Thread Safety**:
   - All public methods are thread-safe
   - Callbacks are executed in the monitoring thread

## Best Practices

1. Always call `stop_monitoring()` when done to clean up resources
2. Use appropriate idle thresholds based on your use case
3. Handle exceptions in callbacks to prevent monitoring from stopping
4. Use the `get_comprehensive_status()` method for debugging

## Integration with Other Components

The Activity Monitoring module works seamlessly with other Focus Guard components:

- **Blocking System**: Trigger blocks based on activity patterns
- **Analytics**: Provide detailed usage statistics
- **Notifications**: Alert users about their activity patterns

For more advanced usage, refer to the API documentation for each class.
