# Focus Guard VM Testing Setup Script
# Creates and configures a Windows VM for testing Focus Guard executables

param(
    [Parameter(Mandatory=$false)]
    [string]$VMName = "FocusGuard-Test-VM",
    
    [Parameter(Mandatory=$false)]
    [string]$ISOPath = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Sandbox", "Hyper-V", "VirtualBox")]
    [string]$Platform = "Sandbox"
)

Write-Host "Focus Guard VM Testing Setup" -ForegroundColor Green
Write-Host "============================" -ForegroundColor Green

function Test-WindowsSandbox {
    $feature = Get-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM"
    return $feature.State -eq "Enabled"
}

function Enable-WindowsSandbox {
    Write-Host "Enabling Windows Sandbox..." -ForegroundColor Yellow
    try {
        Enable-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM" -All -NoRestart
        Write-Host "✓ Windows Sandbox enabled (restart required)" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "✗ Failed to enable Windows Sandbox: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Create-SandboxConfig {
    $configContent = @"
<Configuration>
    <VGpu>Enable</VGpu>
    <Networking>Enable</Networking>
    <MappedFolders>
        <MappedFolder>
            <HostFolder>$PWD\test_package</HostFolder>
            <SandboxFolder>C:\FocusGuard</SandboxFolder>
            <ReadOnly>false</ReadOnly>
        </MappedFolder>
    </MappedFolders>
    <LogonCommand>
        <Command>C:\FocusGuard\run_tests.bat</Command>
    </LogonCommand>
</Configuration>
"@
    
    $configPath = "$PWD\FocusGuard-Sandbox.wsb"
    $configContent | Out-File -FilePath $configPath -Encoding UTF8
    Write-Host "✓ Created sandbox config: $configPath" -ForegroundColor Green
    return $configPath
}

function Create-TestPackage {
    Write-Host "Creating test package..." -ForegroundColor Yellow
    
    $testDir = "$PWD\test_package"
    if (Test-Path $testDir) {
        Remove-Item $testDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $testDir | Out-Null
    
    # Copy executables if they exist
    if (Test-Path "$PWD\deployment\application\dist\FocusGuard_CLI.exe") {
        Copy-Item "$PWD\deployment\application\dist\FocusGuard_CLI.exe" $testDir
        Write-Host "✓ Copied CLI executable" -ForegroundColor Green
    } else {
        Write-Host "⚠ CLI executable not found - run build_exe.py first" -ForegroundColor Yellow
    }
    
    if (Test-Path "$PWD\deployment\application\dist\FocusGuard_Tray.exe") {
        Copy-Item "$PWD\deployment\application\dist\FocusGuard_Tray.exe" $testDir
        Write-Host "✓ Copied Tray executable" -ForegroundColor Green
    } else {
        Write-Host "⚠ Tray executable not found - run build_exe.py first" -ForegroundColor Yellow
    }
    
    if (Test-Path "$PWD\deployment\installer\windows\install_focus_guard.bat") {
        Copy-Item "$PWD\deployment\installer\windows\install_focus_guard.bat" $testDir
        Write-Host "✓ Copied installer" -ForegroundColor Green
    }
    
    # Copy extension files
    if (Test-Path "$PWD\deployment\extension\crx") {
        Copy-Item "$PWD\deployment\extension\crx" "$testDir\extension" -Recurse
        Write-Host "✓ Copied browser extension" -ForegroundColor Green
    }
    
    # Create test script
    $testScript = @"
@echo off
echo Focus Guard VM Test Suite
echo ========================
echo.

echo Testing CLI executable...
if exist FocusGuard_CLI.exe (
    FocusGuard_CLI.exe --help >nul 2>&1
    if errorlevel 1 (
        echo ✗ CLI executable failed
    ) else (
        echo ✓ CLI executable works
    )
) else (
    echo ✗ CLI executable not found
)

echo.
echo Testing Tray executable...
if exist FocusGuard_Tray.exe (
    echo ✓ Tray executable found
    echo   ^(Manual test: Double-click to run^)
) else (
    echo ✗ Tray executable not found
)

echo.
echo Testing installer...
if exist install_focus_guard.bat (
    echo ✓ Installer found
    echo   ^(Manual test: Right-click ^> Run as Administrator^)
) else (
    echo ✗ Installer not found
)

echo.
echo Testing browser extension...
if exist extension\ (
    echo ✓ Extension files found
    echo   ^(Manual test: Load unpacked extension in browser^)
) else (
    echo ✗ Extension files not found
)

echo.
echo Test package ready for manual testing
echo =====================================
echo 1. Run install_focus_guard.bat as Administrator
echo 2. Check Start Menu for Focus Guard shortcuts
echo 3. Launch Focus Guard Tray from Start Menu
echo 4. Load browser extension from extension folder
echo.
pause
"@
    
    $testScript | Out-File -FilePath "$testDir\run_tests.bat" -Encoding ASCII
    Write-Host "✓ Created test script" -ForegroundColor Green
    
    return $testDir
}

function Show-Instructions {
    param([string]$Platform, [string]$ConfigPath = "")
    
    Write-Host "`nTesting Instructions:" -ForegroundColor Cyan
    Write-Host "====================" -ForegroundColor Cyan
    
    switch ($Platform) {
        "Sandbox" {
            Write-Host "1. Double-click: $ConfigPath" -ForegroundColor White
            Write-Host "2. Windows Sandbox will open with Focus Guard files" -ForegroundColor White
            Write-Host "3. Test script will run automatically" -ForegroundColor White
            Write-Host "4. Manually test GUI and browser extension" -ForegroundColor White
        }
        "Hyper-V" {
            Write-Host "1. Open Hyper-V Manager" -ForegroundColor White
            Write-Host "2. Create new VM with Windows 10/11 ISO" -ForegroundColor White
            Write-Host "3. Copy test_package folder to VM" -ForegroundColor White
            Write-Host "4. Run run_tests.bat in VM" -ForegroundColor White
        }
        "VirtualBox" {
            Write-Host "1. Open VirtualBox" -ForegroundColor White
            Write-Host "2. Create new VM with Windows 10/11 ISO" -ForegroundColor White
            Write-Host "3. Set up shared folder pointing to test_package" -ForegroundColor White
            Write-Host "4. Run run_tests.bat in VM" -ForegroundColor White
        }
    }
    
    Write-Host "`nTest Checklist:" -ForegroundColor Cyan
    Write-Host "□ CLI executable runs without errors" -ForegroundColor White
    Write-Host "□ Tray executable shows system tray icon" -ForegroundColor White
    Write-Host "□ Installer creates Start Menu shortcuts" -ForegroundColor White
    Write-Host "□ Browser extension loads and functions" -ForegroundColor White
    Write-Host "□ No missing DLL or dependency errors" -ForegroundColor White
}

# Main execution
switch ($Platform) {
    "Sandbox" {
        if (-not (Test-WindowsSandbox)) {
            Write-Host "Windows Sandbox not enabled. Enabling..." -ForegroundColor Yellow
            if (Enable-WindowsSandbox) {
                Write-Host "Please restart your computer and run this script again." -ForegroundColor Yellow
                exit 0
            } else {
                Write-Host "Failed to enable Windows Sandbox. Try Hyper-V or VirtualBox instead." -ForegroundColor Red
                exit 1
            }
        }
        
        $testDir = Create-TestPackage
        $configPath = Create-SandboxConfig
        Show-Instructions -Platform "Sandbox" -ConfigPath $configPath
    }
    
    "Hyper-V" {
        $testDir = Create-TestPackage
        Show-Instructions -Platform "Hyper-V"
        Write-Host "`nHyper-V Setup:" -ForegroundColor Yellow
        Write-Host "Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All" -ForegroundColor Gray
    }
    
    "VirtualBox" {
        $testDir = Create-TestPackage
        Show-Instructions -Platform "VirtualBox"
        Write-Host "`nVirtualBox Download:" -ForegroundColor Yellow
        Write-Host "https://www.virtualbox.org/wiki/Downloads" -ForegroundColor Gray
    }
}

Write-Host "`n✓ VM testing setup complete!" -ForegroundColor Green
