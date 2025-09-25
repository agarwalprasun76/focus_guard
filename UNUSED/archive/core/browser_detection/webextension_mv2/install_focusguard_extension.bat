@echo off
REM ======================================================================
REM TASK: focusguard-install-extension
REM Installs the FocusGuard WebExtension + native host in the user profile
REM ======================================================================

set FG=%LOCALAPPDATA%\FocusGuard
if not exist "%FG%\ext" mkdir "%FG%\ext"
robocopy /e "%~dp0" "%FG%\ext" >nul
copy "%~dp0focusguard_native_host.exe" "%FG%" >nul

REM 2 ▸ register native-messaging host (Chrome family)
set MAN=%LOCALAPPDATA%\FocusGuard\focusguard_host.json
> "%MAN%" (
  echo {
  echo   "name": "com.focusguard.native",
  echo   "description": "FocusGuard native bridge",
  echo   "path": "%LOCALAPPDATA:\=\\\\%\\FocusGuard\\focusguard_native_host.exe",
  echo   "type": "stdio",
  echo   "allowed_origins": [
  echo     "chrome-extension://apnmgllhphjajigkjlakkkpinbmjgghk//",
  echo     "chrome-extension://__EDGE_ID__//"
  echo   ]
  echo }
)
reg add HKCU\Software\Google\Chrome\NativeMessagingHosts\com.focusguard.native /ve /d "%MAN%" /f
reg add HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.focusguard.native /ve /d "%MAN%" /f

echo Native host registered

REM 3 ▸ external-install the extension (user still must ENABLE it)
reg add HKCU\Software\Google\Chrome\Extensions\apnmgllhphjajigkjlakkkpinbmjgghk /v "path" /d "%LOCALAPPDATA%\FocusGuard\ext" /f
reg add HKCU\Software\Google\Chrome\Extensions\apnmgllhphjajigkjlakkkpinbmjgghk /v "version" /d "1.0.0" /f
reg add HKCU\Software\Microsoft\Edge\Extensions\__EDGE_ID__ /v "path" /d "%LOCALAPPDATA%\FocusGuard\ext" /f
reg add HKCU\Software\Microsoft\Edge\Extensions\__EDGE_ID__ /v "version" /d "1.0.0" /f

echo Extension registered – Chrome/Edge will ask the user to enable it

echo --------------------------------------------------------
echo  ✅ Files copied; registry keys written.
echo  • Next time Chrome / Edge starts, it will ask:
echo      "Enable FocusGuard Tab Watcher?"  → user clicks Enable.
echo  • Incognito?  User opens chrome://extensions →
echo      Details → Allow in Incognito → toggle ON.
echo  • After that, FocusGuard receives a tab snapshot every 2 s.
echo --------------------------------------------------------
