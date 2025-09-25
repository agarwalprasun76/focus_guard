# Focus Guard Windows MVP Implementation
## Windows-Only Development Tickets

This file contains the **minimum viable product** (MVP) implementation focused **exclusively on Windows platform**. These tickets represent the smallest scope needed to create a working, user-installable application.

---

## 🎯 MVP Definition
**Goal**: Create a working Focus Guard application that Windows users can install and use immediately.
**Scope**: Windows-only, CLI-first, single-user, basic functionality
**Timeline**: 1 week sprint

---

## 🚨 MVP CRITICAL TICKETS (Windows-Only)

### [FGV2-WIN-001] Windows Package Structure (Simplified)
**Priority**: P0 - MVP Critical  
**Type**: Infrastructure  
**Effort**: 1 day  
**Assignee**: Developer  

**Description**: Create minimal Windows package structure with essential components only.

**Acceptance Criteria**:
- [ ] Simplified `pyproject.toml` with Windows-specific dependencies
- [ ] Basic `__init__.py` files for core modules
- [ ] Windows-specific entry points
- [ ] Minimal dependency list
- [ ] Windows-only platform markers

**Implementation Details**:
```toml
[project]
name = "focus-guard-windows"
version = "1.0.0-mvp"
description = "Windows-only Focus Guard MVP"
requires-python = ">=3.8"

[project.dependencies]
psutil = ">=5.8.0"
pywin32 = ">=300"
aiohttp = ">=3.8.0"
click = ">=8.0.0"
PyQt5 = ">=5.15.0"

[project.scripts]
focus-guard = "focus_guard.windows_cli:main"
```

**Dependencies**: None  
**Story Points**: 3  

---

### [FGV2-WIN-002] Windows CLI (Minimal)
**Priority**: P0 - MVP Critical  
**Type**: Feature  
**Effort**: 1 day  
**Assignee**: Developer  

**Description**: Create minimal Windows CLI with essential commands only.

**Acceptance Criteria**:
- [ ] `focus-guard start` - Start monitoring
- [ ] `focus-guard stop` - Stop monitoring  
- [ ] `focus-guard status` - Show basic status
- [ ] Windows-specific console output
- [ ] Simple help documentation

**Implementation Details**:
```python
# windows_cli.py
import click
import sys
from focus_guard.core.coordinator import FocusGuardCoordinator

@click.group()
def cli():
    """Focus Guard Windows CLI - Minimal MVP"""
    pass

@cli.command()
def start():
    """Start Focus Guard monitoring."""
    click.echo("Starting Focus Guard...")
    coordinator = FocusGuardCoordinator()
    # Start with Windows-specific settings

@cli.command()
def stop():
    """Stop Focus Guard monitoring."""
    click.echo("Stopping Focus Guard...")

@cli.command()
def status():
    """Show current status."""
    click.echo("Focus Guard Status: Running")
```

**Dependencies**: FGV2-WIN-001  
**Story Points**: 3  

---

### [FGV2-WIN-003] Windows System Tray (Basic)
**Priority**: P0 - MVP Critical  
**Type**: Feature  
**Effort**: 1 day  
**Assignee**: Developer  

**Description**: Create basic Windows system tray with minimal functionality.

**Acceptance Criteria**:
- [ ] Windows system tray icon
- [ ] Right-click menu with: Start, Stop, Exit
- [ ] Status notifications
- [ ] Minimize to tray functionality
- [ ] Auto-start with Windows (registry entry)

**Implementation Details**:
```python
# windows_tray.py
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
import winreg

class WindowsTrayApp:
    def __init__(self):
        self.tray_icon = QSystemTrayIcon()
        self.create_menu()
        self.setup_autostart()
    
    def create_menu(self):
        menu = QMenu()
        start_action = QAction("Start Monitoring")
        stop_action = QAction("Stop Monitoring")  
        exit_action = QAction("Exit")
        
        menu.addAction(start_action)
        menu.addAction(stop_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(menu)
    
    def setup_autostart(self):
        # Add to Windows startup
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                            r"Software\Microsoft\Windows\CurrentVersion\Run", 
                            0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "FocusGuard", 0, winreg.REG_SZ, 
                         f"{sys.executable} -m focus_guard.windows_tray")
```

**Dependencies**: FGV2-WIN-001, FGV2-WIN-002  
**Story Points**: 3  

---

### [FGV2-WIN-004] Windows Installation Script
**Priority**: P0 - MVP Critical  
**Type**: Infrastructure  
**Effort**: 1 day  
**Assignee**: Developer  

**Description**: Create simple Windows batch/PowerShell installation script.

**Acceptance Criteria**:
- [ ] Single-file Windows installer
- [ ] Automatic Python detection
- [ ] Package installation
- [ ] Desktop shortcut creation
- [ ] Start menu entry
- [ ] Installation verification

**Implementation Details**:
```batch
@echo off
REM install_focus_guard.bat

echo Installing Focus Guard Windows MVP...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.8+ first.
    pause
    exit /b 1
)

REM Install package
pip install -e .

REM Create desktop shortcut
powershell -Command "
$WshShell = New-Object -ComObject WScript.Shell;
$Shortcut = $WshShell.CreateShortcut('$env:USERPROFILE\Desktop\Focus Guard.lnk');
$Shortcut.TargetPath = 'focus-guard';
$Shortcut.Save()"

echo Installation complete!
pause
```

**Dependencies**: FGV2-WIN-001, FGV2-WIN-002, FGV2-WIN-003  
**Story Points**: 3  

---

### [FGV2-WIN-005] Windows Configuration (Simplified)
**Priority**: P0 - MVP Critical  
**Type**: Feature  
**Effort**: 1 day  
**Assignee**: Developer  

**Description**: Create minimal Windows configuration system.

**Acceptance Criteria**:
- [ ] Simple JSON configuration file
- [ ] Windows-specific settings
- [ ] Basic configuration editor
- [ ] Configuration validation
- [ ] Default configuration template

**Implementation Details**:
```python
# windows_config.py
import json
import os
from pathlib import Path

class WindowsConfig:
    def __init__(self):
        self.config_path = Path.home() / '.focus_guard' / 'config.json'
        self.default_config = {
            "monitoring_enabled": True,
            "check_interval": 30,
            "blocked_domains": ["facebook.com", "youtube.com"],
            "allowed_apps": ["notepad.exe", "chrome.exe"],
            "notification_enabled": True
        }
    
    def load_config(self):
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        return self.default_config
    
    def save_config(self, config):
        self.config_path.parent.mkdir(exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
```

**Dependencies**: FGV2-WIN-002  
**Story Points**: 3  

---

## 🎯 MVP Sprint Plan (1 Week)

### Day 1: Foundation Setup
- [ ] Create minimal Windows package structure
- [ ] Set up basic `pyproject.toml`
- [ ] Test installation locally

### Day 2: CLI Implementation  
- [ ] Implement basic Windows CLI
- [ ] Test CLI commands
- [ ] Add error handling

### Day 3: System Tray
- [ ] Create Windows system tray
- [ ] Test tray functionality
- [ ] Add basic controls

### Day 4: Configuration & Testing
- [ ] Create Windows configuration
- [ ] Test configuration loading
- [ ] Integration testing

### Day 5: Installation & Polish
- [ ] Create Windows installation script
- [ ] Test complete installation
- [ ] Create basic documentation

## 📋 MVP Success Criteria

### ✅ MVP is Ready When:
- [ ] Windows user can double-click to install
- [ ] Application starts from Start Menu
- [ ] System tray icon appears
- [ ] Basic monitoring works
- [ ] Simple configuration works
- [ ] User can start/stop monitoring

### 📊 MVP Scope Limitations
- **Windows-only** (no cross-platform)
- **CLI-first** (no GUI)
- **Single-user** (no multi-user)
- **Basic features** (no advanced functionality)
- **Manual configuration** (no auto-discovery)

## 🚀 Quick Start Guide (MVP)

### Installation
1. Download `focus-guard-windows-mvp.exe`
2. Double-click to install
3. Follow installation wizard
4. Launch from Start Menu

### Usage
1. Right-click system tray icon
2. Select "Start Monitoring"
3. Configure via simple config file
4. Monitor productivity improvement

---

**Note**: This MVP focuses on getting *something working* for Windows users. Cross-platform support, advanced features, and full GUI will come in subsequent versions.
