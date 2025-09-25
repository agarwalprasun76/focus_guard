# Focus Guard Extension PowerShell Installer
param(
    [Parameter(Mandatory=$true)]
    [string]$ExtensionPath
)

Write-Host "🚀 Focus Guard Extension Auto-Installer" -ForegroundColor Cyan
Write-Host "Extension Path: $ExtensionPath" -ForegroundColor Gray

# Function to get browser installation paths
function Get-BrowserPaths {
    $browsers = @{}
    
    # Chrome paths
    $chromePaths = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
    )
    
    foreach ($path in $chromePaths) {
        if (Test-Path $path) {
            $browsers["Chrome"] = $path
            break
        }
    }
    
    # Edge paths
    $edgePaths = @(
        "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
    )
    
    foreach ($path in $edgePaths) {
        if (Test-Path $path) {
            $browsers["Edge"] = $path
            break
        }
    }
    
    return $browsers
}

# Function to get browser user data directories
function Get-BrowserUserData {
    param([string]$Browser)
    
    $userDataPaths = @{
        "Chrome" = "${env:LOCALAPPDATA}\Google\Chrome\User Data"
        "Edge" = "${env:LOCALAPPDATA}\Microsoft\Edge\User Data"
    }
    
    return $userDataPaths[$Browser]
}

# Function to kill browser processes
function Stop-BrowserProcesses {
    param([string]$Browser)
    
    $processNames = @{
        "Chrome" = "chrome"
        "Edge" = "msedge"
    }
    
    $processName = $processNames[$Browser]
    if ($processName) {
        Get-Process -Name $processName -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 2
    }
}

# Function to create extension shortcut method
function Install-ExtensionShortcut {
    param(
        [string]$Browser,
        [string]$BrowserPath,
        [string]$ExtensionPath
    )
    
    try {
        Write-Host "📦 Installing for $Browser..." -ForegroundColor Yellow
        
        # Stop browser processes
        Stop-BrowserProcesses -Browser $Browser
        
        # Create desktop shortcut with extension loaded
        $shortcutName = "Focus Guard - $Browser.lnk"
        $shortcutPath = [System.IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), $shortcutName)
        
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut($shortcutPath)
        $Shortcut.TargetPath = $BrowserPath
        $Shortcut.Arguments = "--load-extension=`"$ExtensionPath`" --no-first-run --no-default-browser-check"
        $Shortcut.Description = "Launch $Browser with Focus Guard Extension"
        $Shortcut.Save()
        
        Write-Host "✅ Created desktop shortcut: $shortcutName" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Failed to create shortcut for $Browser`: $_" -ForegroundColor Red
        return $false
    }
}

# Function to modify browser preferences
function Install-ExtensionPreferences {
    param(
        [string]$Browser,
        [string]$ExtensionPath
    )
    
    try {
        $userDataDir = Get-BrowserUserData -Browser $Browser
        if (-not (Test-Path $userDataDir)) {
            Write-Host "❌ $Browser user data directory not found" -ForegroundColor Red
            return $false
        }
        
        # Find all profiles
        $profiles = @()
        $defaultProfile = Join-Path $userDataDir "Default"
        if (Test-Path $defaultProfile) {
            $profiles += $defaultProfile
        }
        
        # Add numbered profiles
        Get-ChildItem $userDataDir -Directory | Where-Object { $_.Name -match "^Profile \d+$" } | ForEach-Object {
            $profiles += $_.FullName
        }
        
        $successCount = 0
        foreach ($profile in $profiles) {
            $prefsPath = Join-Path $profile "Preferences"
            
            try {
                # Read existing preferences or create new
                if (Test-Path $prefsPath) {
                    $prefs = Get-Content $prefsPath -Raw | ConvertFrom-Json
                } else {
                    $prefs = @{}
                }
                
                # Ensure extensions object exists
                if (-not $prefs.extensions) {
                    $prefs | Add-Member -NotePropertyName "extensions" -NotePropertyValue @{}
                }
                if (-not $prefs.extensions.ui) {
                    $prefs.extensions | Add-Member -NotePropertyName "ui" -NotePropertyValue @{}
                }
                
                # Enable developer mode
                $prefs.extensions.ui | Add-Member -NotePropertyName "developer_mode" -NotePropertyValue $true -Force
                
                # Save preferences
                $prefs | ConvertTo-Json -Depth 10 | Set-Content $prefsPath -Encoding UTF8
                $successCount++
                
                Write-Host "✅ Configured profile: $(Split-Path $profile -Leaf)" -ForegroundColor Green
            }
            catch {
                Write-Host "❌ Failed to configure profile $(Split-Path $profile -Leaf): $_" -ForegroundColor Red
            }
        }
        
        return $successCount -gt 0
    }
    catch {
        Write-Host "❌ Failed to modify $Browser preferences: $_" -ForegroundColor Red
        return $false
    }
}

# Main installation logic
function Install-Extension {
    # Validate extension directory
    if (-not (Test-Path $ExtensionPath)) {
        Write-Host "❌ Extension directory not found: $ExtensionPath" -ForegroundColor Red
        return $false
    }
    
    $manifestPath = Join-Path $ExtensionPath "manifest.json"
    if (-not (Test-Path $manifestPath)) {
        Write-Host "❌ manifest.json not found in extension directory" -ForegroundColor Red
        return $false
    }
    
    Write-Host "✅ Extension files validated" -ForegroundColor Green
    
    # Detect browsers
    $browsers = Get-BrowserPaths
    if ($browsers.Count -eq 0) {
        Write-Host "❌ No supported browsers found (Chrome/Edge)" -ForegroundColor Red
        return $false
    }
    
    Write-Host "🔍 Detected browsers: $($browsers.Keys -join ', ')" -ForegroundColor Cyan
    
    $overallSuccess = $false
    
    foreach ($browser in $browsers.Keys) {
        $browserPath = $browsers[$browser]
        Write-Host "`n📦 Installing for $browser..." -ForegroundColor Yellow
        
        # Try multiple installation methods
        $methods = @(
            @{ Name = "Desktop Shortcut"; Action = { Install-ExtensionShortcut -Browser $browser -BrowserPath $browserPath -ExtensionPath $ExtensionPath } },
            @{ Name = "Browser Preferences"; Action = { Install-ExtensionPreferences -Browser $browser -ExtensionPath $ExtensionPath } }
        )
        
        $browserSuccess = $false
        foreach ($method in $methods) {
            Write-Host "   Trying $($method.Name)..." -ForegroundColor Gray
            if (& $method.Action) {
                $browserSuccess = $true
            }
        }
        
        if ($browserSuccess) {
            $overallSuccess = $true
            Write-Host "✅ $browser installation completed" -ForegroundColor Green
        } else {
            Write-Host "❌ $browser installation failed" -ForegroundColor Red
        }
    }
    
    return $overallSuccess
}

# Run installation
$success = Install-Extension

if ($success) {
    Write-Host "`n🎉 Installation completed!" -ForegroundColor Green
    Write-Host "📝 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Use the desktop shortcuts to launch browsers with the extension" -ForegroundColor White
    Write-Host "   2. Or manually load the extension in developer mode" -ForegroundColor White
    Write-Host "   3. Run Focus Guard MVP to test tab detection" -ForegroundColor White
    exit 0
} else {
    Write-Host "`n❌ Installation failed" -ForegroundColor Red
    Write-Host "📖 Manual installation required:" -ForegroundColor Yellow
    Write-Host "   1. Open chrome://extensions/ or edge://extensions/" -ForegroundColor White
    Write-Host "   2. Enable 'Developer mode'" -ForegroundColor White
    Write-Host "   3. Click 'Load unpacked'" -ForegroundColor White
    Write-Host "   4. Select: $ExtensionPath" -ForegroundColor White
    exit 1
}
