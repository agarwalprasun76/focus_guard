#!/usr/bin/env python3
"""
Focus Guard Windows .exe Builder

This script builds standalone Windows executables using PyInstaller.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

WINDOWS_DIR = Path(__file__).resolve().parent.parent
APPLICATION_DIR = WINDOWS_DIR.parent
DIST_DIR = APPLICATION_DIR / "dist"
BUILD_DIR = APPLICATION_DIR / "build"

def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"+ PyInstaller {PyInstaller.__version__} found")
        return True
    except ImportError:
        print("X PyInstaller not found")
        print("Install with: pip install pyinstaller")
        return False

def create_version_info():
    """Create version info file for Windows executables."""
    version_info = '''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
# filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
# Set not needed items to zero 0.
filevers=(1,0,0,0),
prodvers=(1,0,0,0),
# Contains a bitmask that specifies the valid bits 'flags'r
mask=0x3f,
# Contains a bitmask that specifies the Boolean attributes of the file.
flags=0x0,
# The operating system for which this file was designed.
# 0x4 - NT and there is no need to change it.
OS=0x4,
# The general type of file.
# 0x1 - the file is an application.
fileType=0x1,
# The function of the file.
# 0x0 - the function is not defined for this fileType
subtype=0x0,
# Creation date and time stamp.
date=(0, 0)
),
  kids=[
StringFileInfo(
  [
  StringTable(
    u'040904B0',
    [StringStruct(u'CompanyName', u'Focus Guard'),
    StringStruct(u'FileDescription', u'Focus Guard - Distraction Blocker'),
    StringStruct(u'FileVersion', u'1.0.0'),
    StringStruct(u'InternalName', u'FocusGuard'),
    StringStruct(u'LegalCopyright', u'Copyright (c) 2025 Focus Guard'),
    StringStruct(u'OriginalFilename', u'FocusGuard.exe'),
    StringStruct(u'ProductName', u'Focus Guard'),
    StringStruct(u'ProductVersion', u'1.0.0')])
  ]), 
VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
    
    version_file = Path(__file__).parent.parent / "version_info.txt"
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(version_info)
    print(f"+ Created version info: {version_file}")

def build_executable(spec_file, name):
    """Build executable using PyInstaller spec file."""
    print(f"\nBuilding {name}...")
    
    spec_path = Path(__file__).parent.parent / "specs" / spec_file
    if not spec_path.exists():
        print(f"X Spec file not found: {spec_path}")
        return False
    
    try:
        # Run PyInstaller
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            str(spec_path),
            "--clean",
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(BUILD_DIR),
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"+ {name} built successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"X {name} build failed:")
        print(f"Error: {e.stderr}")
        return False

def create_simple_installer():
    """Create a simple batch installer."""
    installer_script = '''@echo off
echo Focus Guard Installation
echo ========================

REM Create installation directory
set INSTALL_DIR=%PROGRAMFILES%\\Focus Guard
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy executables
echo Installing Focus Guard CLI...
copy "FocusGuard_CLI.exe" "%INSTALL_DIR%\\" >nul
if errorlevel 1 (
    echo ERROR: Failed to install CLI
    pause
    exit /b 1
)

echo Installing Focus Guard Tray...
copy "FocusGuard_Tray.exe" "%INSTALL_DIR%\\" >nul
if errorlevel 1 (
    echo ERROR: Failed to install Tray
    pause
    exit /b 1
)

REM Create Start Menu shortcuts
echo Creating shortcuts...
set STARTMENU=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTMENU%\\Focus Guard CLI.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\FocusGuard_CLI.exe'; $Shortcut.Save()"
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTMENU%\\Focus Guard Tray.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\FocusGuard_Tray.exe'; $Shortcut.Save()"

REM Create Desktop shortcut for Tray
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\\Desktop\\Focus Guard.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\FocusGuard_Tray.exe'; $Shortcut.Save()"

echo.
echo ✓ Focus Guard installed successfully!
echo.
echo Usage:
echo   - CLI: "%INSTALL_DIR%\\FocusGuard_CLI.exe"
echo   - Tray: "%INSTALL_DIR%\\FocusGuard_Tray.exe"
echo   - Start Menu: Focus Guard CLI / Focus Guard Tray
echo   - Desktop: Focus Guard (Tray)
echo.
pause
'''
    
    installer_path = DIST_DIR / "install_focus_guard.bat"
    installer_path.parent.mkdir(exist_ok=True)
    
    with open(installer_path, 'w', encoding='utf-8') as f:
        f.write(installer_script)
    
    print(f"+ Created installer: {installer_path}")

def main():
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    """Main build process."""
    print("Focus Guard Windows .exe Builder")
    print("=" * 40)
    
    # Check prerequisites
    if not check_pyinstaller():
        return 1
    
    # Create version info
    create_version_info()
    
    # Build executables
    success_count = 0
    
    if build_executable("pyinstaller_cli.spec", "CLI Executable"):
        success_count += 1
    
    if build_executable("pyinstaller_tray.spec", "Tray GUI Executable"):
        success_count += 1
    
    # Create installer
    if success_count > 0:
        create_simple_installer()
    
    # Summary
    print(f"\nBuild Summary")
    print("=" * 20)
    print(f"Executables built: {success_count}/2")
    
    if success_count == 2:
        print("+ All executables built successfully!")
        print("\nNext steps:")
        print("1. Test executables in deployment/application/dist/ directory")
        print("2. Run deployment/application/dist/install_focus_guard.bat to install locally")
        print("3. Deploy browser extension using deployment/tools/deploy.py")
        return 0
    else:
        print("X Some builds failed - check errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
