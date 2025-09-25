# Alert System Module

## Overview
The Alert System module is responsible for notifying users when distractions are detected during focus sessions. It provides multiple notification methods with different severity levels and implements an escalation strategy for persistent distractions.

## Architecture

### Core Components

1. **AlertProvider (Base Class)**
   - Abstract base class for all alert providers
   - Defines the common interface for sending alerts
   - Located in `core/alert_system/alert_provider.py`

2. **AlertSystem**
   - Main controller that manages multiple alert providers
   - Implements alert history tracking and escalation logic
   - Handles cooldown periods between alerts
   - Located in `core/alert_system/alert_system.py`

3. **Concrete Alert Providers**
   - **PopupAlertProvider**: Shows visual popup alerts using platform-specific methods
   - **SoundAlertProvider**: Plays sound alerts with configurable volume and repetition
   - **DesktopNotificationProvider**: Uses native OS notification systems
   - **WebhookAlertProvider**: Sends alerts to configurable webhook endpoints
   - **EmailAlertProvider**: Sends email notifications for alerts
   - **AppBlockerProvider**: Can temporarily block distracting applications

## Features

### Alert Levels
The system supports three severity levels:
- **Normal**: First-level alerts for initial distractions
- **Warning**: Escalated alerts for repeated distractions
- **Critical**: Highest severity for persistent distractions

### Escalation Strategy
- Alerts escalate in severity based on frequency and recency
- Configurable thresholds determine when to escalate
- Each escalation level can trigger different alert types

### Cross-Platform Support
- Windows: PowerShell-based notifications and sound alerts
- macOS: AppleScript notifications and sound playback
- Linux: Native notification systems and sound playback

### Persistence
- Alert history is tracked and can be saved/loaded
- Enables intelligent escalation based on past behavior

## Configuration Options

The alert system is highly configurable:

```python
config = {
    "cooldown_period": 60,  # seconds between alerts for the same app
    "escalation_threshold": 3,  # alerts before escalation
    "escalation_window": 300,  # time window for escalation (seconds)
    
    # Provider-specific configurations
    "popup_alert": {
        "popup_duration": 10  # seconds
    },
    "sound_alert": {
        "volume": 0.8,
        "repeat_count": 2,
        "repeat_interval": 0.5
    }
}
```

## Usage Example

```python
from core.alert_system.alert_system import AlertSystem

# Create alert system with default providers
alert_system = AlertSystem()

# Send an alert when distraction is detected
window_info = {
    "app_name": "DistractingApp.exe",
    "window_title": "Social Media",
    "pid": "12345",
    "timestamp": "2025-07-03T12:45:00"
}

alert_system.alert(window_info, "You're getting distracted!")
```

## Testing

The alert system includes several test scripts:
- `test_alert_levels.py`: Tests different alert severity levels
- `test_enhanced_alerts.py`: Tests the escalation mechanism
- `test_popup_alert.py`: Tests popup alerts in isolation
- `test_native_popup.py`: Tests platform-native notifications
- `simple_popup_test.py`: Basic Tkinter popup test
- `direct_alert_test.py`: Direct testing without the full application

## Future Enhancements

- User feedback mechanism for alert relevance
- Machine learning to optimize alert timing and methods
- Additional alert channels (SMS, mobile push notifications)
- Customizable alert templates
