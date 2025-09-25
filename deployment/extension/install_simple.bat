@echo off
REM Focus Guard Extension - Interactive Installation with Popups
REM Guides user through each step with popup windows for each browser separately

set EXTENSION_DIR=%~dp0..\..\focus_guard\core\browser\extension\webextension_mv3

REM Check if extension directory exists
if not exist "%EXTENSION_DIR%" (
    msg * "ERROR: Extension directory not found! Expected: %EXTENSION_DIR%"
    exit /b 1
)

REM Step 1: Welcome and preparation
msg * "Focus Guard Extension Installer - Welcome! This installer will guide you through installing the Focus Guard extension in Chrome and Edge separately. Click OK to start."

REM Step 2: Close browsers
msg * "STEP 1: Please close ALL Chrome and Edge windows completely before continuing. Click OK when all browsers are closed."

REM ===== CHROME INSTALLATION =====
msg * "Starting CHROME installation. Click OK to continue with Chrome setup."

REM Step 3: Open Chrome
msg * "CHROME STEP 1: Opening Chrome extensions page. Click OK to continue."
start chrome://extensions/
timeout /t 3 /nobreak >nul

REM Step 4: Enable Developer Mode in Chrome
msg * "CHROME STEP 2: In the Chrome window, look for 'Developer mode' toggle in the TOP-RIGHT corner and turn it ON (it should turn blue). Click OK when done."

REM Step 5: Load unpacked extension in Chrome
msg * "CHROME STEP 3: In Chrome, click the 'Load unpacked' button that appeared after enabling Developer mode. Click OK when ready to select the extension folder."

REM Step 6: Show folder path for Chrome - Open folder first
explorer "%EXTENSION_DIR%"
msg * "CHROME STEP 4: A file explorer window just opened showing the extension folder. In Chrome's 'Load unpacked' dialog, navigate to the same folder that just opened. The path is: focus_guard -> core -> browser -> extension -> webextension_mv3. Click OK when you've selected this folder in Chrome."

REM Step 7: Verify Chrome installation
msg * "CHROME STEP 5: Verify the extension appears as 'FocusGuard Tab Watcher (MV3)' in Chrome and make sure it's ENABLED (toggle should be ON). Click OK when Chrome installation is complete."

REM ===== EDGE INSTALLATION =====
msg * "Chrome installation complete! Now starting EDGE installation. Click OK to continue with Edge setup."

REM Step 8: Open Edge
msg * "EDGE STEP 1: Opening Edge extensions page. Click OK to continue."
start msedge://extensions/
timeout /t 3 /nobreak >nul

REM Step 9: Enable Developer Mode in Edge
msg * "EDGE STEP 2: In the Edge window, look for 'Developer mode' toggle in the TOP-RIGHT corner and turn it ON (it should turn blue). Click OK when done."

REM Step 10: Load unpacked extension in Edge
msg * "EDGE STEP 3: In Edge, click the 'Load unpacked' button that appeared after enabling Developer mode. Click OK when ready to select the extension folder."

REM Step 11: Show folder path for Edge - Open folder first
explorer "%EXTENSION_DIR%"
msg * "EDGE STEP 4: A file explorer window just opened showing the extension folder. In Edge's 'Load unpacked' dialog, navigate to the same folder that just opened. The path is: focus_guard -> core -> browser -> extension -> webextension_mv3. Click OK when you've selected this folder in Edge."

REM Step 12: Verify Edge installation
msg * "EDGE STEP 5: Verify the extension appears as 'FocusGuard Tab Watcher (MV3)' in Edge and make sure it's ENABLED (toggle should be ON). Click OK when Edge installation is complete."

REM Step 13: Final instructions
msg * "Installation Complete! The Focus Guard extension is now installed in both Chrome and Edge. To test it, run: python focus_guard\core\mvp_main.py"

REM Step 14: Open file explorer to extension directory for easy access
msg * "Opening the extension folder for your reference. You can bookmark this location for future use."
explorer "%EXTENSION_DIR%"
