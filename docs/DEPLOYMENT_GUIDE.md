# Focus Guard Activity Monitor - Deployment Guide

This guide explains how to deploy the Focus Guard Activity Monitor on another machine (e.g., for parental monitoring).

## Overview

The deployment system provides:
- **Background activity monitoring** - Tracks application usage, window titles, and idle time
- **Email reports** - Sends hourly and/or daily usage summaries
- **Protected storage** - Log files stored in admin-protected directories
- **Windows service** - Runs automatically at startup, survives reboots
- **Configurable parameters** - Machine name, reporting frequency, retention periods

## Architecture

```
focus_guard/deployment/
├── config.py          # Configuration dataclasses (single source of truth)
├── email_reporter.py  # Email report generation (reuses SQLiteUsageDatabase)
├── service.py         # Windows service wrapper
├── installer.py       # Admin installation utilities
├── build_exe.py       # PyInstaller build script
└── main_service.py    # CLI entry point for the executable
```

## Quick Start

### 1. Build the Executable

```bash
# Install PyInstaller if needed
pip install pyinstaller

# Build the executable
python -m focus_guard.deployment.build_exe --name FocusGuardMonitor --console

# Or use the spec file for more control
python -m focus_guard.deployment.build_exe --use-spec
```

The executable will be created at `dist/FocusGuardMonitor.exe`.

### 2. Configure Before Deployment

Create a configuration file or use the CLI:

```bash
# View current configuration
FocusGuardMonitor.exe config --show

# Set configuration values
FocusGuardMonitor.exe config --set machine_name="DaughterPC" user_name="Sarah"
FocusGuardMonitor.exe config --set email.smtp_username="your.email@gmail.com"
FocusGuardMonitor.exe config --set email.smtp_password="your-app-password"
FocusGuardMonitor.exe config --set email.recipients="parent@email.com"
FocusGuardMonitor.exe config --set reporting.hourly_report=true
FocusGuardMonitor.exe config --set storage.log_retention_days=30
```

### 3. Install on Target Machine

Run as Administrator:

```bash
# Install as Windows service (recommended)
python -m focus_guard.deployment.installer install --exe dist/FocusGuardMonitor.exe

# Or install as startup program (no service)
python -m focus_guard.deployment.installer install --exe dist/FocusGuardMonitor.exe --no-service
```

### 4. Test Email Configuration

```bash
FocusGuardMonitor.exe test-email
```

## Configuration Reference

### Machine Identification

| Parameter | Description | Default |
|-----------|-------------|---------|
| `machine_name` | Name to identify this machine in reports | Computer hostname |
| `user_name` | Name of the user being monitored | Empty |

### Email Settings (`email.*`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `email.enabled` | Enable email reports | `true` |
| `email.smtp_server` | SMTP server address | `smtp.gmail.com` |
| `email.smtp_port` | SMTP port | `587` |
| `email.smtp_username` | SMTP login username | Empty |
| `email.smtp_password` | SMTP password (use app password for Gmail) | Empty |
| `email.use_tls` | Use TLS encryption | `true` |
| `email.sender_email` | From email address | Empty |
| `email.sender_name` | From display name | `FocusGuard Monitor` |
| `email.recipients` | List of recipient emails | Empty |

### Reporting Settings (`reporting.*`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `reporting.hourly_report` | Send hourly reports | `true` |
| `reporting.daily_report` | Send daily reports | `true` |
| `reporting.report_frequency` | Frequency: `hourly`, `every_2_hours`, `every_4_hours`, `daily` | `hourly` |
| `reporting.include_top_apps` | Number of top apps to include | `10` |
| `reporting.include_hourly_breakdown` | Include hourly breakdown in daily reports | `true` |

### Storage Settings (`storage.*`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `storage.data_directory` | Base directory for all data | `C:\ProgramData\FocusGuard` |
| `storage.log_retention_days` | Days to keep log files | `30` |
| `storage.database_retention_days` | Days to keep database records | `90` |

### Monitoring Settings (`monitoring.*`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `monitoring.sampling_interval` | Seconds between activity checks | `5` |
| `monitoring.idle_threshold_short` | Short idle threshold (seconds) | `30` |
| `monitoring.idle_threshold_medium` | Medium idle threshold (seconds) | `120` |
| `monitoring.idle_threshold_long` | Long idle threshold (seconds) | `300` |
| `monitoring.pause_when_locked` | Pause monitoring when screen locked | `true` |

## Gmail Setup for Email Reports

1. Go to your Google Account settings
2. Enable 2-Factor Authentication
3. Go to Security → App passwords
4. Generate a new app password for "Mail"
5. Use this app password (not your regular password) in the config

## File Locations

| Item | Location |
|------|----------|
| Configuration | `C:\ProgramData\FocusGuard\deployment_config.json` |
| Database | `C:\ProgramData\FocusGuard\usage.db` |
| Service logs | `C:\ProgramData\FocusGuard\logs\service_YYYY-MM-DD.log` |
| Activity logs | `C:\ProgramData\FocusGuard\activity_YYYY-MM-DD.log` |

## Service Management

```bash
# Start the service
python -m focus_guard.deployment.installer start

# Stop the service
python -m focus_guard.deployment.installer stop

# Check service status
python -m focus_guard.deployment.installer status

# Uninstall
python -m focus_guard.deployment.installer uninstall
python -m focus_guard.deployment.installer uninstall --remove-data  # Also remove logs
```

## Running Standalone (for testing)

```bash
# Run without installing as service
FocusGuardMonitor.exe run

# Run with verbose output
FocusGuardMonitor.exe -v run
```

## Manual Report Generation

```bash
# Send daily report for yesterday
FocusGuardMonitor.exe report --type daily

# Send daily report for specific date
FocusGuardMonitor.exe report --type daily --date 2026-01-18

# Send hourly report
FocusGuardMonitor.exe report --type hourly
```

## Security Considerations

1. **Admin installation** - The installer requires admin privileges to:
   - Create protected directories that users cannot delete
   - Install as a Windows service
   - Add to startup registry

2. **Protected logs** - Log files are stored in `C:\ProgramData\FocusGuard` with restricted permissions (admin-only write access)

3. **Config password** - Optionally set a password hash to protect configuration changes

## Troubleshooting

### Service won't start
- Check `C:\ProgramData\FocusGuard\logs\service_*.log` for errors
- Ensure all dependencies are bundled in the executable
- Try running standalone first: `FocusGuardMonitor.exe run`

### Emails not sending
- Test with: `FocusGuardMonitor.exe test-email`
- Verify SMTP credentials
- For Gmail, ensure you're using an App Password
- Check firewall isn't blocking SMTP port 587

### No data being logged
- Verify the service is running: `sc query FocusGuardMonitor`
- Check if monitoring is paused (screen locked)
- Look at service logs for errors

## Future Enhancements

- [ ] Configuration UI (planned)
- [ ] Browser extension integration for URL tracking
- [ ] Cloud sync for multi-device monitoring
- [ ] Mobile app for viewing reports
