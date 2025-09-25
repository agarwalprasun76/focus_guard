# Focus Guard Testing on Clean Windows Systems

This guide covers testing Focus Guard executables on fresh Windows machines or VMs to ensure proper deployment.

## VM Setup Options

### 1. Windows Sandbox (Recommended for Quick Testing)
- **Built into Windows 10/11 Pro**
- **Pros**: Instant clean environment, automatic cleanup
- **Cons**: Limited to Windows 10/11 Pro, no persistence

**Setup:**
```powershell
# Enable Windows Sandbox
Enable-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM"
```

### 2. VirtualBox VM
- **Free virtualization platform**
- **Pros**: Full control, persistent, works on any Windows
- **Cons**: Requires VM setup and Windows license

**Setup:**
1. Download VirtualBox from oracle.com
2. Create new VM with Windows 10/11 ISO
3. Allocate 4GB RAM, 50GB disk
4. Install Windows with default settings

### 3. VMware Workstation/Player
- **Professional virtualization**
- **Pros**: Better performance, snapshots
- **Cons**: VMware Workstation requires license

### 4. Hyper-V (Windows Pro/Enterprise)
- **Built into Windows**
- **Pros**: Native Windows virtualization
- **Cons**: Requires Windows Pro/Enterprise

## Testing Preparation

### 1. Build Executables
```bash
# On development machine
cd C:\Users\prasun_agarwal\focus_guard
python packaging/build_exe.py
```

### 2. Create Test Package
```bash
# Create distribution folder
mkdir test_package
copy dist\FocusGuard_CLI.exe test_package\
copy dist\FocusGuard_Tray.exe test_package\
copy dist\install_focus_guard.bat test_package\

# Add browser extension for manual testing
xcopy deployment\crx test_package\extension\ /E /I
```

### 3. Transfer to Test System
- **USB drive**: Copy test_package folder
- **Network share**: Share folder from host
- **Cloud storage**: Upload to OneDrive/Google Drive
- **VM shared folder**: Configure in VM settings

## Testing Checklist

### Phase 1: Basic Executable Testing
```bash
# Test CLI executable
FocusGuard_CLI.exe --help
FocusGuard_CLI.exe test
FocusGuard_CLI.exe status

# Test Tray executable (should show system tray icon)
FocusGuard_Tray.exe
```

### Phase 2: Installation Testing
```bash
# Run installer (requires admin)
install_focus_guard.bat

# Verify installation
dir "%PROGRAMFILES%\Focus Guard"
dir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Focus*"
```

### Phase 3: Functionality Testing
```bash
# Test CLI commands
"%PROGRAMFILES%\Focus Guard\FocusGuard_CLI.exe" start
"%PROGRAMFILES%\Focus Guard\FocusGuard_CLI.exe" status
"%PROGRAMFILES%\Focus Guard\FocusGuard_CLI.exe" stop
```

### Phase 4: Browser Extension Testing
```bash
# Deploy extension
python deployment\deploy.py developer  # If Python available
# OR manually load extension from test_package\extension\
```

### Phase 5: Integration Testing
1. Start Focus Guard Tray
2. Open browsers (Chrome, Edge)
3. Navigate to test websites
4. Verify blocking behavior
5. Check system tray menu functionality

## Test Scenarios

### Scenario 1: Clean Windows 10 VM
- **Purpose**: Test on most common Windows version
- **Focus**: Basic functionality, compatibility
- **Expected**: All features work without issues

### Scenario 2: Windows 11 VM
- **Purpose**: Test on latest Windows
- **Focus**: UI compatibility, modern Windows features
- **Expected**: Enhanced system tray integration

### Scenario 3: Windows Server VM
- **Purpose**: Test enterprise deployment
- **Focus**: Group policy, admin restrictions
- **Expected**: Proper handling of restricted environments

### Scenario 4: Minimal Windows VM
- **Purpose**: Test dependency bundling
- **Focus**: No Python, minimal software installed
- **Expected**: Executables run without external dependencies

## Common Issues & Solutions

### Issue: "MSVCP140.dll missing"
**Solution**: Install Visual C++ Redistributable
```bash
# Download and install from Microsoft
# Or bundle with installer
```

### Issue: "PyQt5 not found"
**Solution**: Verify PyQt5 is bundled in .spec file
```python
# In pyinstaller_tray.spec
hiddenimports = ['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets']
```

### Issue: Extension not loading
**Solution**: Check browser extension paths
```bash
# Verify extension files are bundled
dir webextension_mv3\
```

### Issue: Configuration not found
**Solution**: Verify config files are bundled
```bash
# Check config directory in executable
dir config\
```

## Automated Testing Script

Create `test_package\run_tests.bat`:
```batch
@echo off
echo Focus Guard Automated Test Suite
echo ================================

echo Testing CLI executable...
FocusGuard_CLI.exe --help >nul 2>&1
if errorlevel 1 (
    echo FAIL: CLI executable
    goto :end
) else (
    echo PASS: CLI executable
)

echo Testing Tray executable...
start /min FocusGuard_Tray.exe
timeout /t 3 >nul
tasklist | find "FocusGuard_Tray" >nul
if errorlevel 1 (
    echo FAIL: Tray executable
) else (
    echo PASS: Tray executable
    taskkill /f /im FocusGuard_Tray.exe >nul 2>&1
)

echo Testing installation...
install_focus_guard.bat
if exist "%PROGRAMFILES%\Focus Guard\FocusGuard_CLI.exe" (
    echo PASS: Installation
) else (
    echo FAIL: Installation
)

:end
echo.
echo Test complete. Press any key to exit.
pause >nul
```

## VM Snapshots Strategy

1. **Base Snapshot**: Clean Windows installation
2. **Pre-Test Snapshot**: Before Focus Guard installation
3. **Post-Install Snapshot**: After successful installation
4. **Test Snapshots**: Before each major test scenario

## Performance Testing

### Startup Time
```bash
# Measure executable startup time
powershell "Measure-Command { FocusGuard_CLI.exe --help }"
```

### Memory Usage
```bash
# Monitor memory usage
tasklist /fi "imagename eq FocusGuard*" /fo table
```

### File Size Analysis
```bash
# Check executable sizes
dir FocusGuard*.exe
```

## Distribution Testing

### Network Installation
1. Host executables on network share
2. Test installation from network location
3. Verify functionality with network dependencies

### USB Distribution
1. Copy to USB drive
2. Test on multiple machines
3. Verify portable operation

### Cloud Distribution
1. Upload to cloud storage
2. Test download and installation
3. Verify integrity after download

## Documentation for End Users

Create `test_package\README_TESTING.txt`:
```
Focus Guard Testing Instructions
===============================

1. Extract all files to a folder
2. Right-click "install_focus_guard.bat" -> Run as Administrator
3. Look for Focus Guard in Start Menu
4. Launch "Focus Guard Tray" from Start Menu
5. Right-click system tray icon to access features

Troubleshooting:
- If installation fails, check Windows version (requires Windows 10+)
- If executables don't run, install Visual C++ Redistributable
- If browser extension doesn't work, manually load from extension folder

Support: Check logs in %APPDATA%\Focus Guard\logs\
```

This comprehensive testing approach ensures your Focus Guard executables work reliably across different Windows environments.
