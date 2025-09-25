@echo off
REM Focus Guard Windows MVP Installation Script
REM Simple one-click installation for Windows users

title Focus Guard Windows MVP Installation

echo.
echo    ╔══════════════════════════════════════════╗
echo    ║    Focus Guard Windows MVP Installer   ║
echo    ║     AI-Powered Productivity Monitor    ║
echo    ╚══════════════════════════════════════════╝
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Administrator privileges required.
    echo Please run this installer as administrator.
    pause
    exit /b 1
)

REM Check Python installation
echo 🔍 Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found!
    echo Please install Python 3.8+ from https://python.org
    echo After installation, run this script again.
    pause
    exit /b 1
)

REM Check Python version
echo ✅ Python found, checking version...
for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✅ Python version: %PYTHON_VERSION%

REM Install package
echo 📦 Installing Focus Guard Windows MVP...
cd /d "%~dp0"

REM Install package in development mode
python -m pip install -e .
if %errorlevel% neq 0 (
    echo ❌ Installation failed!
    echo Try: python -m pip install --upgrade pip
    pause
    exit /b 1
)

REM Create desktop shortcut
echo 🖥️  Creating desktop shortcut...
set DESKTOP_PATH=%USERPROFILE%\Desktop
set SHORTCUT_PATH=%DESKTOP_PATH%\Focus Guard.lnk
set SCRIPT_PATH=%~dp0

powershell -Command "
$WshShell = New-Object -ComObject WScript.Shell;
$Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%');
$Shortcut.TargetPath = 'cmd';
$Shortcut.Arguments = '/k focus-guard-tray';
$Shortcut.WorkingDirectory = '%SCRIPT_PATH%';
$Shortcut.IconLocation = '%SCRIPT_PATH%\\focus_guard\\assets\\icon.ico';
$Shortcut.Description = 'Focus Guard Windows MVP';
$Shortcut.Save()"

REM Create Start Menu shortcut
echo 🏠 Creating Start Menu entry...
set START_MENU_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Focus Guard
mkdir "%START_MENU_PATH%" >nul 2>&1

powershell -Command "
$WshShell = New-Object -ComObject WScript.Shell;
$Shortcut = $WshShell.CreateShortcut('%START_MENU_PATH%\\Focus Guard.lnk');
$Shortcut.TargetPath = 'cmd';
$Shortcut.Arguments = '/k focus-guard-tray';
$Shortcut.WorkingDirectory = '%SCRIPT_PATH%';
$Shortcut.IconLocation = '%SCRIPT_PATH%\\focus_guard\\assets\\icon.ico';
$Shortcut.Description = 'Focus Guard Windows MVP';
$Shortcut.Save()"

REM Add to Windows startup (optional)
echo ⚙️  Adding to Windows startup...
reg add "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v "FocusGuard" /t REG_SZ /d "cmd /k focus-guard-tray" /f

REM Create configuration directory
echo 📁 Creating configuration directory...
mkdir "%USERPROFILE%\AppData\Local\FocusGuard" >nul 2>&1

REM Create default configuration
echo ⚙️  Creating default configuration...
python -c "
from focus_guard.windows_config import WindowsConfig
config = WindowsConfig()
config.save_config(config.default_config)
print('✅ Default configuration created')
"

REM Installation complete
echo.
echo    ╔══════════════════════════════════════════╗
echo    ║        Installation Complete!           ║
echo    ╚══════════════════════════════════════════╝
echo.
echo ✅ Focus Guard Windows MVP installed successfully!
echo.
echo 📍 You can now:
echo    • Double-click "Focus Guard" on your desktop
echo    • Find "Focus Guard" in Start Menu
echo    • Run "focus-guard" from command line
echo.
echo ⚙️  Configuration file created at:
echo    %USERPROFILE%\AppData\Local\FocusGuard\config.json
echo.
echo 🚀 Ready to use! The system tray icon will appear when you start.
echo.
pause
