# Focus Guard Extension Simple Installer
param(
    [Parameter(Mandatory=$true)]
    [string]$ExtensionPath
)

Write-Host "Focus Guard Extension Auto-Installer" -ForegroundColor Cyan
Write-Host "Extension Path: $ExtensionPath" -ForegroundColor Gray

# Validate extension directory
if (-not (Test-Path $ExtensionPath)) {
    Write-Host "ERROR: Extension directory not found: $ExtensionPath" -ForegroundColor Red
    exit 1
}

$manifestPath = Join-Path $ExtensionPath "manifest.json"
if (-not (Test-Path $manifestPath)) {
    Write-Host "ERROR: manifest.json not found in extension directory" -ForegroundColor Red
    exit 1
}

Write-Host "SUCCESS: Extension files validated" -ForegroundColor Green

# Find Chrome
$chromePath = $null
$chromePaths = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
)

foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        $chromePath = $path
        break
    }
}

# Find Edge
$edgePath = $null
$edgePaths = @(
    "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
)

foreach ($path in $edgePaths) {
    if (Test-Path $path) {
        $edgePath = $path
        break
    }
}

$success = $false

# Install for Chrome
if ($chromePath) {
    Write-Host "`nInstalling for Chrome..." -ForegroundColor Yellow
    
    try {
        # Stop Chrome processes
        Get-Process -Name "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 2
        
        # Enable Developer Mode in Chrome preferences
        $chromeUserDataDir = "${env:LOCALAPPDATA}\Google\Chrome\User Data"
        $prefsFile = Join-Path $chromeUserDataDir "Default\Preferences"
        
        if (Test-Path $prefsFile) {
            Write-Host "INFO: Enabling Developer Mode in Chrome..." -ForegroundColor Cyan
            $prefs = Get-Content $prefsFile -Raw | ConvertFrom-Json
            if (-not $prefs.extensions) { $prefs.extensions = @{} }
            if (-not $prefs.extensions.ui) { $prefs.extensions.ui = @{} }
            $prefs.extensions.ui.developer_mode = $true
            $prefs | ConvertTo-Json -Depth 100 | Set-Content $prefsFile
            Write-Host "SUCCESS: Developer Mode enabled" -ForegroundColor Green
        }
        
        # Create desktop shortcut with extension loading
        $shortcutPath = [System.IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), "Focus Guard - Chrome.lnk")
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut($shortcutPath)
        $Shortcut.TargetPath = $chromePath
        $Shortcut.Arguments = "--load-extension=`"$ExtensionPath`" --no-first-run"
        $Shortcut.Description = "Launch Chrome with Focus Guard Extension"
        $Shortcut.Save()
        
        Write-Host "SUCCESS: Created desktop shortcut for Chrome" -ForegroundColor Green
        
        # Launch Chrome with extension and instructions
        Start-Process -FilePath $chromePath -ArgumentList "--load-extension=`"$ExtensionPath`"", "--no-first-run" -WindowStyle Normal
        Write-Host "SUCCESS: Launched Chrome with extension" -ForegroundColor Green
        Write-Host "INFO: Extension loaded temporarily - will persist if you keep this Chrome session" -ForegroundColor Cyan
        
        $success = $true
    }
    catch {
        Write-Host "ERROR: Chrome installation failed: $_" -ForegroundColor Red
    }
}

# Install for Edge
if ($edgePath) {
    Write-Host "`nInstalling for Edge..." -ForegroundColor Yellow
    
    try {
        # Stop Edge processes
        Get-Process -Name "msedge" -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 2
        
        # Create desktop shortcut
        $shortcutPath = [System.IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), "Focus Guard - Edge.lnk")
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut($shortcutPath)
        $Shortcut.TargetPath = $edgePath
        $Shortcut.Arguments = "--load-extension=`"$ExtensionPath`" --no-first-run"
        $Shortcut.Description = "Launch Edge with Focus Guard Extension"
        $Shortcut.Save()
        
        Write-Host "SUCCESS: Created desktop shortcut for Edge" -ForegroundColor Green
        $success = $true
    }
    catch {
        Write-Host "ERROR: Edge installation failed: $_" -ForegroundColor Red
    }
}

if ($success) {
    Write-Host "`nInstallation completed!" -ForegroundColor Green
    Write-Host "IMPORTANT: For permanent installation:" -ForegroundColor Yellow
    Write-Host "   1. Go to chrome://extensions/ in the launched Chrome window" -ForegroundColor White
    Write-Host "   2. Enable 'Developer mode' (toggle in top right)" -ForegroundColor White
    Write-Host "   3. Click 'Load unpacked' button" -ForegroundColor White
    Write-Host "   4. Select folder: $ExtensionPath" -ForegroundColor White
    Write-Host "   5. The extension will then persist across browser restarts" -ForegroundColor White
    Write-Host "`nTesting:" -ForegroundColor Cyan
    Write-Host "   - Run Focus Guard MVP to test tab detection" -ForegroundColor White
    Write-Host "   - Open YouTube Shorts URL to test blocking" -ForegroundColor White
    exit 0
} else {
    Write-Host "`nInstallation failed" -ForegroundColor Red
    Write-Host "Manual installation required:" -ForegroundColor Yellow
    Write-Host "   1. Open chrome://extensions/ or edge://extensions/" -ForegroundColor White
    Write-Host "   2. Enable 'Developer mode'" -ForegroundColor White
    Write-Host "   3. Click 'Load unpacked'" -ForegroundColor White
    Write-Host "   4. Select: $ExtensionPath" -ForegroundColor White
    exit 1
}
