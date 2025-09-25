@echo off
echo ========================================
echo Focus Guard Extension Auto-Installer
echo ========================================

set EXTENSION_DIR=%~dp0..\webextension_mv3
echo Extension directory: %EXTENSION_DIR%

REM Check if extension directory exists
if not exist "%EXTENSION_DIR%" (
    echo ERROR: Extension directory not found!
    echo Expected: %EXTENSION_DIR%
    pause
    exit /b 1
)

echo.
echo Installing extension for Chrome and Edge...

REM Run PowerShell script for installation
powershell -ExecutionPolicy Bypass -File "%~dp0install_extension_simple.ps1" "%EXTENSION_DIR%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✅ Installation completed successfully!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Close ALL Chrome/Edge windows completely
    echo 2. Restart Chrome or Edge
    echo 3. The extension should be automatically loaded
    echo 4. Run the Focus Guard MVP to test
    echo.
) else (
    echo.
    echo ========================================
    echo ❌ Installation failed
    echo ========================================
    echo Please try manual installation:
    echo 1. Open chrome://extensions/ or edge://extensions/
    echo 2. Enable Developer mode
    echo 3. Click "Load unpacked"
    echo 4. Select: %EXTENSION_DIR%
    echo.
)

pause
