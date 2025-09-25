# Focus Guard Extension Deployment Script
# Generated automatically

$ExtensionID = "hmjfbkppeejdnekjapejicmfhfogocjo"
$CrxUrl = "https://your-domain.com/focusguard/FocusGuard.crx"
$UpdatesUrl = "https://your-domain.com/focusguard/updates.xml"
$Version = "1.0.0"

Write-Host "Focus Guard Extension Deployment" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host "Extension ID: $ExtensionID"
Write-Host "Version: $Version"
Write-Host "CRX URL: $CrxUrl"
Write-Host "Updates URL: $UpdatesUrl"
Write-Host ""

# Create Edge policy
$PolicyKey = 'HKLM:\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist'
$PolicyValue = "$ExtensionID;$UpdatesUrl"

try {
    if (!(Test-Path $PolicyKey)) {
        New-Item -Path $PolicyKey -Force | Out-Null
    }
    New-ItemProperty -Path $PolicyKey -Name 1 -Value $PolicyValue -PropertyType String -Force | Out-Null
    Write-Host "SUCCESS: Machine-wide policy created" -ForegroundColor Green
} catch {
    Write-Host "ADMIN REQUIRED: Run as Administrator for machine-wide policy" -ForegroundColor Yellow
    
    # Try user-specific
    $PolicyKey = 'HKCU:\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist'
    try {
        if (!(Test-Path $PolicyKey)) {
            New-Item -Path $PolicyKey -Force | Out-Null
        }
        New-ItemProperty -Path $PolicyKey -Name 1 -Value $PolicyValue -PropertyType String -Force | Out-Null
        Write-Host "SUCCESS: User-specific policy created" -ForegroundColor Green
    } catch {
        Write-Host "FAILED: Could not create policy" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Upload files to HTTPS server:"
Write-Host "   - C:\Users\prasun_agarwal\focus_guard\build\crx\FocusGuard_v1.0.0.crx -> $CrxUrl"
Write-Host "   - C:\Users\prasun_agarwal\focus_guard\build\crx\updates.xml -> $UpdatesUrl"
Write-Host "2. Close all Edge windows"
Write-Host "3. Open Edge and wait 1-2 minutes"
Write-Host "4. Check edge://policy to verify policy"
Write-Host "5. Check edge://extensions to see extension"
