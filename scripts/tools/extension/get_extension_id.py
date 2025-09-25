"""
Get the extension ID by loading the CRX or unpacked extension.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def get_extension_id():
    """Load extension to get the ID."""
    project_root = Path(__file__).parent.parent
    extension_dir = project_root / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
    
    print("Getting Extension ID")
    print("=" * 40)
    print(f"Extension directory: {extension_dir}")
    
    # Find Edge executable
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    
    edge_path = None
    for path in edge_paths:
        if os.path.exists(path):
            edge_path = path
            break
    
    if not edge_path:
        print("ERROR: Microsoft Edge not found")
        return None
    
    print(f"Edge executable: {edge_path}")
    
    # Launch Edge with extension loaded
    print("\nLaunching Edge with extension...")
    try:
        cmd = [edge_path, f"--load-extension={extension_dir}", "--no-first-run"]
        subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ Edge launched with extension")
        
        print("\nMANUAL STEPS:")
        print("1. Go to: edge://extensions/")
        print("2. Enable 'Developer mode' (left sidebar)")
        print("3. Find 'FocusGuard Tab Watcher (MV3)'")
        print("4. Copy the Extension ID (long string like: abcdefghijklmnopqrstuvwxyz123456)")
        print("5. Paste it below when prompted")
        
        # Get ID from user
        extension_id = input("\nEnter the Extension ID: ").strip()
        
        if len(extension_id) == 32 and extension_id.isalnum():
            print(f"✅ Extension ID captured: {extension_id}")
            return extension_id
        else:
            print("❌ Invalid Extension ID format")
            return None
            
    except Exception as e:
        print(f"❌ Failed to launch Edge: {e}")
        return None

if __name__ == "__main__":
    extension_id = get_extension_id()
    if extension_id:
        print(f"\nExtension ID: {extension_id}")
        
        # Save to file for other scripts
        id_file = Path(__file__).parent.parent / "build" / "crx" / "extension_id.txt"
        with open(id_file, 'w') as f:
            f.write(extension_id)
        print(f"Saved to: {id_file}")
    else:
        sys.exit(1)
