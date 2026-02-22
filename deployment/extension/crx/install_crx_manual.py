#!/usr/bin/env python3
"""
Manual CRX Installation Guide for Focus Guard
Provides step-by-step instructions for CRX installation.
"""

import os
import sys
from pathlib import Path

# Ensure focus_guard package is importable when run as a standalone script
_repo_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from focus_guard.core.extension_constants import CHROME_EXTENSION_ID

def main():
    """Main function with CRX installation instructions."""
    crx_file = Path(__file__).parent / "FocusGuard_v1.0.0.crx"
    
    print("Focus Guard CRX Installation Guide")
    print("=" * 50)
    print()
    print("The automated CRX installation requires manual steps because:")
    print("- Chrome/Edge block automatic CRX installation for security")
    print("- Registry policies need administrator privileges")
    print("- Command line flags don't work with CRX files")
    print()
    
    print("MANUAL CRX INSTALLATION STEPS:")
    print()
    
    print("METHOD 1: Drag and Drop (Easiest)")
    print("1. Open Chrome or Edge")
    print("2. Go to chrome://extensions/ or edge://extensions/")
    print("3. Enable 'Developer mode' (toggle in top-right)")
    print("4. Drag and drop this file into the browser window:")
    print(f"   {crx_file}")
    print("5. Click 'Add Extension' when prompted")
    print()
    
    print("METHOD 2: Registry Policy (Enterprise)")
    print("1. Run PowerShell as Administrator")
    print("2. Execute these commands:")
    print()
    print("For Chrome:")
    print('New-Item -Path "HKLM:\\SOFTWARE\\Policies\\Google\\Chrome\\ExtensionInstallForcelist" -Force')
    print(f'New-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Google\\Chrome\\ExtensionInstallForcelist" -Name "1" -Value "{CHROME_EXTENSION_ID};file:///{crx_file.as_posix()}" -PropertyType String -Force')
    print()
    print("For Edge:")
    print('New-Item -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Edge\\ExtensionInstallForcelist" -Force')
    print(f'New-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Edge\\ExtensionInstallForcelist" -Name "1" -Value "{CHROME_EXTENSION_ID};file:///{crx_file.as_posix()}" -PropertyType String -Force')
    print()
    print("3. Restart browser and wait 1-2 minutes")
    print()
    
    print("METHOD 3: Unpack and Load (Development)")
    print("1. Extract the CRX file contents")
    print("2. Use 'Load unpacked' with the extracted folder")
    print("3. This is the same as the manual installation we tried earlier")
    print()
    
    print("RECOMMENDED: Use METHOD 1 (Drag and Drop)")
    print("It's the simplest and most reliable approach.")
    print()
    
    # Check if CRX file exists
    if not crx_file.exists():
        print("ERROR: CRX file not found!")
        print(f"Expected location: {crx_file}")
        return 1
    
    print(f"CRX File Location: {crx_file}")
    print("File size:", f"{crx_file.stat().st_size:,} bytes")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
