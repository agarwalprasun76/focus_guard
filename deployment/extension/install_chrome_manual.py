#!/usr/bin/env python3
"""
Chrome Manual Extension Installation Helper
Provides specific guidance for Chrome extension installation.
"""

import os
import sys
import subprocess
from pathlib import Path

def install_chrome_extension():
    """Guide user through Chrome extension installation."""
    extension_dir = Path(__file__).parent.parent.parent / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
    
    print("Chrome Extension Manual Installation")
    print("=" * 40)
    print()
    print("Chrome has stricter security policies than Edge.")
    print("Follow these steps for reliable installation:")
    print()
    
    print("STEP 1: Close ALL Chrome windows")
    print("- Make sure Chrome is completely closed")
    print()
    
    print("STEP 2: Open Chrome fresh")
    print("- Start Chrome normally (don't use any special flags)")
    print()
    
    print("STEP 3: Go to Extensions page")
    print("- Type: chrome://extensions/")
    print("- Press Enter")
    print()
    
    print("STEP 4: Enable Developer Mode")
    print("- Look for 'Developer mode' toggle in TOP-RIGHT corner")
    print("- Turn it ON (should turn blue)")
    print()
    
    print("STEP 5: Load the extension")
    print("- Click 'Load unpacked' button (appears after enabling dev mode)")
    print("- Navigate to and select this folder:")
    print(f"  {extension_dir}")
    print()
    
    print("STEP 6: Verify installation")
    print("- Extension should appear as 'FocusGuard Tab Watcher (MV3)'")
    print("- Make sure the toggle is ON (enabled)")
    print("- You should see the extension icon in the toolbar")
    print()
    
    print("TROUBLESHOOTING:")
    print("- If you see errors, check the Console tab in chrome://extensions/")
    print("- Make sure all files exist in the extension directory")
    print("- Try refreshing the extensions page")
    print()
    
    # Verify extension directory exists
    if not extension_dir.exists():
        print("ERROR: Extension directory not found!")
        print(f"Expected: {extension_dir}")
        return False
    
    # Check required files
    required_files = ["manifest.json", "background.js"]
    missing_files = []
    
    for file in required_files:
        if not (extension_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"ERROR: Missing files: {', '.join(missing_files)}")
        return False
    
    print(f"Extension directory verified: {extension_dir}")
    print()
    print("After installation, test by:")
    print("1. Opening a new tab")
    print("2. Running: python focus_guard/core/mvp_main.py")
    print("3. The MVP should detect the extension")
    
    return True

if __name__ == "__main__":
    install_chrome_extension()
    input("Press Enter when done...")
