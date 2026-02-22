#!/usr/bin/env python3
"""
Focus Guard Extension - Final Installation Solution
Uses unpacked extension with automated browser launching for easy user experience.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Ensure focus_guard package is importable when run as a standalone script
_repo_root = str(Path(__file__).resolve().parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from focus_guard.core.extension_constants import CHROME_EXTENSION_ID

class FinalExtensionInstaller:
    """Final reliable extension installer using unpacked approach."""
    
    def __init__(self):
        self.extension_id = CHROME_EXTENSION_ID
        self.extension_dir = Path(__file__).parent.parent.parent / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3"
        
    def find_chrome_path(self):
        """Find Chrome executable."""
        possible_paths = [
            Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        return None
    
    def find_edge_path(self):
        """Find Edge executable."""
        possible_paths = [
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        return None
    
    def close_browsers(self):
        """Close all browser instances."""
        try:
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], capture_output=True)
            print("[OK] Closed browser processes")
            time.sleep(3)
        except:
            pass
    
    def launch_with_extension(self, browser_name, browser_path):
        """Launch browser with extension loaded."""
        try:
            args = [
                str(browser_path),
                f"--load-extension={self.extension_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "chrome://extensions/"
            ]
            
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            print(f"[OK] {browser_name} launched with extension")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to launch {browser_name}: {e}")
            return False
    
    def install(self):
        """Main installation process."""
        print("Focus Guard Extension - Final Installer")
        print("=" * 50)
        print()
        print("This installer will:")
        print("1. Close all browser windows")
        print("2. Launch browsers with the extension loaded")
        print("3. Open the extensions page for verification")
        print()
        
        # Verify extension directory
        if not self.extension_dir.exists():
            print(f"[ERROR] Extension directory not found: {self.extension_dir}")
            return False
        
        print(f"[OK] Extension directory: {self.extension_dir}")
        print()
        
        # Close browsers
        print("Closing browsers...")
        self.close_browsers()
        
        # Find browsers
        chrome_path = self.find_chrome_path()
        edge_path = self.find_edge_path()
        
        success = False
        
        # Launch Chrome with extension
        if chrome_path:
            print("Launching Chrome with extension...")
            if self.launch_with_extension("Chrome", chrome_path):
                success = True
                time.sleep(2)  # Delay between browser launches
        else:
            print("[INFO] Chrome not found")
        
        # Launch Edge with extension
        if edge_path:
            print("Launching Edge with extension...")
            if self.launch_with_extension("Edge", edge_path):
                success = True
        else:
            print("[INFO] Edge not found")
        
        if success:
            print()
            print("[OK] Installation completed!")
            print()
            print("VERIFICATION STEPS:")
            print("1. Browser(s) should have opened to chrome://extensions/")
            print("2. Look for 'FocusGuard Tab Watcher (MV3)'")
            print("3. The extension should be loaded and enabled")
            print("4. If you see a yellow warning, click 'Load unpacked' and select:")
            print(f"   {self.extension_dir}")
            print()
            print("TESTING:")
            print("- Open a new tab and visit any website")
            print("- The extension should detect tab changes")
            print("- Run: python focus_guard/core/mvp_main.py")
            print()
            return True
        else:
            print()
            print("[ERROR] No browsers found or launch failed")
            print()
            print("MANUAL INSTALLATION:")
            print("1. Open Chrome or Edge")
            print("2. Go to chrome://extensions/ or edge://extensions/")
            print("3. Enable 'Developer mode'")
            print("4. Click 'Load unpacked'")
            print(f"5. Select: {self.extension_dir}")
            print()
            return False

def main():
    """Main function."""
    installer = FinalExtensionInstaller()
    success = installer.install()
    
    print("Press Enter to exit...")
    input()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
