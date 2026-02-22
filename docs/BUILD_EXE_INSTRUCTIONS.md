# FocusGuard Activity Monitor - Building the Executable

This document provides step-by-step instructions for building the FocusGuard Activity Monitor as a standalone Windows executable (.exe) for deployment.

## Prerequisites

### 1. Python Environment
- Python 3.10+ installed
- All project dependencies installed: `pip install -e .`

### 2. PyInstaller
Install PyInstaller for creating the executable:
```bash
pip install pyinstaller
```

### 3. Required Dependencies
Ensure these are installed (should be in pyproject.toml):
```bash
pip install pywin32 psutil
```

## Build Process

### Step 1: Verify the Project Works
Before building, test that everything works:
```bash
# Test the deployment module
python scripts/test_deployment.py --show-config

# Run a quick monitor test
python scripts/test_deployment.py --monitor --duration 30

# Test email (if configured)
python scripts/test_deployment.py --test-email
```

### Step 2: Build the Executable
Run the build script:
```bash
python -m focus_guard.deployment.build_exe
```

Or manually with PyInstaller:
```bash
pyinstaller --onefile --noconsole --name FocusGuardService ^
    --add-data "focus_guard;focus_guard" ^
    --hidden-import win32timezone ^
    --hidden-import win32gui ^
    --hidden-import win32process ^
    --hidden-import win32api ^
    --hidden-import win32con ^
    --hidden-import psutil ^
    focus_guard/deployment/main_service.py
```

### Step 3: Locate the Built Executable
After building, the executable will be in:
```
dist/FocusGuardService.exe
```

## Deployment Package

### Files to Include
Create a deployment folder with:
```
FocusGuard/
├── FocusGuardService.exe      # Main executable
├── install.bat                 # Installation script (run as admin)
├── uninstall.bat              # Uninstallation script (run as admin)
├── config_template.json       # Configuration template
└── README.txt                 # Quick start guide
```

### install.bat
```batch
@echo off
echo Installing FocusGuard Activity Monitor...
echo.
echo This requires Administrator privileges.
echo.

:: Check for admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Please run this script as Administrator
    pause
    exit /b 1
)

:: Create directories
mkdir "C:\Program Files\FocusGuard" 2>nul
mkdir "C:\ProgramData\FocusGuard" 2>nul

:: Copy executable
copy /Y FocusGuardService.exe "C:\Program Files\FocusGuard\"

:: Install as Windows service
sc create FocusGuardService binPath= "\"C:\Program Files\FocusGuard\FocusGuardService.exe\"" start= auto
sc description FocusGuardService "FocusGuard Activity Monitor - Monitors application usage and sends reports"
sc failure FocusGuardService reset= 86400 actions= restart/5000/restart/10000/restart/30000

:: Start the service
sc start FocusGuardService

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Configure email settings: FocusGuardService.exe --configure
echo 2. Check service status: sc query FocusGuardService
echo.
pause
```

### uninstall.bat
```batch
@echo off
echo Uninstalling FocusGuard Activity Monitor...
echo.

:: Check for admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Please run this script as Administrator
    pause
    exit /b 1
)

:: Stop and remove service
sc stop FocusGuardService
sc delete FocusGuardService

:: Remove files (optional - uncomment to remove data)
:: rmdir /S /Q "C:\Program Files\FocusGuard"
:: rmdir /S /Q "C:\ProgramData\FocusGuard"

echo.
echo Uninstallation complete!
pause
```

## Configuration

### Pre-Deployment Configuration
Before deploying, configure the settings:

```bash
# Interactive setup
python scripts/test_deployment.py --setup-email

# Or edit the config file directly
notepad C:\ProgramData\FocusGuard\deployment_config.json
```

### Configuration File Location
- **Config file**: `C:\ProgramData\FocusGuard\deployment_config.json`
- **Database**: `C:\ProgramData\FocusGuard\usage.db`
- **Logs**: `C:\ProgramData\FocusGuard\logs\`

### Key Configuration Options

```json
{
  "machine_name": "DaughterLaptop",
  "user_name": "Siyona Agarwal",
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "focusguardapp@gmail.com",
    "smtp_password": "your-app-password",
    "sender_email": "focusguardapp@gmail.com",
    "recipients": ["parent@email.com"]
  },
  "reporting": {
    "schedule": {
      "hourly_enabled": true,
      "hourly_interval_hours": 1,
      "hourly_minute": 5,
      "daily_enabled": true,
      "daily_hour": 7,
      "daily_minute": 0,
      "send_on_start": false,
      "grace_period_minutes": 10
    }
  }
}
```

## Command Line Options

The executable supports these command-line arguments:

```
FocusGuardService.exe [options]

Options:
  --run           Run the service (default)
  --configure     Interactive configuration
  --test-email    Send a test email
  --report        Generate and send a report now
  --status        Show service status
  --help          Show help
```

## Troubleshooting

### Service Won't Start
1. Check Windows Event Viewer for errors
2. Verify config file exists and is valid JSON
3. Run manually to see errors: `FocusGuardService.exe --run`

### Emails Not Sending
1. Verify email configuration: `FocusGuardService.exe --test-email`
2. Check Gmail app password is correct
3. Ensure "Less secure apps" or App Passwords are enabled

### High CPU/Memory Usage
The service is optimized for low resource usage:
- Adaptive sampling (5s active, 30s idle)
- Batched database writes
- Periodic garbage collection

Expected usage: <50MB RAM, <1% CPU

## Security Notes

### Tamper Resistance
When installed as a service with admin privileges:
- Standard users cannot stop the service
- Data directory is protected (C:\ProgramData\FocusGuard)
- Service auto-restarts on failure

### Password Protection
The config file contains the email password. Protect it:
1. Set file permissions to admin-only
2. Consider encrypting sensitive fields (future enhancement)

## Testing Checklist

Before deploying to target machine:

- [ ] Email configuration tested and working
- [ ] Reports generating correctly
- [ ] Service starts automatically on boot
- [ ] Service restarts after failure
- [ ] Standard user cannot stop service
- [ ] Data is being logged to database
- [ ] Visible windows tracking working
- [ ] Idle detection working

## Version History

- **v1.0**: Initial deployment with activity monitoring and email reports
- **v1.1**: Added comprehensive visible windows tracking
- **v1.2**: Configurable scheduling via config file

---

*Last updated: January 2026*
