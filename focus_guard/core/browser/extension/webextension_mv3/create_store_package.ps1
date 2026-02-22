# FocusGuard Extension - Store Package Creator
# Creates a ZIP file ready for Chrome Web Store and Edge Add-ons submission

param(
    [string]$OutputPath = ".\dist\FocusGuard_Extension.zip"
)

$ErrorActionPreference = "Stop"

# Get script directory (extension root)
$ExtensionRoot = $PSScriptRoot

# Create dist directory if it doesn't exist
$DistDir = Join-Path $ExtensionRoot "dist"
if (-not (Test-Path $DistDir)) {
    New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
}

# Define files to include
$FilesToInclude = @(
    "manifest.json",
    "background.js",
    "popup.html",
    "popup.js",
    "blocked.html",
    "blocked.js"
)

# Define folders to include
$FoldersToInclude = @(
    "icons"
)

# Create temporary staging directory
$StagingDir = Join-Path $env:TEMP "FocusGuard_Extension_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null

Write-Host "Creating FocusGuard extension package..." -ForegroundColor Cyan
Write-Host "Extension root: $ExtensionRoot" -ForegroundColor Gray

# Copy files
foreach ($file in $FilesToInclude) {
    $sourcePath = Join-Path $ExtensionRoot $file
    if (Test-Path $sourcePath) {
        Copy-Item $sourcePath -Destination $StagingDir
        Write-Host "  + $file" -ForegroundColor Green
    } else {
        Write-Host "  ! Missing: $file" -ForegroundColor Yellow
    }
}

# Copy folders
foreach ($folder in $FoldersToInclude) {
    $sourcePath = Join-Path $ExtensionRoot $folder
    if (Test-Path $sourcePath) {
        $destPath = Join-Path $StagingDir $folder
        Copy-Item $sourcePath -Destination $destPath -Recurse
        
        # Count files in folder
        $fileCount = (Get-ChildItem $destPath -File).Count
        Write-Host "  + $folder/ ($fileCount files)" -ForegroundColor Green
    } else {
        Write-Host "  ! Missing folder: $folder" -ForegroundColor Yellow
    }
}

# Verify required icons exist
$RequiredIcons = @("icon16.png", "icon32.png", "icon48.png", "icon128.png")
$IconsDir = Join-Path $StagingDir "icons"
$MissingIcons = @()

foreach ($icon in $RequiredIcons) {
    $iconPath = Join-Path $IconsDir $icon
    if (-not (Test-Path $iconPath)) {
        $MissingIcons += $icon
    }
}

if ($MissingIcons.Count -gt 0) {
    Write-Host "`nWARNING: Missing required icons:" -ForegroundColor Yellow
    foreach ($icon in $MissingIcons) {
        Write-Host "  - $icon" -ForegroundColor Yellow
    }
    Write-Host "The extension may be rejected without proper icons.`n" -ForegroundColor Yellow
}

# Remove the old zip if it exists
$OutputFullPath = Join-Path $ExtensionRoot $OutputPath
if (Test-Path $OutputFullPath) {
    Remove-Item $OutputFullPath -Force
}

# Create ZIP file
Write-Host "`nCreating ZIP archive..." -ForegroundColor Cyan
Compress-Archive -Path "$StagingDir\*" -DestinationPath $OutputFullPath -Force

# Clean up staging directory
Remove-Item $StagingDir -Recurse -Force

# Get file info
$ZipInfo = Get-Item $OutputFullPath
$SizeKB = [math]::Round($ZipInfo.Length / 1KB, 2)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Package created successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Output: $OutputFullPath" -ForegroundColor White
Write-Host "Size: $SizeKB KB" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to https://chrome.google.com/webstore/devconsole" -ForegroundColor Gray
Write-Host "2. Click 'New Item' and upload this ZIP file" -ForegroundColor Gray
Write-Host "3. Fill in the store listing details" -ForegroundColor Gray
Write-Host "4. Submit for review" -ForegroundColor Gray
Write-Host ""
Write-Host "For Edge Add-ons:" -ForegroundColor Yellow
Write-Host "1. Go to https://partner.microsoft.com/dashboard" -ForegroundColor Gray
Write-Host "2. Navigate to Edge Add-ons section" -ForegroundColor Gray
Write-Host "3. Upload the same ZIP file" -ForegroundColor Gray
