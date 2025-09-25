# Alert System Module

## Overview
The Alert System module provides a flexible and extensible framework for managing and delivering alerts across multiple channels. It's designed to handle various types of notifications, from simple popups to critical system alerts, with support for different delivery mechanisms and user preferences.

## Features

- **Multiple Alert Providers**: Support for various notification channels (popup, sound, email, webhook, etc.)
- **Alert Levels**: Different severity levels (NORMAL, WARNING, CRITICAL) for appropriate handling
- **Conditional Alerting**: Configurable conditions for when and how alerts should be delivered
- **History & Persistence**: Track alert history with configurable retention
- **Cooldown Periods**: Prevent alert fatigue with configurable cooldown periods
- **Cross-Platform Support**: Works across Windows, macOS, and Linux
- **Extensible Architecture**: Easy to add new alert providers and customize behavior

## Core Components

### 1. AlertSystem
The main entry point that manages alert providers, history, and delivery logic.

Key responsibilities:
- Managing alert providers
- Maintaining alert history
- Enforcing cooldown periods
- Coordinating alert delivery

### 2. AlertProvider (Base Class)
Abstract base class for all alert providers. Implementations include:

- **PopupAlertProvider**: Shows visual popup notifications
- **SoundAlertProvider**: Plays alert sounds
- **BlockingAlertProvider**: Shows modal dialogs requiring user acknowledgment
- **EmailAlertProvider**: Sends alerts via email
- **WebhookAlertProvider**: Sends alerts to webhook endpoints
- **AppAlertProvider**: Integrates with companion applications

### 3. AlertConfigManager
Manages configuration for the alert system, including:
- Provider settings
- Alert history size limits
- Cooldown periods
- Provider enable/disable state

### 4. Alert Models
- **AlertInfo**: Contains all information about an alert
- **AlertLevel**: Severity levels (NORMAL, WARNING, CRITICAL)
- **AlertHistoryEntry**: Record of past alerts

## Configuration

The alert system is highly configurable through the `AlertConfigManager`. Example configuration:

```python
{
    "enabled": true,
    "history_size": 100,
    "cooldown_period": 60,
    "default_level": "normal",
    "providers": {
        "popup": {
            "enabled": true,
            "popup_duration": 10,
            "overlay_on_distraction": true,
            "show_app_name": true,
            "max_popups": 3
        },
        "sound": {
            "enabled": true,
            "volume": 0.8,
            "repeat_count": 1,
            "sound_files": {
                "normal": "normal_alert.wav",
                "warning": "warning_alert.wav",
                "critical": "critical_alert.wav"
            },
            "cooldown_period": 30
        },
        "blocking": {
            "enabled": true,
            "timeout": 0,
            "buttons": ["OK", "Snooze", "Disable"],
            "default_button": 0,
            "escalation_threshold": 3,
            "min_level": "warning"
        },
        "email": {
            "enabled": false,
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "use_tls": true,
            "username": "user@example.com",
            "sender": "alerts@example.com",
            "recipients": ["user@example.com"],
            "subject_prefix": "[FocusGuard Alert]"
        },
        "webhook": {
            "enabled": false,
            "urls": ["https://example.com/webhook"],
            "min_level": "warning"
        }
    }
}
```

## Usage Examples

### Basic Usage

```python
from core_v2.alert.alert_system import AlertSystem
from core_v2.alert.models import AlertInfo, AlertLevel

# Initialize the alert system
alert_system = AlertSystem()

# Send an alert
alert_info = AlertInfo(
    app_name="Firefox",
    title="Distraction Detected",
    message="Spending too much time on news websites",
    level=AlertLevel.WARNING
)

alert_system.send_alert(alert_info)
```

### Custom Provider Configuration

```python
from core_v2.alert.alert_system import AlertSystem
from core_v2.alert.providers.email import EmailAlertProvider

# Initialize with custom configuration
alert_system = AlertSystem()

# Add a custom email provider
email_config = {
    "enabled": True,
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "use_tls": True,
    "username": "alerts@example.com",
    "password": "yourpassword",
    "sender": "alerts@example.com",
    "recipients": ["user@example.com"]
}

alert_system.add_provider("email", EmailAlertProvider(email_config))
```

### Handling Alert Responses

```python
from core_v2.alert.alert_system import AlertSystem
from core_v2.alert.models import AlertInfo, AlertLevel

alert_system = AlertSystem()

def handle_alert_response(alert_id: str, response: str):
    print(f"Received response for alert {alert_id}: {response}")
    if response == "snooze":
        print("Snoozing alerts for 30 minutes")
    elif response == "disable":
        print("Disabling alerts")

# Send an alert with callback
alert_info = AlertInfo(
    app_name="Slack",
    title="Message Received",
    message="New message in #general",
    level=AlertLevel.NORMAL,
    response_callback=handle_alert_response,
    response_options=["Dismiss", "Snooze", "Disable"]
)

alert_system.send_alert(alert_info)
```

## Extending the Alert System

### Creating a Custom Alert Provider

1. Create a new class that inherits from `AlertProvider`
2. Implement the required methods
3. Register the provider with the alert system

```python
from core_v2.alert.providers.base import AlertProvider

class CustomAlertProvider(AlertProvider):
    def __init__(self, config=None):
        super().__init__(config)
        self.name = "CustomAlertProvider"
        # Initialize your provider here

    def send_alert(self, alert_info):
        # Implement alert delivery logic
        print(f"Custom alert: {alert_info.title} - {alert_info.message}")
        return True

    def update_config(self, config):
        # Handle configuration updates
        super().update_config(config)
        # Update provider-specific settings
```

## Platform Support

The alert system includes platform-specific implementations for:

- **Windows**: Uses PowerShell for notifications and Windows API for sound
- **macOS**: Uses native Notification Center and system sounds
- **Linux**: Uses libnotify for notifications and aplay for sounds

## Best Practices

1. **Use Appropriate Alert Levels**:
   - NORMAL: For informational messages
   - WARNING: For important notifications
   - CRITICAL: For urgent issues requiring immediate attention

2. **Respect User Preferences**:
   - Check if alerts are enabled before sending
   - Honor user-configured cooldown periods
   - Allow users to disable specific alert types

3. **Error Handling**:
   - Always handle provider failures gracefully
   - Log errors for debugging
   - Fall back to alternative providers when possible

4. **Performance**:
   - Use non-blocking operations for alert delivery
   - Limit the frequency of alerts to prevent notification fatigue
   - Clean up resources when alerts are dismissed

## Troubleshooting

### Common Issues

1. **Alerts not showing up**:
   - Check if the provider is enabled in the configuration
   - Verify that the alert level meets the minimum threshold
   - Check the logs for any error messages

2. **Sound not playing**:
   - Verify that sound files exist at the specified paths
   - Check system volume and mute settings
   - Ensure the platform-specific sound implementation is working

3. **Email alerts failing**:
   - Verify SMTP server settings
   - Check authentication credentials
   - Ensure the network connection is working

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add or update tests
5. Submit a pull request

## License

[Your License Information Here]

## Acknowledgments

- Thanks to all contributors who have helped improve the alert system
- Inspired by various notification libraries and frameworks
