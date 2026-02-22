@echo off
REM Canonical source for Extension ID: focus_guard/core/extension_constants.py
echo Focus Guard Edge Policy Installation
echo ====================================
echo Extension ID: hnpfnmlcmdhkbhnfifmnonehebeafclp
echo.

REM Create registry policy using REG command
echo Creating Edge policy in registry...

REM Try user-level first
REG ADD "HKCU\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist" /v "1" /t REG_SZ /d "hnpfnmlcmdhkbhnfifmnonehebeafclp;https://your-domain.com/focusguard/updates.xml" /f

if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: User-level policy created
    echo.
    echo Verifying policy...
    REG QUERY "HKCU\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist" /v "1"
    echo.
    echo NEXT STEPS:
    echo 1. Close ALL Edge windows
    echo 2. Wait 10 seconds
    echo 3. Open Edge
    echo 4. Wait 1-2 minutes
    echo 5. Check edge://policy
    echo 6. Check edge://extensions
    echo.
    echo Extension should install automatically!
) else (
    echo FAILED: Could not create policy
    echo Try running as Administrator:
    echo Right-click Command Prompt -^> Run as Administrator
    echo Then run this script again
)

pause
