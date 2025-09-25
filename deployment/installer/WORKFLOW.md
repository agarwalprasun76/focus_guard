# Installer Workflow

This document outlines the complete workflow for end-user installation of Focus Guard.

## Installation Methods

### 1. Windows Batch Installers

#### Standard Installation
```bash
# Run as Administrator
deployment/installer/windows/install_focus_guard.bat
```

#### Enhanced Installation (with extension)
```bash
# Run as Administrator  
deployment/installer/windows/install_focus_guard_enhanced.bat
```

#### MVP Installation (minimal)
```bash
deployment/installer/windows/install_mvp.bat
```

#### Extension Only
```bash
deployment/installer/windows/install_extension.bat
```

### 2. Cross-Platform Python Scripts

#### Automated Extension Installation
```bash
python deployment/installer/scripts/install_extension_automated.py
```

#### PowerShell Extension Installation
```powershell
powershell deployment/installer/scripts/install_extension.ps1
```

### 3. Inno Setup Installer

#### Create Windows Installer
```bash
# Build executable installer
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" deployment/installer/windows/inno_setup/inno_setup_script_mv3.iss
```

## Installation Components

### Core Application
- `FocusGuard_CLI.exe` - Command line interface
- `FocusGuard_Tray.exe` - System tray application
- Configuration files
- Start menu shortcuts
- Desktop shortcuts

### Browser Extension
- Extension files copied to browser directory
- Native messaging host registration
- Browser policy configuration (if enterprise)

### System Integration
- Windows Registry entries
- Startup configuration
- Service registration (if applicable)

## File Locations After Installation

### Windows
- **Executables**: `%PROGRAMFILES%\FocusGuard\`
- **Configuration**: `%APPDATA%\FocusGuard\`
- **Logs**: `%LOCALAPPDATA%\FocusGuard\logs\`
- **Extension**: Browser-specific directories

### Mac
- **Application**: `/Applications/FocusGuard.app`
- **Configuration**: `~/Library/Application Support/FocusGuard/`
- **Logs**: `~/Library/Logs/FocusGuard/`

## Installation Verification

### Check Installation
```bash
# Verify executables
where FocusGuard_CLI.exe
where FocusGuard_Tray.exe

# Check services
sc query FocusGuardService

# Verify extension
# Check browser extensions page
```

### Test Functionality
1. Launch Focus Guard Tray from Start Menu
2. Check system tray icon appears
3. Open browser and verify extension is active
4. Test basic blocking functionality

## Troubleshooting

### Installation Failures
- Run installer as Administrator
- Check antivirus software interference
- Verify sufficient disk space
- Check Windows version compatibility

### Extension Issues
- Manually enable in browser extensions
- Check native messaging host registration
- Verify file permissions
- Restart browser after installation

### Permission Problems
- Ensure Administrator privileges
- Check UAC settings
- Verify registry write permissions
- Check file system permissions

## Uninstallation

### Windows
```bash
# Use Windows Add/Remove Programs
# Or run uninstaller if created by Inno Setup
%PROGRAMFILES%\FocusGuard\unins000.exe
```

### Manual Cleanup
1. Remove application files
2. Delete configuration directories
3. Remove registry entries
4. Uninstall browser extension
5. Remove startup entries

## Distribution

### End-User Distribution
- Provide signed installer executable
- Include installation instructions
- Provide system requirements
- Include troubleshooting guide

### Enterprise Distribution
- Use group policy for deployment
- Configure enterprise browser policies
- Provide silent installation options
- Include deployment verification scripts
