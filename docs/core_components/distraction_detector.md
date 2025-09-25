# distraction_detector.py

This module detects user distractions by monitoring active application usage and comparing it to an allowed list for the current focus/task context.

## Key Features
- Real-time distraction detection by comparing current activity to allowed apps/processes
- Fuzzy matching and user override support
- Tracks time spent in each app/process
- Configurable alert thresholds (per app or global)
- Triggers alerts and logs distraction events
- Supports user learning/personalization (mark apps as distractions or allowed)
- Provides logging and reporting hooks
- Extensible for future features and reporting

## Core Methods
- `is_distracted(window_info)`: Checks if the current window is a distraction
- `update_activity(window_info)`: Updates activity state, tracks time, triggers alerts
- `trigger_alert(window_info)`: Triggers alerts when thresholds are exceeded
- `log_event(window_info)`: Logs activity/distraction events
- `mark_as_allowed(app_name)`: User marks app as NOT a distraction
- `mark_as_distraction(app_name)`: User marks app as a distraction
- `get_distraction_summary()`: Returns a summary of all detected distractions
- `configure(config)`: Updates configuration at runtime

## Integration Points
- Receives activity data from the activity monitor (see `core/activity_monitor.py`)
- Can call alert/notification systems via callback
- Reports and logs can be integrated with reporting modules

## Usage
See the module docstrings and the project plan for configuration and integration details.

---

## Flow Diagram

See `distraction_detector_flow.md` for a detailed mermaid flow diagram of the module's logic.
