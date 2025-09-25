# FocusGuard

A cross-platform application for monitoring user activity and reducing distractions.

## Features

- Activity monitoring
- Distraction detection
- Calendar integration
- Cross-platform support
- Configurable alert system
- Centralized configuration management

## Installation

```bash
# Install in development mode
pip install -e .

# Install with test dependencies
pip install -e ".[test]"
```

## Running Tests

```bash
pytest tests/
```

## Configuration

FocusGuard uses a centralized JSON configuration file to manage all settings. The configuration file is located at `config/focus_guard_config.json` and is automatically created with default values if it doesn't exist.

### Configuration Structure

```json
{
  "user": {
    "name": "Default User",
    "parent_email": "parent@example.com"
  },
  "alert_system": {
    "cooldown_period": 60,
    "escalation_threshold": 3,
    "escalation_window": 300,
    "providers": {
      "popup": {
        "enabled": true,
        "popup_duration": 10
      },
      "sound": {
        "enabled": true,
        "volume": 0.8,
        "repeat_count": 2,
        "repeat_interval": 0.5
      },
      "email": {
        "enabled": true,
        "email_recipient": "",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_password": "",
        "use_tls": true,
        "from_name": "FocusGuard App",
        "subject_prefix": "FocusGuard Alert",
        "max_emails_per_day": 5,
        "include_screenshot": true
      }
    }
  },
  "distraction_detection": {
    "allowed_apps": ["Windsurf.exe", "code.exe", "explorer.exe", "notepad.exe"],
    "distraction_thresholds": {
      "default": 10,
      "social_media": 5,
      "games": 5,
      "video_streaming": 10
    },
    "categories": {
      "social_media": ["facebook.com", "twitter.com", "instagram.com"],
      "games": ["steam.exe", "epicgameslauncher.exe"],
      "video_streaming": ["youtube.com", "netflix.com", "twitch.tv"]
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

### Configuration Options

#### User Settings
- `name`: The name of the user
- `parent_email`: Email address for parent/guardian notifications

#### Alert System
- `cooldown_period`: Time in seconds between alerts
- `escalation_threshold`: Number of alerts before escalation
- `escalation_window`: Time window in seconds for counting alerts for escalation
- `providers`: Configuration for different alert providers

#### Distraction Detection
- `allowed_apps`: List of applications that are always allowed
- `distraction_thresholds`: Time thresholds in seconds for different categories
- `categories`: Lists of apps/sites categorized by type

#### Monitoring
- `check_interval`: Time in seconds between activity checks
- `session_duration`: Duration of monitoring session in seconds
- `screenshot_enabled`: Whether to take screenshots
- `screenshot_interval`: Time between screenshots in seconds

#### Data Storage
- `log_level`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `log_to_file`: Whether to save logs to file
- `history_retention_days`: Number of days to keep history
- `data_directory`: Directory for storing data files

## License

MIT
