# Focus Guard Extension - Admin Installation Script
# Automatically installs extension policies for Chrome and Edge

$ExtensionID = "hmjfbkppeejdnekjapejicmfhfogocjo"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CrxFile = Join-Path $ScriptDir "FocusGuard_v1.0.0.crx"
$UpdatesXml = Join-Path $ScriptDir "updates.xml"

Write-Host "Focus Guard Extension - Admin Installation" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Extension ID: $ExtensionID"
Write-Host "CRX File: $CrxFile"
Write-Host "Updates XML: $UpdatesXml"
Write-Host ""

# Verify files exist
if (!(Test-Path $CrxFile)) {
    Write-Host "ERROR: CRX file not found: $CrxFile" -ForegroundColor Red
    exit 1
}

if (!(Test-Path $UpdatesXml)) {
    Write-Host "ERROR: Updates XML not found: $UpdatesXml" -ForegroundColor Red
    exit 1
}

Write-Host "Files verified successfully" -ForegroundColor Green
Write-Host ""

# Function to create registry policy
function Create-ExtensionPolicy {
    param(
        [string]$Browser,
        [string]$RegistryPath,
        [string]$PolicyValue
    )
    
    try {
        Write-Host "Installing $Browser policy..." -ForegroundColor Yellow
        
        # Create the registry key if it doesn't exist
        if (!(Test-Path "HKLM:\$RegistryPath")) {
            New-Item -Path "HKLM:\$RegistryPath" -Force | Out-Null
        }
        
        # Set the policy value
        New-ItemProperty -Path "HKLM:\$RegistryPath" -Name "1" -Value $PolicyValue -PropertyType String -Force | Out-Null
        
        Write-Host "SUCCESS: $Browser policy created" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "ERROR: Failed to create $Browser policy - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Create policy value (using direct CRX file path)
$PolicyValue = "$ExtensionID;file:///$($CrxFile.Replace('\', '/'))"

# Install Chrome policy
$ChromeSuccess = Create-ExtensionPolicy -Browser "Chrome" -RegistryPath "SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist" -PolicyValue $PolicyValue

# Install Edge policy  
$EdgeSuccess = Create-ExtensionPolicy -Browser "Edge" -RegistryPath "SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist" -PolicyValue $PolicyValue

Write-Host ""

if ($ChromeSuccess -or $EdgeSuccess) {
    Write-Host "Installation completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "The extension will automatically install when you:" -ForegroundColor Yellow
    Write-Host "1. Close all browser windows"
    Write-Host "2. Open Chrome or Edge"
    Write-Host "3. Wait 1-2 minutes for policy to take effect"
    Write-Host ""
    Write-Host "To verify installation:" -ForegroundColor Yellow
    Write-Host "- Check chrome://policy or edge://policy"
    Write-Host "- Check chrome://extensions or edge://extensions"
    Write-Host "- Look for 'FocusGuard Tab Watcher (MV3)'"
    Write-Host ""
    Write-Host "Note: The extension will be force-installed and managed by policy" -ForegroundColor Cyan
} else {
    Write-Host "Installation failed for all browsers" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
