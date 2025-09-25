@echo off
REM Focus Guard Extension - Guided Installation Launcher
REM Launches the Python-based guided installer with better UX

echo Focus Guard Extension - Guided Installer
echo ==========================================
echo.
echo Starting the guided installation process...
echo This installer provides better UX with validation and proper browser opening.
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.6+ and try again
    pause
    exit /b 1
)

REM Run the guided installer
python "%~dp0install_browser_extension_guided.py"

if %errorlevel% equ 0 (
    echo.
    echo Installation completed successfully!
) else (
    echo.
    echo Installation encountered issues. Please check the messages above.
)

echo.
pause
