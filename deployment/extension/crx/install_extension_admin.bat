@echo off
REM Focus Guard Extension - One-Click Admin Installation
REM This script automatically requests admin privileges and installs the extension

echo Focus Guard Extension Installer
echo ================================
echo.
echo This installer will:
echo 1. Request administrator privileges
echo 2. Install extension policies for Chrome and Edge
echo 3. The extension will auto-install when you open your browser
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Already running as administrator...
    goto :install
) else (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:install
echo.
echo Installing Focus Guard extension policies...
echo.

REM Run the PowerShell installation script
powershell -ExecutionPolicy Bypass -Command "& '%~dp0install_extension_admin.ps1'"

echo.
echo Installation completed!
echo.
echo Next steps:
echo 1. Close all Chrome/Edge windows
echo 2. Open Chrome or Edge
echo 3. Wait 1-2 minutes for the extension to auto-install
echo 4. Check chrome://extensions or edge://extensions to verify
echo.
pause
