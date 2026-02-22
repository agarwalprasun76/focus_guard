#!/usr/bin/env python3
"""
Local CRX Installation Script for Focus Guard
Uses direct file system approach without registry policies.
"""

import os
import sys
import subprocess
from pathlib import Path

# Ensure focus_guard package is importable when run as a standalone script
_repo_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from focus_guard.core.extension_constants import CHROME_EXTENSION_ID

class LocalCRXInstaller:
    """Installs Focus Guard extension using local CRX file."""
    
    def __init__(self):
        self.extension_id = CHROME_EXTENSION_ID
        self.crx_dir = Path(__file__).parent
        self.crx_file = self.crx_dir / "FocusGuard_v1.0.0.crx"
        
    def find_chrome_path(self) -> Path:
        """Find Chrome executable path."""
        possible_paths = [
            Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        return None
    
    def find_edge_path(self) -> Path:
        """Find Edge executable path."""
        possible_paths = [
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        return None
    
    def install_crx_chrome(self) -> bool:
        """Install CRX in Chrome using command line."""
        try:
            chrome_path = self.find_chrome_path()
            if not chrome_path:
                print("[ERROR] Chrome not found")
                return False
            
            # Close Chrome first
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], 
                         capture_output=True, text=True)
            
            import time
            time.sleep(2)
            
            # Launch Chrome with CRX installation
            args = [
                str(chrome_path),
                f"--install-extension={self.crx_file}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            print("[OK] Chrome launched with CRX installation")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to install CRX in Chrome: {e}")
            return False
    
    def install_crx_edge(self) -> bool:
        """Install CRX in Edge using command line."""
        try:
            edge_path = self.find_edge_path()
            if not edge_path:
                print("[ERROR] Edge not found")
                return False
            
            # Close Edge first
            subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], 
                         capture_output=True, text=True)
            
            import time
            time.sleep(2)
            
            # Launch Edge with CRX installation
            args = [
                str(edge_path),
                f"--install-extension={self.crx_file}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            print("[OK] Edge launched with CRX installation")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to install CRX in Edge: {e}")
            return False
    
    def verify_crx_file(self) -> bool:
        """Verify CRX file exists."""
        if not self.crx_file.exists():
            print(f"[ERROR] CRX file not found: {self.crx_file}")
            return False
        
        print(f"[OK] CRX file verified: {self.crx_file}")
        return True
    
    def install_all(self) -> bool:
        """Install CRX in all available browsers."""
        print("Focus Guard Local CRX Installation")
        print("=" * 50)
        print(f"Extension ID: {self.extension_id}")
        print(f"CRX File: {self.crx_file}")
        print()
        
        if not self.verify_crx_file():
            return False
        
        chrome_success = self.install_crx_chrome()
        edge_success = self.install_crx_edge()
        
        if chrome_success or edge_success:
            print()
            print("[OK] Installation completed!")
            print()
            print("Next steps:")
            print("1. Browser(s) should have opened with extension installation prompt")
            print("2. Click 'Add Extension' when prompted")
            print("3. Check chrome://extensions or edge://extensions to verify")
            print("4. Extension should appear as 'FocusGuard Tab Watcher (MV3)'")
            return True
        else:
            print()
            print("[ERROR] Failed to install in any browser")
            return False

def main():
    """Main installation function."""
    installer = LocalCRXInstaller()
    return 0 if installer.install_all() else 1

if __name__ == "__main__":
    sys.exit(main())
