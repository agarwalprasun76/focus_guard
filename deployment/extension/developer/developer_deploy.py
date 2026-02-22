"""
Load Focus Guard extension in Edge developer mode (no admin required).
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Ensure focus_guard package is importable when run as a standalone script
_repo_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from focus_guard.core.extension_constants import CHROME_EXTENSION_ID

def find_edge_executable():
    """Find Microsoft Edge executable."""
    possible_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def load_extension_in_edge():
    """Load extension in Edge developer mode."""
    extension_id = CHROME_EXTENSION_ID
    extension_path = Path(__file__).parent.parent.parent.parent / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
    
    print("Focus Guard Extension Loader")
    print("=" * 40)
    print(f"Extension ID: {extension_id}")
    print(f"Extension Path: {extension_path}")
    print()
    
    if not extension_path.exists():
        print(f"ERROR: Extension directory not found: {extension_path}")
        return False
    
    edge_exe = find_edge_executable()
    if not edge_exe:
        print("ERROR: Microsoft Edge not found")
        return False
    
    print(f"Found Edge: {edge_exe}")
    print()
    
    # Launch Edge with extension loaded
    print("Launching Edge with extension...")
    cmd = [
        edge_exe,
        f"--load-extension={extension_path}",
        "--no-first-run",
        "--no-default-browser-check",
        "edge://extensions/"
    ]
    
    try:
        subprocess.Popen(cmd)
        print("SUCCESS: Edge launched with extension loaded")
        print()
        print("INSTRUCTIONS:")
        print("1. Edge should open to extensions page")
        print("2. Enable 'Developer mode' (top right toggle)")
        print("3. Extension should appear as 'Focus Guard'")
        print(f"4. Extension ID should be: {extension_id}")
        print("5. Toggle the extension ON if needed")
        print()
        print("The extension is now loaded and active!")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to launch Edge: {e}")
        return False

def create_desktop_shortcut():
    """Create desktop shortcut for easy access."""
    extension_path = Path(__file__).parent.parent.parent.parent / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
    edge_exe = find_edge_executable()
    
    if not edge_exe:
        return False
    
    desktop = Path.home() / "Desktop"
    shortcut_path = desktop / "Focus Guard Extension.bat"
    
    shortcut_content = f'''@echo off
echo Loading Focus Guard Extension...
"{edge_exe}" --load-extension="{extension_path}" --no-first-run edge://extensions/
'''
    
    try:
        with open(shortcut_path, 'w') as f:
            f.write(shortcut_content)
        print(f"Desktop shortcut created: {shortcut_path}")
        return True
    except Exception as e:
        print(f"Could not create shortcut: {e}")
        return False

def main():
    success = load_extension_in_edge()
    
    if success:
        print("=" * 50)
        print("ALTERNATIVE TO REGISTRY POLICY")
        print("=" * 50)
        print("Since registry policies require admin privileges,")
        print("this method loads the extension directly in Edge.")
        print()
        print("To make this permanent:")
        print("1. Keep the extension enabled in Edge")
        print("2. Use the desktop shortcut for easy access")
        print("3. Or bookmark edge://extensions/ page")
        
        create_desktop_shortcut()
        
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
