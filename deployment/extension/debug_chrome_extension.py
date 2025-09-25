#!/usr/bin/env python3
"""
Debug Chrome Extension Loading Issues
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def debug_chrome_extension():
    """Debug why Chrome isn't loading the extension."""
    extension_dir = Path(__file__).parent.parent.parent / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
    
    print("Chrome Extension Debug")
    print("=" * 30)
    print()
    
    # Check extension files
    required_files = ["manifest.json", "background.js"]
    for file in required_files:
        file_path = extension_dir / file
        if file_path.exists():
            print(f"[OK] {file} exists")
        else:
            print(f"[ERROR] {file} missing")
            return False
    
    # Check manifest.json content
    try:
        import json
        with open(extension_dir / "manifest.json", 'r') as f:
            manifest = json.load(f)
        
        print(f"[OK] Manifest version: {manifest.get('manifest_version')}")
        print(f"[OK] Extension name: {manifest.get('name')}")
        print(f"[OK] Extension version: {manifest.get('version')}")
        
        # Check for Chrome-specific issues
        if "service_worker" not in manifest.get("background", {}):
            print("[WARNING] No service_worker in background")
        else:
            print("[OK] Service worker configured")
            
    except Exception as e:
        print(f"[ERROR] Manifest validation failed: {e}")
        return False
    
    # Try launching Chrome with more verbose flags
    chrome_path = None
    possible_paths = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"
    ]
    
    for path in possible_paths:
        if path.exists():
            chrome_path = path
            break
    
    if not chrome_path:
        print("[ERROR] Chrome not found")
        return False
    
    print(f"[OK] Chrome found: {chrome_path}")
    print()
    
    # Close existing Chrome processes
    print("Closing Chrome processes...")
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    time.sleep(3)
    
    # Launch Chrome with debug flags
    print("Launching Chrome with debug flags...")
    args = [
        str(chrome_path),
        f"--load-extension={extension_dir}",
        "--enable-logging",
        "--log-level=0",
        "--enable-extension-activity-logging",
        "--no-first-run",
        "--no-default-browser-check",
        "chrome://extensions/"
    ]
    
    try:
        subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        print("[OK] Chrome launched with debug flags")
        print()
        print("Check Chrome for:")
        print("1. Extension in chrome://extensions/")
        print("2. Any error messages or warnings")
        print("3. Developer mode should be enabled")
        print()
        print("If extension still doesn't appear:")
        print("1. Enable Developer mode in chrome://extensions/")
        print("2. Click 'Load unpacked'")
        print(f"3. Select: {extension_dir}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to launch Chrome: {e}")
        return False

if __name__ == "__main__":
    debug_chrome_extension()
    input("Press Enter to exit...")
