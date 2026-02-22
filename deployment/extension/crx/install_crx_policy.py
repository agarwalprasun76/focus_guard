#!/usr/bin/env python3
"""
CRX Policy-Based Extension Installation Script for Focus Guard
Uses Windows Registry policies to force-install the extension.
"""

import os
import sys
import winreg
import subprocess
from pathlib import Path

# Ensure focus_guard package is importable when run as a standalone script
_repo_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from focus_guard.core.extension_constants import CHROME_EXTENSION_ID

class CRXPolicyInstaller:
    """Installs Focus Guard extension using Windows Registry policies."""
    
    def __init__(self):
        self.extension_id = CHROME_EXTENSION_ID
        self.crx_dir = Path(__file__).parent
        self.crx_file = self.crx_dir / "FocusGuard_v1.0.0.crx"
        self.updates_xml = self.crx_dir / "updates.xml"
        
    def create_chrome_policy(self) -> bool:
        """Create Chrome registry policy for extension installation."""
        try:
            policy_key = r"SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist"
            policy_value = f"{self.extension_id};file:///{self.updates_xml.as_posix()}"
            
            # Use user-specific policy (works without admin)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, policy_key) as key:
                winreg.SetValueEx(key, "1", 0, winreg.REG_SZ, policy_value)
            print("[OK] Chrome user-specific policy created")
            return True
                
        except Exception as e:
            print(f"[ERROR] Failed to create Chrome policy: {e}")
            return False
    
    def create_edge_policy(self) -> bool:
        """Create Edge registry policy for extension installation."""
        try:
            policy_key = r"SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist"
            policy_value = f"{self.extension_id};file:///{self.updates_xml.as_posix()}"
            
            # Use user-specific policy (works without admin)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, policy_key) as key:
                winreg.SetValueEx(key, "1", 0, winreg.REG_SZ, policy_value)
            print("[OK] Edge user-specific policy created")
            return True
                
        except Exception as e:
            print(f"[ERROR] Failed to create Edge policy: {e}")
            return False
    
    def verify_files(self) -> bool:
        """Verify required files exist."""
        if not self.crx_file.exists():
            print(f"[ERROR] CRX file not found: {self.crx_file}")
            return False
            
        if not self.updates_xml.exists():
            print(f"[ERROR] Updates XML not found: {self.updates_xml}")
            return False
            
        print("[OK] Required files verified")
        return True
    
    def close_browsers(self) -> bool:
        """Close all browser instances to allow policy refresh."""
        try:
            # Close Chrome
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], 
                         capture_output=True, text=True)
            
            # Close Edge
            subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], 
                         capture_output=True, text=True)
            
            print("[OK] Closed browser processes")
            import time
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to close browsers: {e}")
            return False
    
    def install_all(self) -> bool:
        """Install extension for all browsers using registry policies."""
        print("Focus Guard CRX Policy Installation")
        print("=" * 50)
        print(f"Extension ID: {self.extension_id}")
        print(f"CRX File: {self.crx_file}")
        print(f"Updates XML: {self.updates_xml}")
        print()
        
        # Verify files
        if not self.verify_files():
            return False
        
        # Close browsers
        print("Closing browsers to refresh policies...")
        self.close_browsers()
        
        # Create policies
        chrome_success = self.create_chrome_policy()
        edge_success = self.create_edge_policy()
        
        if chrome_success or edge_success:
            print()
            print("[OK] Installation completed successfully!")
            print()
            print("Next steps:")
            print("1. Start Chrome or Edge")
            print("2. Wait 1-2 minutes for policy to take effect")
            print("3. Check chrome://policy or edge://policy to verify")
            print("4. Check chrome://extensions or edge://extensions")
            print("5. Extension should appear as 'FocusGuard Tab Watcher (MV3)'")
            print()
            print("Note: Extension will be force-installed and cannot be disabled by users")
            return True
        else:
            print()
            print("[ERROR] Failed to create any policies")
            return False
    
    def remove_policies(self) -> bool:
        """Remove extension policies (for uninstallation)."""
        try:
            # Remove Chrome policies
            try:
                winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist")
            except:
                pass
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, 
                               r"SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist")
            except:
                pass
            
            # Remove Edge policies
            try:
                winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist")
            except:
                pass
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, 
                               r"SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist")
            except:
                pass
            
            print("[OK] Extension policies removed")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to remove policies: {e}")
            return False

def main():
    """Main installation function."""
    installer = CRXPolicyInstaller()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--remove":
        return 0 if installer.remove_policies() else 1
    else:
        return 0 if installer.install_all() else 1

if __name__ == "__main__":
    sys.exit(main())
