"""
Test Edge policy configuration with the real extension ID.
"""

import os
import sys
import winreg
from pathlib import Path

# Ensure focus_guard package is importable when run as a standalone script
_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from focus_guard.core.extension_constants import CHROME_EXTENSION_ID

def test_edge_policy():
    """Test Edge policy configuration."""
    extension_id = CHROME_EXTENSION_ID
    updates_url = "https://your-domain.com/focusguard/updates.xml"
    
    print("Testing Edge Policy Configuration")
    print("=" * 50)
    print(f"Extension ID: {extension_id}")
    print(f"Updates URL: {updates_url}")
    print()
    
    # Create policy
    policy_key = r'SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist'
    policy_value = f'{extension_id};{updates_url}'
    
    try:
        # Try machine-wide first
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, policy_key) as key:
            winreg.SetValueEx(key, '1', 0, winreg.REG_SZ, policy_value)
        print("SUCCESS: Machine-wide policy created (HKLM)")
        registry_location = "HKLM"
    except PermissionError:
        print("ADMIN REQUIRED: Trying user-specific policy...")
        try:
            # Fallback to user-specific
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, policy_key) as key:
                winreg.SetValueEx(key, '1', 0, winreg.REG_SZ, policy_value)
            print("SUCCESS: User-specific policy created (HKCU)")
            registry_location = "HKCU"
        except Exception as e:
            print(f"FAILED: Could not create policy: {e}")
            return False
    except Exception as e:
        print(f"FAILED: Registry error: {e}")
        return False
    
    # Verify policy
    print(f"\nPolicy created in {registry_location}:")
    print(f"Key: {policy_key}")
    print(f"Value: {policy_value}")
    
    print("\nNext steps:")
    print("1. Close all Edge windows")
    print("2. Open Edge and wait 1-2 minutes")
    print("3. Go to edge://policy to verify policy is active")
    print("4. Go to edge://extensions to see extension installed")
    print("5. Extension should appear automatically")
    
    return True

if __name__ == "__main__":
    success = test_edge_policy()
    sys.exit(0 if success else 1)
