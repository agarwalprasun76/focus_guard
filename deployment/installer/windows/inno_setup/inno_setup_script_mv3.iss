[Setup]
AppName=FocusGuard
AppVersion=1.0
DefaultDirName={localappdata}\FocusGuard
DefaultGroupName=FocusGuard
UninstallDisplayIcon={app}\focus_guard_native_host.exe
OutputDir=output

[Files]
; Copy native messaging host executable
Source: "..\\..\\core\\browser_detection\\webExtension_mv3\\dist\\focus_guard_native_host.exe"; DestDir: "{localappdata}\\FocusGuard"; Flags: ignoreversion

; Copy native messaging host manifest
Source: "..\\..\\installer\\win\\focus_guard_host.json"; DestDir: "{localappdata}\\FocusGuard"; Flags: ignoreversion

; Copy web extension files
Source: "..\\..\\core\\browser_detection\\webExtension_mv3\\manifest.json"; DestDir: "{localappdata}\\FocusGuard\\ext"; Flags: ignoreversion
Source: "..\\..\\core\\browser_detection\\webExtension_mv3\\background.js"; DestDir: "{localappdata}\\FocusGuard\\ext"; Flags: ignoreversion
Source: "..\\..\\core\\browser_detection\\webExtension_mv3\\icons\\*"; DestDir: "{localappdata}\\FocusGuard\\ext\\icons"; Flags: ignoreversion recursesubdirs createallsubdirs

; Copy README file
Source: "..\\..\\installer\\README.md"; DestDir: "{localappdata}\\FocusGuard"; Flags: ignoreversion

; Copy background.js for extension
Source: "..\\..\\core\\browser_detection\\webExtension_mv3\\background.js"; DestDir: "{localappdata}\\FocusGuard\\ext"; Flags: ignoreversion

[Registry]
; Chrome Native Messaging host registration
Root: HKCU; Subkey: "Software\\Google\\Chrome\\NativeMessagingHosts\\com.focusguard.native"; ValueType: string; ValueData: "{localappdata}\\FocusGuard\\focus_guard_host.json"; Flags: uninsdeletevalue

; Edge Native Messaging host registration
Root: HKCU; Subkey: "Software\\Microsoft\\Edge\\NativeMessagingHosts\\com.focusguard.native"; ValueType: string; ValueData: "{localappdata}\\FocusGuard\\focus_guard_host.json"; Flags: uninsdeletevalue

; Chrome external extension install
Root: HKCU; Subkey: "Software\\Google\\Chrome\\Extensions\\apnmgllhphjajigkjlakkkpinbmjgghk"; ValueType: string; ValueName: "path"; ValueData: "{localappdata}\\FocusGuard\\ext"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\\Google\\Chrome\\Extensions\\apnmgllhphjajigkjlakkkpinbmjgghk"; ValueType: string; ValueName: "version"; ValueData: "1.0.0"; Flags: uninsdeletevalue

; Edge external extension install (replace __EDGE_ID__ with your actual Edge extension ID)
Root: HKCU; Subkey: "Software\\Microsoft\\Edge\\Extensions\\apnmgllhphjajigkjlakkkpinbmjgghk"; ValueType: string; ValueName: "path"; ValueData: "{localappdata}\\FocusGuard\\ext"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\\Microsoft\\Edge\\Extensions\\apnmgllhphjajigkjlakkkpinbmjgghk"; ValueType: string; ValueName: "version"; ValueData: "1.0.0"; Flags: uninsdeletevalue

[Run]
; Open Chrome Extensions Page after installation
Filename: "chrome.exe"; Parameters: "chrome://extensions/"; Description: "Open Chrome Extensions Page"; Flags: postinstall nowait skipifdoesntexist

; Open Edge Extensions Page after installation
Filename: "msedge.exe"; Parameters: "edge://extensions/"; Description: "Open Edge Extensions Page"; Flags: postinstall nowait skipifdoesntexist

[Code]
function IsProcessRunning(const ProcName: String): Boolean;
var
  FSWbemLocator, FWMIService, FWbemObjectSet: Variant;
begin
  Result := False;
  try
    FSWbemLocator := CreateOleObject('WbemScripting.SWbemLocator');
    FWMIService := FSWbemLocator.ConnectServer('.', 'root\CIMV2', '', '');
    FWbemObjectSet := FWMIService.ExecQuery('SELECT * FROM Win32_Process WHERE Name = ''' + ProcName + '''');
    Result := (FWbemObjectSet.Count > 0);
  except
    Result := False;
  end;
end;

function InitializeSetup(): Boolean;
var
  runningApps: String;
begin
  runningApps := '';
  if IsProcessRunning('chrome.exe') then
    runningApps := runningApps + 'Chrome\n';
  if IsProcessRunning('msedge.exe') then
    runningApps := runningApps + 'Edge\n';
  if IsProcessRunning('focus_guard_native_host.exe') then
    runningApps := runningApps + 'FocusGuard Native Host\n';

  if runningApps <> '' then
  begin
    MsgBox('Please close the following applications before installing FocusGuard:\n\n' + runningApps, mbInformation, MB_OK);
    Result := False;
    exit;
  end;
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox('FocusGuard has been successfully installed. Please enable the extension in your browser.', mbInformation, MB_OK);
  end;
end;