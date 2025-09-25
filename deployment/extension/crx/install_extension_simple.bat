@echo off
REM Focus Guard Extension - Simple One-Click Installer
REM Uses enterprise policy approach with automatic admin elevation

echo Focus Guard Extension - One-Click Installer
echo ==========================================
echo.
echo This will install the Focus Guard browser extension using
echo Windows enterprise policies. The extension will appear as
echo "Managed by your organization" in your browser.
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges...
    goto :install
) else (
    echo Requesting administrator privileges...
    echo Please click "Yes" when prompted by Windows UAC.
    echo.
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:install
echo.
echo Installing extension policies...
echo.

REM Run the enterprise installation script
powershell -ExecutionPolicy Bypass -File "%~dp0install_extension_enterprise.ps1"

if %errorLevel% == 0 (
    echo.
    echo ========================================
    echo Installation completed successfully!
    echo ========================================
    echo.
    echo NEXT STEPS:
    echo 1. CLOSE ALL Chrome and Edge windows now
    echo 2. Wait 10 seconds
    echo 3. Open Chrome or Edge
    echo 4. Extension will auto-install in 1-2 minutes
    echo 5. Check chrome://extensions to verify
    echo.
    echo The extension will show as "FocusGuard Tab Watcher (MV3)"
    echo and will be marked as "Managed by your organization"
    echo.
) else (
    echo.
    echo Installation failed. Please try the manual installation method.
    echo.
)

echo Press any key to exit...
pause >nul
