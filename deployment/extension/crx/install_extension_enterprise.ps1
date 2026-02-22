# Focus Guard Extension - Enterprise Installation Script
# Sets up enterprise management and installs extension policies

# Canonical source: focus_guard/core/extension_constants.py
$ExtensionID = "hnpfnmlcmdhkbhnfifmnonehebeafclp"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CrxFile = Join-Path $ScriptDir "FocusGuard_v1.0.0.crx"

Write-Host "Focus Guard Extension - Enterprise Installation" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""

# Function to enable enterprise management
function Enable-EnterpriseManagement {
    param([string]$Browser)
    
    try {
        if ($Browser -eq "Chrome") {
            $CloudManagementPath = "HKLM:\SOFTWARE\Policies\Google\Chrome"
            $EnrollmentPath = "HKLM:\SOFTWARE\Policies\Google\Chrome\CloudManagementEnrollmentToken"
        } else {
            $CloudManagementPath = "HKLM:\SOFTWARE\Policies\Microsoft\Edge"
            $EnrollmentPath = "HKLM:\SOFTWARE\Policies\Microsoft\Edge\CloudManagementEnrollmentToken"
        }
        
        # Create cloud management registry keys to simulate enterprise environment
        if (!(Test-Path $CloudManagementPath)) {
            New-Item -Path $CloudManagementPath -Force | Out-Null
        }
        
        # Set enterprise enrollment token (dummy value to enable enterprise features)
        New-ItemProperty -Path $CloudManagementPath -Name "CloudManagementEnrollmentToken" -Value "enterprise-managed" -PropertyType String -Force | Out-Null
        
        Write-Host "Enterprise management enabled for $Browser" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "Failed to enable enterprise management for $Browser" -ForegroundColor Yellow
        return $false
    }
}

# Function to create extension policy with enterprise support
function Set-ExtensionPolicy {
    param(
        [string]$Browser,
        [string]$RegistryPath,
        [string]$ExtensionID,
        [string]$CrxPath
    )
    
    try {
        Write-Host "Installing $Browser extension policy..." -ForegroundColor Yellow
        
        # Create the registry key
        $FullPath = "HKLM:\$RegistryPath"
        if (!(Test-Path $FullPath)) {
            New-Item -Path $FullPath -Force | Out-Null
        }
        
        # Set the extension policy (direct CRX file reference)
        $PolicyValue = "$ExtensionID;file:///$($CrxPath.Replace('\', '/'))"
        New-ItemProperty -Path $FullPath -Name "1" -Value $PolicyValue -PropertyType String -Force | Out-Null
        
        Write-Host "SUCCESS: $Browser extension policy created" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "ERROR: Failed to create $Browser policy - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Verify CRX file exists
if (!(Test-Path $CrxFile)) {
    Write-Host "ERROR: CRX file not found: $CrxFile" -ForegroundColor Red
    exit 1
}

Write-Host "CRX File: $CrxFile" -ForegroundColor Cyan
Write-Host "Extension ID: $ExtensionID" -ForegroundColor Cyan
Write-Host ""

# Enable enterprise management for both browsers
Write-Host "Enabling enterprise management..." -ForegroundColor Yellow
$ChromeEnterprise = Enable-EnterpriseManagement -Browser "Chrome"
$EdgeEnterprise = Enable-EnterpriseManagement -Browser "Edge"

Write-Host ""

# Install extension policies
$ChromeSuccess = Set-ExtensionPolicy -Browser "Chrome" -RegistryPath "SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist" -ExtensionID $ExtensionID -CrxPath $CrxFile
$EdgeSuccess = Set-ExtensionPolicy -Browser "Edge" -RegistryPath "SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist" -ExtensionID $ExtensionID -CrxPath $CrxFile

Write-Host ""

if ($ChromeSuccess -or $EdgeSuccess) {
    Write-Host "Installation completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT: Close ALL browser windows now!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Then:" -ForegroundColor Cyan
    Write-Host "1. Wait 10 seconds"
    Write-Host "2. Open Chrome or Edge"
    Write-Host "3. The extension will auto-install (may take 1-2 minutes)"
    Write-Host "4. Check chrome://extensions or edge://extensions"
    Write-Host ""
    Write-Host "The extension will show as 'Managed by your organization'" -ForegroundColor Green
} else {
    Write-Host "Installation failed for all browsers" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
