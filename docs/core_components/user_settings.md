# FocusGuard Configuration Guide

This document explains the various configuration settings available in FocusGuard's `focus_guard_config.json` file. Understanding these settings will help you customize the application to your specific needs.

## Configuration File Location

The configuration file is located at:
```
config/focus_guard_config.json
```

This file is automatically created with default values when you first run the application if it doesn't already exist.

## User Settings

| Setting | Description |
|---------|-------------|
| `user.name` | Your name or identifier used in logs and notifications |
| `user.parent_email` | Email address for parent/guardian notifications. This is used as the default recipient for email alerts if no specific recipient is set in the email provider configuration |

## Alert System Settings

### General Alert Settings

| Setting | Description |
|---------|-------------|
| `alert_system.cooldown_period` | Time in seconds between alerts. This prevents alert fatigue by limiting how frequently alerts can be triggered for the same distraction |
| `alert_system.escalation_threshold` | Number of alerts that must occur within the escalation window before the alert level escalates from normal to warning to critical |
| `alert_system.escalation_window` | Time window in seconds during which alerts are counted for escalation purposes |

### Popup Alert Provider

| Setting | Description |
|---------|-------------|
| `alert_system.providers.popup.enabled` | Whether popup notifications are enabled |
| `alert_system.providers.popup.popup_duration` | How long popup notifications remain visible on screen (in seconds) before automatically closing |

### Sound Alert Provider

| Setting | Description |
|---------|-------------|
| `alert_system.providers.sound.enabled` | Whether sound alerts are enabled |
| `alert_system.providers.sound.volume` | Volume level for sound alerts (0.0 to 1.0) |
| `alert_system.providers.sound.repeat_count` | Number of times to repeat the alert sound |
| `alert_system.providers.sound.repeat_interval` | Time in seconds between repeated alert sounds |

### Email Alert Provider

| Setting | Description |
|---------|-------------|
| `alert_system.providers.email.enabled` | Whether email alerts are enabled |
| `alert_system.providers.email.email_recipient` | Email address to receive alerts. If empty, falls back to `user.parent_email` |
| `alert_system.providers.email.smtp_server` | SMTP server address for sending emails (e.g., "smtp.gmail.com") |
| `alert_system.providers.email.smtp_port` | SMTP server port (typically 587 for TLS) |
| `alert_system.providers.email.smtp_username` | Username/email for SMTP authentication |
| `alert_system.providers.email.smtp_password` | Password for SMTP authentication. For Gmail with 2FA, use an app-specific password |
| `alert_system.providers.email.use_tls` | Whether to use TLS encryption for SMTP connection |
| `alert_system.providers.email.from_name` | Name to display as the sender of alert emails |
| `alert_system.providers.email.subject_prefix` | Text to prepend to email subject lines |
| `alert_system.providers.email.max_emails_per_day` | Maximum number of emails to send per day to prevent excessive notifications |
| `alert_system.providers.email.include_screenshot` | Whether to attach screenshots to critical alert emails |

## Distraction Detection Settings

| Setting | Description |
|---------|-------------|
| `distraction_detection.allowed_apps` | List of application executables that are always allowed and never considered distractions |
| `distraction_detection.distraction_thresholds.default` | Default time in seconds that a potential distraction can be active before triggering an alert |
| `distraction_detection.distraction_thresholds.social_media` | Time threshold specifically for social media distractions |
| `distraction_detection.distraction_thresholds.games` | Time threshold specifically for game distractions |
| `distraction_detection.distraction_thresholds.video_streaming` | Time threshold specifically for video streaming distractions |

### Distraction Categories

The `distraction_detection.categories` section defines lists of applications and websites grouped by category. These categories are used with the corresponding thresholds above.

| Category | Description |
|---------|-------------|
| `social_media` | Social media websites and applications that may be distracting |
| `games` | Game executables and websites that may be distracting |
| `video_streaming` | Video streaming websites and applications that may be distracting |

## Monitoring Settings

| Setting | Description |
|---------|-------------|
| `monitoring.check_interval` | How frequently (in seconds) the application checks for distractions |
| `monitoring.session_duration` | Duration of a monitoring session in seconds. The application will run for this amount of time before exiting |
| `monitoring.screenshot_enabled` | Whether to take screenshots during monitoring |
| `monitoring.screenshot_interval` | Time between screenshots in seconds (only if screenshots are enabled) |

## Data Storage Settings

| Setting | Description |
|---------|-------------|
| `data_storage.log_level` | Level of detail for logging. Options: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" |
| `data_storage.log_to_file` | Whether to save logs to a file in addition to console output |
| `data_storage.history_retention_days` | Number of days to keep historical data before automatic deletion |
| `data_storage.data_directory` | Directory for storing data files. If empty, uses a default location |

## Example Configuration

Here's an example of a complete configuration file with explanations:

```json
{
  "user": {
    "name": "Alex",
    "parent_email": "parent@example.com"
  },
  "alert_system": {
    "cooldown_period": 30,
    "escalation_threshold": 3,
    "escalation_window": 300,
    "providers": {
      "popup": {
        "enabled": true,
        "popup_duration": 10
      },
      "sound": {
        "enabled": true,
        "volume": 0.7,
        "repeat_count": 2,
        "repeat_interval": 0.5
      },
      "email": {
        "enabled": true,
        "email_recipient": "parent@example.com",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "focusguardapp@gmail.com",
        "smtp_password": "your-app-specific-password",
        "use_tls": true,
        "from_name": "FocusGuard App",
        "subject_prefix": "FocusGuard Alert",
        "max_emails_per_day": 5,
        "include_screenshot": true
      }
    }
  },
  "distraction_detection": {
    "allowed_apps": ["code.exe", "explorer.exe", "notepad.exe", "word.exe"],
    "distraction_thresholds": {
      "default": 15,
      "social_media": 5,
      "games": 0,
      "video_streaming": 10
    },
    "categories": {
      "social_media": [
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "tiktok.com"
      ],
      "games": [
        "steam.exe",
        "epicgameslauncher.exe",
        "robloxplayer.exe"
      ],
      "video_streaming": [
        "youtube.com",
        "netflix.com",
        "hulu.com",
        "twitch.tv"
      ]
    }
  },
  "monitoring": {
    "check_interval": 10,
    "session_duration": 3600,
    "screenshot_enabled": true,
    "screenshot_interval": 300
  },
  "data_storage": {
    "log_level": "INFO",
    "log_to_file": true,
    "history_retention_days": 30,
    "data_directory": ""
  }
}
```

## Tips for Configuration

1. **Start with Default Values**: The default configuration provides a good starting point. Make small adjustments as needed.

2. **Email Setup**: For Gmail, you'll need to use an app-specific password if you have 2-factor authentication enabled.

3. **Allowed Apps**: Be sure to include all legitimate applications needed for work or study in the `allowed_apps` list.

4. **Distraction Thresholds**: Set these based on your personal needs:
   - Lower values (e.g., 5 seconds) for strict monitoring
   - Higher values (e.g., 30 seconds) for more lenient monitoring

5. **Session Duration**: For study sessions, consider using the Pomodoro technique with sessions of 25-30 minutes (1500-1800 seconds).

6. **Security**: Keep your configuration file secure, especially if it contains email credentials.

## Troubleshooting

- **No Alerts**: Check that the appropriate alert providers are enabled and properly configured.
- **Email Issues**: Verify your SMTP settings and ensure your email provider allows SMTP access.
- **False Positives**: Add frequently used legitimate applications to the `allowed_apps` list.
- **High CPU Usage**: Increase the `check_interval` to reduce how often the application checks for distractions.
