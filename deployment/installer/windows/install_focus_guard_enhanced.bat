@echo off
REM Enhanced Focus Guard Windows Installation Script
REM This script installs Focus Guard with CLI and System Tray support

echo ========================================
echo Focus Guard Enhanced Installation
echo ========================================
echo.

REM Check if Python is installed
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

python --version
echo ✅ Python found

REM Check Python version
echo.
echo [2/6] Verifying Python version...
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"
if errorlevel 1 (
    echo ❌ Python 3.8+ required
    echo Please upgrade your Python installation
    pause
    exit /b 1
)
echo ✅ Python version compatible

REM Install required packages
echo.
echo [3/6] Installing required packages...
pip install click PyQt5 aiohttp psutil requests openai sentence-transformers
if errorlevel 1 (
    echo ❌ Package installation failed
    echo Please check your internet connection and try again
    pause
    exit /b 1
)
echo ✅ Packages installed successfully

REM Install Focus Guard in development mode
echo.
echo [4/6] Installing Focus Guard...
pip install -e .
if errorlevel 1 (
    echo ❌ Focus Guard installation failed
    pause
    exit /b 1
)
echo ✅ Focus Guard installed

REM Create desktop shortcuts
echo.
echo [5/6] Creating shortcuts...

REM Create CLI shortcut
powershell -Command "
$WshShell = New-Object -ComObject WScript.Shell;
$Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Focus Guard CLI.lnk');
$Shortcut.TargetPath = 'cmd.exe';
$Shortcut.Arguments = '/k python -m focus_guard.cli.windows_cli';
$Shortcut.WorkingDirectory = '%CD%';
$Shortcut.Description = 'Focus Guard Command Line Interface';
$Shortcut.Save()"

REM Create System Tray shortcut
powershell -Command "
$WshShell = New-Object -ComObject WScript.Shell;
$Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Focus Guard Tray.lnk');
$Shortcut.TargetPath = 'python.exe';
$Shortcut.Arguments = '-m focus_guard.gui.windows_tray';
$Shortcut.WorkingDirectory = '%CD%';
$Shortcut.Description = 'Focus Guard System Tray Application';
$Shortcut.Save()"

REM Create Start Menu shortcuts
if not exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Focus Guard" mkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Focus Guard"

powershell -Command "
$WshShell = New-Object -ComObject WScript.Shell;
$Shortcut = $WshShell.CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\Focus Guard\Focus Guard CLI.lnk');
$Shortcut.TargetPath = 'cmd.exe';
$Shortcut.Arguments = '/k python -m focus_guard.cli.windows_cli';
$Shortcut.WorkingDirectory = '%CD%';
$Shortcut.Save()"

powershell -Command "
$WshShell = New-Object -ComObject WScript.Shell;
$Shortcut = $WshShell.CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\Focus Guard\Focus Guard Tray.lnk');
$Shortcut.TargetPath = 'python.exe';
$Shortcut.Arguments = '-m focus_guard.gui.windows_tray';
$Shortcut.WorkingDirectory = '%CD%';
$Shortcut.Save()"

echo ✅ Shortcuts created

REM Run installation verification
echo.
echo [6/6] Verifying installation...
python -m focus_guard.cli.windows_cli test
if errorlevel 1 (
    echo ❌ Installation verification failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installing Browser Extensions (Robust)...
echo ========================================
echo.

REM Install browser extensions with robust protection
python -c "
import sys
sys.path.insert(0, '.')
try:
    from focus_guard.core.browser.extension.installer import ExtensionInstaller
    print('Installing browser extensions with robust protection...')
    
    # Use robust installer with protection
    installer = ExtensionInstaller(use_robust_installer=True)
    
    # Install with full protection
    result = installer.install_with_protection()
    
    if 'error' not in result:
        print('Extension installation completed!')
        print('Protection Status:')
        for key, value in result['protection'].items():
            status = 'OK' if value else 'FAIL'
            print(f'  {status} {key}')
        
        # Show installation report
        report = installer.get_installation_status_report()
        print('\nInstallation Report:')
        print(report)
    else:
        print(f'Extension installation failed: {result[\"error\"]}')
        print('Falling back to standard installation...')
        
        # Fall back to standard installation
        results = installer.install_for_detected_browsers()
        for browser, result in results.items():
            status = 'OK' if result['success'] else 'FAIL'
            print(f'  {status} {browser.name}')
            
except Exception as e:
    print(f'Error installing extensions: {e}')
    print('Extensions can be installed manually later.')
"

echo.
echo ========================================
echo Starting Focus Guard...
echo ========================================
echo.

REM Start Focus Guard with enhanced features
python -c "
import sys
sys.path.insert(0, '.')
try:
    from focus_guard.cli.windows_cli import main as cli_main
    print('Starting Focus Guard enhanced version...')
    # Start the coordinator in the background
    import subprocess
    subprocess.Popen([sys.executable, '-c', '''
import sys
sys.path.insert(0, \".\")
from focus_guard.core.coordinator import Coordinator
coordinator = Coordinator()
coordinator.start()
print(\"Focus Guard coordinator started successfully!\")
'''], creationflags=subprocess.CREATE_NEW_CONSOLE)
    print('Focus Guard started in background!')
except Exception as e:
    print(f'Error starting Focus Guard: {e}')
    print('You can start it manually using: focus-guard start')
"

echo.
echo ========================================
echo ✅ Installation Complete!
echo ========================================
echo.
echo You can now use Focus Guard in several ways:
echo.
echo 1. Command Line Interface:
echo    - Desktop shortcut: "Focus Guard CLI"
echo    - Or run: python -m focus_guard.cli.windows_cli
echo.
echo 2. System Tray Application:
echo    - Desktop shortcut: "Focus Guard Tray"
echo    - Or run: python -m focus_guard.gui.windows_tray
echo.
echo 3. Available CLI commands:
echo    - focus-guard-cli start    (Start monitoring)
echo    - focus-guard-cli stop     (Stop monitoring)
echo    - focus-guard-cli status   (Show status)
echo    - focus-guard-cli config   (Open configuration)
echo    - focus-guard-cli test     (Run functionality test)
echo    - focus-guard-cli demo     (Run interactive demo)
echo.
echo 4. System Tray Features:
echo    - Right-click tray icon for menu
echo    - Start/stop monitoring
echo    - Quick access to configuration
echo    - Run tests and demos
echo    - Auto-starts with Windows
echo.
echo Next steps:
echo 1. Launch "Focus Guard Tray" from desktop
echo 2. Right-click the system tray icon
echo 3. Select "Start Monitoring" to begin
echo.
echo For help: python -m focus_guard.cli.windows_cli --help
echo ========================================
pause
