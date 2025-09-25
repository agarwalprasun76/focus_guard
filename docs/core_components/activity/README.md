# Activity Monitoring

The Activity Monitoring module provides comprehensive tracking of user activity, idle detection, and usage statistics.

## Features

- **Cross-platform idle detection** with configurable thresholds
- **Application usage tracking** with session management
- **Real-time activity monitoring** with event callbacks
- **Detailed usage statistics** and analytics
- **Thread-safe implementation** for reliable operation

## Quick Start

```python
from focus_guard.core.activity.enhanced_monitor import EnhancedActivityMonitor
from focus_guard.core.activity.idle_detector import IdleConfiguration

# Configure idle detection
idle_config = IdleConfiguration(
    short_idle_threshold=30,    # 30 seconds
    medium_idle_threshold=300,  # 5 minutes
    long_idle_threshold=1800    # 30 minutes
)

# Create monitor
monitor = EnhancedActivityMonitor(
    idle_config=idle_config,
    session_timeout=300,      # 5 minutes
    polling_interval=1.0      # Check activity every second
)

# Add callbacks
def on_activity(window_info):
    print(f"Activity: {window_info.app_name} - {window_info.window_title}")

monitor.add_activity_callback(on_activity)

# Start monitoring
monitor.start_monitoring()

# Get usage statistics
stats = monitor.get_usage_statistics(days=7)
print(f"Weekly active time: {stats['total_active_time']/3600:.1f} hours")

# Stop when done
monitor.stop_monitoring()
```

## Documentation

- [Activity Monitoring Guide](./activity_monitoring.md) - Comprehensive guide to all features
- [API Reference](./api/activity.md) - Detailed API documentation
- [Examples](../examples/activity_monitoring_quickstart.py) - Practical usage examples

## Performance

The module is optimized for performance with:
- Efficient event handling
- Minimal CPU usage during idle periods
- Configurable polling intervals
- Automatic cleanup of old data

## Integration

Easily integrate with other Focus Guard components:
- Blocking System - Trigger actions based on activity patterns
- Analytics - Generate detailed usage reports
- Notifications - Alert users about their activity

## Testing

Run the test suite with:
```bash
pytest focus_guard/tests/core/activity/
```

## License

This module is part of the Focus Guard project and is licensed under the MIT License.
