@echo off
REM Get the directory of this script, removing trailing backslash if present
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Set absolute paths
set "SRC_DIR=%SCRIPT_DIR%\..\..\core\browser_detection\webExtension_mv2"
set "DIST_DIR=%SRC_DIR%\dist"
set "FG_APPDATA=%LOCALAPPDATA%\FocusGuard"

REM Normalize SRC_DIR to absolute path
pushd "%SRC_DIR%" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Could not change directory to "%SRC_DIR%"
    pause
    exit /b 1
)
set "SRC_DIR=%CD%"
popd >nul

REM Debug: Show paths
echo SCRIPT_DIR=%SCRIPT_DIR%
echo SRC_DIR=%SRC_DIR%
echo DIST_DIR=%DIST_DIR%

REM Check for the native host script
if exist "%SRC_DIR%\focusguard_native_host.py" (
    echo Found focusguard_native_host.py
) else (
    echo NOT FOUND: %SRC_DIR%\focusguard_native_host.py
    pause
    exit /b 1
)

REM Build the native host executable with PyInstaller (from source dir)
pushd "%SRC_DIR%"
python -m PyInstaller --onefile focus_guard_native_host.py
if %ERRORLEVEL% NEQ 0 (
    echo PyInstaller build failed!
    popd
    pause
    exit /b 1
)
popd

REM Copy the built EXE from dist to the source directory for the installer
if not exist "%DIST_DIR%\focus_guard_native_host.exe" (
    echo ERROR: Build output not found: "%DIST_DIR%\focus_guard_native_host.exe"
    pause
    exit /b 1
)

REM Copy the built EXE to the FocusGuard local app data directory for local testing
if not exist "%FG_APPDATA%" mkdir "%FG_APPDATA%"
copy /Y "%DIST_DIR%\focus_guard_native_host.exe" "%FG_APPDATA%\focus_guard_native_host.exe"

echo Native host EXE built and copied to:
echo   %SRC_DIR%\focus_guard_native_host.exe (for installer)
echo   %FG_APPDATA%\focus_guard_native_host.exe (for local testing)
pause