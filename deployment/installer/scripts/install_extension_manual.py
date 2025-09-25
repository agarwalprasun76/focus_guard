#!/usr/bin/env python3
"""
Manual Extension Installation Script for Focus Guard
This script provides step-by-step manual installation instructions.
"""

import os
import sys
from pathlib import Path

def main():
    """Main installation function with manual instructions."""
    extension_dir = Path(__file__).parent.parent.parent.parent / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
    
    print("Focus Guard Browser Extension - Manual Installation")
    print("=" * 60)
    print()
    print("Since automated installation methods have limitations, please follow")
    print("these manual steps to install the extension permanently:")
    print()
    
    print("STEP 1: Open your browser")
    print("   - Open Chrome or Edge")
    print()
    
    print("STEP 2: Go to Extensions page")
    print("   - Chrome: Type 'chrome://extensions/' in address bar")
    print("   - Edge: Type 'edge://extensions/' in address bar")
    print()
    
    print("STEP 3: Enable Developer Mode")
    print("   - Look for 'Developer mode' toggle in top-right corner")
    print("   - Turn it ON")
    print()
    
    print("STEP 4: Load the extension")
    print("   - Click 'Load unpacked' button")
    print("   - Navigate to and select this folder:")
    print(f"     {extension_dir}")
    print()
    
    print("STEP 5: Verify installation")
    print("   - You should see 'FocusGuard Tab Watcher (MV3)' in the list")
    print("   - Make sure it's ENABLED (toggle should be blue/on)")
    print()
    
    print("STEP 6: Test the extension")
    print("   - Run the Focus Guard MVP:")
    print("   - python focus_guard/core/mvp_main.py")
    print()
    
    print("=" * 60)
    print("Extension Directory:", extension_dir)
    print("Extension should be permanently installed after these steps!")
    
    # Check if extension directory exists
    if not extension_dir.exists():
        print()
        print("ERROR: Extension directory not found!")
        print("Please ensure the Focus Guard project is properly set up.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
