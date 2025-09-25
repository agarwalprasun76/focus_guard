@echo off
REM Focus Guard MVP Installation Script
REM This script sets up the Focus Guard MVP for immediate use

echo ================================================
echo FOCUS GUARD MVP INSTALLER
echo ================================================

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python is not installed or not in PATH
    echo     Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo [+] Python found

REM Check if we're in the right directory
if not exist "focus_guard\core\mvp_main.py" (
    echo [!] Error: mvp_main.py not found
    echo     Please run this script from the Focus Guard root directory
    pause
    exit /b 1
)

echo [+] Focus Guard directory structure verified

REM Install dependencies
echo.
echo [+] Installing Python dependencies...
pip install -r requirements/requirements-browser.txt
if %errorlevel% neq 0 (
    echo [!] Failed to install dependencies
    pause
    exit /b 1
)

echo [+] Dependencies installed successfully

REM Test the installation
echo.
echo [+] Testing Focus Guard MVP installation...
python -c "from focus_guard.core.mvp_main import main; print('Installation test passed!')"
if %errorlevel% neq 0 (
    echo [!] Installation test failed
    pause
    exit /b 1
)

echo [+] Installation test passed

REM Run the demo
echo.
echo ================================================
echo RUNNING MVP DEMO
echo ================================================
python demo_mvp.py

echo.
echo ================================================
echo INSTALLATION COMPLETE!
echo ================================================
echo.
echo Focus Guard MVP is now installed and ready to use!
echo.
echo To start Focus Guard:
echo   python focus_guard/core/mvp_main.py
echo.
echo To run the demo again:
echo   python demo_mvp.py
echo.
echo For help and documentation, see:
echo   focus_guard/core/README_FOCUSGUARD.md
echo ================================================

pause
