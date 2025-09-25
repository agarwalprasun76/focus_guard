# FocusGuard Configuration Guide

This document explains the configuration settings available in FocusGuard. Understanding these settings will help you customize the application to your specific needs.

## Configuration File Location

The configuration file is located at:
```
config/focus_guard_config.json
```

A template file is provided at `config/focus_guard_config_template.json`. You can copy this file to `focus_guard_config.json` and customize it. The application will automatically create a default configuration file if one doesn't exist.

## User Settings

| Setting | Description |
|---------|-------------|
| `user.name` | Your name or identifier used in logs and notifications |
| `user.parent_email` | Email address for parent/guardian notifications (used as default recipient for email alerts) |

## Alert System Settings

### General Alert Settings

| Setting | Description |
|---------|-------------|
| `alert_system.cooldown_period` | Time in seconds between alerts to prevent alert fatigue |
| `alert_system.escalation_threshold` | Number of alerts before escalation (normal → warning → critical) |
| `alert_system.escalation_window` | Time window in seconds for counting alerts toward escalation |

### Popup Alert Provider

| Setting | Description |
|---------|-------------|
| `alert_system.providers.popup.enabled` | Enable/disable popup notifications |
| `alert_system.providers.popup.popup_duration` | How long popups remain visible (seconds) |

### Sound Alert Provider

| Setting | Description |
|---------|-------------|
| `alert_system.providers.sound.enabled` | Enable/disable sound alerts |
| `alert_system.providers.sound.volume` | Volume level (0.0 to 1.0) |
| `alert_system.providers.sound.repeat_count` | Number of times to repeat the alert sound |
| `alert_system.providers.sound.repeat_interval` | Time between repeated sounds (seconds) |

### Email Alert Provider

| Setting | Description |
|---------|-------------|
| `alert_system.providers.email.enabled` | Enable/disable email alerts |
| `alert_system.providers.email.email_recipient` | Recipient email address (falls back to `user.parent_email` if empty) |
| `alert_system.providers.email.smtp_server` | SMTP server address (e.g., "smtp.gmail.com") |
| `alert_system.providers.email.smtp_port` | SMTP port (typically 587 for TLS) |
| `alert_system.providers.email.smtp_username` | Email username for authentication |
| `alert_system.providers.email.smtp_password` | Email password or app password for authentication |
| `alert_system.providers.email.use_tls` | Whether to use TLS encryption |
| `alert_system.providers.email.use_ssl` | Whether to use SSL encryption (alternative to TLS) |
| `alert_system.providers.email.from_name` | Sender name for emails |
| `alert_system.providers.email.subject_prefix` | Text to prepend to email subjects |
| `alert_system.providers.email.max_emails_per_day` | Daily email limit to prevent excessive notifications |
| `alert_system.providers.email.include_screenshot` | Whether to attach screenshots to critical alerts |

### Desktop Notification Provider

| Setting | Description |
|---------|-------------|
| `alert_system.providers.desktop_notification.enabled` | Enable/disable system desktop notifications |

### App Blocker Provider

| Setting | Description |
|---------|-------------|
| `alert_system.providers.app_blocker.enabled` | Enable/disable temporary blocking of distracting applications |
| `alert_system.providers.app_blocker.block_duration` | How long to block apps (seconds) |
| `alert_system.providers.app_blocker.block_threshold` | Number of alerts before blocking is triggered |

## Distraction Detection Settings

| Setting | Description |
|---------|-------------|
| `distraction_detection.allowed_apps` | List of applications that are never considered distractions |
| `distraction_detection.distraction_thresholds.default` | Default time (seconds) before triggering an alert |
| `distraction_detection.distraction_thresholds.social_media` | Time threshold for social media |
| `distraction_detection.distraction_thresholds.games` | Time threshold for games (0 = immediate alert) |
| `distraction_detection.distraction_thresholds.video_streaming` | Time threshold for video streaming |

### Distraction Categories

The `distraction_detection.categories` section defines lists of applications and websites grouped by category:

| Category | Description |
|---------|-------------|
| `social_media` | Social media websites and applications |
| `games` | Game executables and websites |
| `video_streaming` | Video streaming websites and applications |

## Monitoring Settings

| Setting | Description |
|---------|-------------|
| `monitoring.check_interval` | How often to check for distractions (seconds) |
| `monitoring.session_duration` | Total duration of monitoring session (seconds) |
| `monitoring.screenshot_enabled` | Whether to take screenshots during monitoring |
| `monitoring.screenshot_interval` | Time between screenshots (seconds) |

## Data Storage Settings

| Setting | Description |
|---------|-------------|
| `data_storage.log_level` | Logging detail level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") |
| `data_storage.log_to_file` | Whether to save logs to a file |
| `data_storage.history_retention_days` | Days to keep historical data before deletion |
| `data_storage.data_directory` | Directory for data storage (empty = use default) |

## Example Configuration

Here's an example of a complete configuration file:

```json
{
  "user": {
    "name": "Student",
    "parent_email": "parent@example.com"
  },
  "alert_system": {
    "cooldown_period": 30,
    "escalation_threshold": 3,
    "escalation_window": 300,
    "providers": {
      "popup": {
        "enabled": true,
        "popup_duration": 30
      },
      "sound": {
        "enabled": true,
        "volume": 0.7,
        "repeat_count": 2,
        "repeat_interval": 0.5
      },
      "email": {
        "enabled": true,
        "email_recipient": "",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "your.email@gmail.com",
        "smtp_password": "your-app-password-here",
        "use_tls": true,
        "use_ssl": false,
        "from_name": "FocusGuard App",
        "subject_prefix": "FocusGuard Alert",
        "max_emails_per_day": 5,
        "include_screenshot": true
      },
      "desktop_notification": {
        "enabled": true
      },
      "app_blocker": {
        "enabled": false,
        "block_duration": 300,
        "block_threshold": 5
      }
    }
  },
  "distraction_detection": {
    "allowed_apps": [
      "code.exe",
      "explorer.exe", 
      "notepad.exe", 
      "word.exe", 
      "excel.exe", 
      "powerpnt.exe",
      "teams.exe",
      "zoom.exe"
    ],
    "distraction_thresholds": {
      "default": 10,
      "social_media": 5,
      "games": 0,
      "video_streaming": 10
    },
    "categories": {
      "social_media": [
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "tiktok.com",
        "snapchat.com",
        "reddit.com"
      ],
      "games": [
        "steam.exe",
        "epicgameslauncher.exe",
        "robloxplayer.exe",
        "minecraft.exe",
        "league of legends.exe"
      ],
      "video_streaming": [
        "youtube.com",
        "netflix.com",
        "hulu.com",
        "twitch.tv",
        "disney+.com"
      ]
    }
  },
  "monitoring": {
    "check_interval": 5,
    "session_duration": 3600,
    "screenshot_enabled": true,
    "screenshot_interval": 60
  },
  "data_storage": {
    "log_level": "INFO",
    "log_to_file": true,
    "history_retention_days": 30,
    "data_directory": ""
  }
}
```

## Gmail Configuration Tips

If you're using Gmail for email alerts:

1. For accounts with 2-Factor Authentication (2FA), you must use an App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Sign in with your Google account
   - Select "App" → "Other (Custom name)" → enter "FocusGuard"
   - Click "Generate"
   - Use the generated 16-character password in your configuration

2. For accounts without 2FA, you may need to:
   - Enable "Less secure app access" in your Google Account settings
   - Note: Google is phasing this out, so using an App Password is recommended

## Troubleshooting

- **No Alerts**: Check that alert providers are enabled and properly configured
- **Email Issues**: Verify SMTP settings and ensure your email provider allows SMTP access
- **False Positives**: Add legitimate applications to the `allowed_apps` list
- **High CPU Usage**: Increase the `check_interval` value
- **Session Duration**: If the application runs too long or short, adjust `monitoring.session_duration`
