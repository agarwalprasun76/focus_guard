"""
Configure Edge policy for force-installing Focus Guard extension.
"""

import os
import sys
import winreg
from pathlib import Path

class EdgePolicyManager:
    """Manages Edge extension policies via Windows Registry."""
    
    def __init__(self):
        self.build_dir = Path(__file__).parent.parent / "build" / "crx"
        
    def create_force_install_policy(self, extension_id: str, updates_url: str):
        """Create ExtensionInstallForcelist policy in registry."""
        print("Configuring Edge Force-Install Policy")
        print("=" * 50)
        
        # Machine-wide policy (requires admin)
        policy_key = r'SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist'
        policy_value = f'{extension_id};{updates_url}'
        
        try:
            # Try HKLM first (machine-wide, requires admin)
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, policy_key) as key:
                winreg.SetValueEx(key, '1', 0, winreg.REG_SZ, policy_value)
            
            print(f"SUCCESS: Machine-wide policy created")
            print(f"Registry: HKLM\\{policy_key}")
            print(f"Value: {policy_value}")
            return True
            
        except PermissionError:
            print("ADMIN REQUIRED: Cannot create machine-wide policy")
            print("Trying user-specific policy...")
            
            try:
                # Fallback to HKCU (user-specific, no admin required)
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, policy_key) as key:
                    winreg.SetValueEx(key, '1', 0, winreg.REG_SZ, policy_value)
                
                print(f"SUCCESS: User-specific policy created")
                print(f"Registry: HKCU\\{policy_key}")
                print(f"Value: {policy_value}")
                return True
                
            except Exception as e:
                print(f"FAILED: Could not create policy: {e}")
                return False
        
        except Exception as e:
            print(f"FAILED: Registry error: {e}")
            return False
    
    def verify_policy(self):
        """Verify the policy is active."""
        policy_key = r'SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist'
        
        for hive, name in [(winreg.HKEY_LOCAL_MACHINE, "HKLM"), (winreg.HKEY_CURRENT_USER, "HKCU")]:
            try:
                with winreg.OpenKey(hive, policy_key) as key:
                    value, _ = winreg.QueryValueEx(key, '1')
                    print(f"Policy found in {name}: {value}")
                    return True
            except FileNotFoundError:
                continue
            except Exception as e:
                print(f"Error checking {name}: {e}")
        
        print("No policy found")
        return False
    
    def remove_policy(self):
        """Remove the force-install policy."""
        policy_key = r'SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist'
        
        for hive, name in [(winreg.HKEY_LOCAL_MACHINE, "HKLM"), (winreg.HKEY_CURRENT_USER, "HKCU")]:
            try:
                with winreg.OpenKey(hive, policy_key, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, '1')
                    print(f"Policy removed from {name}")
                    return True
            except FileNotFoundError:
                continue
            except Exception as e:
                print(f"Could not remove from {name}: {e}")
        
        return False

def main():
    """Configure Edge policy with example values."""
    manager = EdgePolicyManager()
    
    # Example values - replace with actual ones
    extension_id = "abcdefghijklmnopqrstuvwxyz123456"  # 32-character ID from edge://extensions
    updates_url = "https://your-domain.com/focusguard/updates.xml"
    
    print("Focus Guard Edge Policy Configuration")
    print("=" * 60)
    print("IMPORTANT: Replace these placeholder values:")
    print(f"Extension ID: {extension_id}")
    print(f"Updates URL: {updates_url}")
    print()
    
    # Check if we have real values
    if extension_id == "abcdefghijklmnopqrstuvwxyz123456":
        print("STEP 1: Get Extension ID")
        print("1. Open Edge and go to: edge://extensions/")
        print("2. Enable 'Developer mode'")
        print("3. Click 'Load unpacked'")
        print("4. Select: C:\\Users\\prasun_agarwal\\focus_guard\\focus_guard\\core\\browser\\extension\\webextension_mv3")
        print("5. Copy the Extension ID (32-character string)")
        print()
        
        real_id = input("Enter the real Extension ID (or press Enter to use placeholder): ").strip()
        if real_id and len(real_id) == 32:
            extension_id = real_id
    
    if updates_url == "https://your-domain.com/focusguard/updates.xml":
        print("STEP 2: Set Updates URL")
        real_url = input("Enter the real updates.xml URL (or press Enter to use placeholder): ").strip()
        if real_url and real_url.startswith("https://"):
            updates_url = real_url
    
    print()
    print("Creating policy...")
    success = manager.create_force_install_policy(extension_id, updates_url)
    
    if success:
        print()
        print("NEXT STEPS:")
        print("1. Close all Edge windows")
        print("2. Open Edge and wait 1-2 minutes")
        print("3. Check edge://policy to verify policy is active")
        print("4. Check edge://extensions to see extension installed")
        print("5. Extension should appear automatically (users cannot remove it)")
        
        print()
        print("VERIFICATION:")
        manager.verify_policy()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
