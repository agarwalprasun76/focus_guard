# Focus Guard Edge Policy Installation
# Run this PowerShell script as Administrator

$ExtensionID = "hmjfbkppeejdnekjapejicmfhfogocjo"
$UpdatesUrl = "https://your-domain.com/focusguard/updates.xml"

Write-Host "Focus Guard Edge Policy Installation" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host "Extension ID: $ExtensionID"
Write-Host "Updates URL: $UpdatesUrl"
Write-Host ""

# Check if running as administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "Attempting user-level policy installation..." -ForegroundColor Yellow
    Write-Host ""
}

# Policy configuration
$PolicyKey = if ($isAdmin) { 'HKLM:\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist' } else { 'HKCU:\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist' }
$PolicyValue = "$ExtensionID;$UpdatesUrl"

try {
    # Create the registry key if it doesn't exist
    if (!(Test-Path $PolicyKey)) {
        Write-Host "Creating policy registry key..." -ForegroundColor Cyan
        New-Item -Path $PolicyKey -Force | Out-Null
    }
    
    # Set the policy value
    Write-Host "Setting extension force-install policy..." -ForegroundColor Cyan
    New-ItemProperty -Path $PolicyKey -Name "1" -Value $PolicyValue -PropertyType String -Force | Out-Null
    
    $scope = if ($isAdmin) { "Machine-wide (HKLM)" } else { "User-specific (HKCU)" }
    Write-Host "SUCCESS: Policy created - $scope" -ForegroundColor Green
    Write-Host "Registry: $PolicyKey" -ForegroundColor Gray
    Write-Host "Value: $PolicyValue" -ForegroundColor Gray
    
} catch {
    Write-Host "FAILED: Could not create policy" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if (-not $isAdmin) {
        Write-Host ""
        Write-Host "SOLUTION: Try running PowerShell as Administrator:" -ForegroundColor Yellow
        Write-Host "1. Right-click PowerShell -> Run as Administrator" -ForegroundColor Yellow
        Write-Host "2. Run this script again" -ForegroundColor Yellow
    }
    
    exit 1
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Close ALL Microsoft Edge windows" -ForegroundColor White
Write-Host "2. Wait 10 seconds" -ForegroundColor White
Write-Host "3. Open Microsoft Edge" -ForegroundColor White
Write-Host "4. Wait 1-2 minutes for policy to take effect" -ForegroundColor White
Write-Host "5. Check edge://policy to verify policy is active" -ForegroundColor White
Write-Host "6. Check edge://extensions to see extension installed" -ForegroundColor White

Write-Host ""
Write-Host "Verification URLs:" -ForegroundColor Cyan
Write-Host "- Policy status: edge://policy" -ForegroundColor White
Write-Host "- Extensions list: edge://extensions" -ForegroundColor White

Write-Host ""
Write-Host "NOTE: Extension will install automatically from policy." -ForegroundColor Green
Write-Host "Users cannot remove force-installed extensions." -ForegroundColor Green
