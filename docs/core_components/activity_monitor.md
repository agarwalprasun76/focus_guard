# Activity Monitoring Module

The Activity Monitoring module is a core component of Focus Guard that provides comprehensive tracking of user activity, idle detection, and usage statistics across different applications and windows.

## Features

- **Cross-Platform Support**: Works on Windows, Linux (X11), and macOS
- **Idle Detection**: Configurable idle states with customizable thresholds
- **Active Window Monitoring**: Tracks currently focused applications and window titles
- **Usage Statistics**: Detailed tracking of application usage and active time
- **Real-time Event System**: Callback-based notifications for activity changes
- **Session Management**: Automatic session tracking with configurable timeouts
- **Performance Optimized**: Low CPU usage with efficient polling mechanisms

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
current_session = tracker.get_current_session()
print(f"Current session active time: {current_session.active_seconds:.1f}s")

# Get daily statistics
daily_stats = tracker.get_daily_statistics()
print(f"Today's active time: {daily_stats.total_active_time/3600:.1f} hours")
```

### 3. EnhancedActivityMonitor

Combines idle detection, usage tracking, and window monitoring into a single interface.

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
    print(f"Activity: {window_info.app_name} - {window_info.window_title}")
    
def on_idle_state_change(event):
    print(f"Idle state: {event.current_state.name} for {event.idle_seconds:.1f}s")

monitor.add_activity_callback(on_activity)
monitor.add_idle_state_callback(on_idle_state_change)

# Start monitoring
monitor.start_monitoring()

# Get usage statistics
stats = monitor.get_usage_statistics(days=7)
print(f"Weekly active time: {stats['total_active_time']/3600:.1f} hours")

# Stop when done
monitor.stop_monitoring()
```

## Platform Support

### Windows
- Uses `win32gui` for window management
- Leverages `psutil` for process information
- Implements efficient polling with `ctypes`

### Linux (X11)
- Uses `xprop` for active window detection
- Utilizes `wmctrl` for window management
- Implements X11-specific event handling

### macOS
- Uses native Quartz APIs
- Implements AppKit integration
- Supports multiple displays and spaces

## Integration

The Activity Monitoring module integrates with other Focus Guard components:

- **Blocking System**: Trigger actions based on activity patterns
- **Analytics**: Generate detailed usage reports and insights
- **Notifications**: Alert users about their activity patterns
- **Browser Integration**: Correlate desktop activity with web browsing

## Performance Considerations

- **Efficient Polling**: Configurable polling intervals balance responsiveness and resource usage
- **Event-based Architecture**: Minimizes CPU usage during idle periods
- **Background Processing**: Heavy operations run in separate threads
- **Memory Management**: Automatic cleanup of old data and sessions

## Testing

Run the test suite with:

```bash
pytest focus_guard/tests/core/activity/
```

## License

This module is part of the Focus Guard project and is licensed under the MIT License.
