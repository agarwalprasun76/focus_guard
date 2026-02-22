"""
Manual Edge policy creation using REG commands (bypasses Python registry permissions).
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

def create_edge_policy_manual():
    """Create Edge policy using REG command."""
    extension_id = CHROME_EXTENSION_ID
    updates_url = "https://your-domain.com/focusguard/updates.xml"
    
    print("Manual Edge Policy Creation")
    print("=" * 40)
    print(f"Extension ID: {extension_id}")
    print(f"Updates URL: {updates_url}")
    print()
    
    # Create registry commands
    policy_key = r"HKCU\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist"
    policy_value = f"{extension_id};{updates_url}"
    
    # REG commands
    create_key_cmd = f'REG ADD "{policy_key}" /f'
    set_value_cmd = f'REG ADD "{policy_key}" /v "1" /t REG_SZ /d "{policy_value}" /f'
    
    print("Creating registry policy...")
    print(f"Key: {policy_key}")
    print(f"Value: {policy_value}")
    print()
    
    try:
        # Create the key
        result1 = subprocess.run(create_key_cmd, shell=True, capture_output=True, text=True)
        if result1.returncode == 0:
            print("✓ Registry key created")
        else:
            print(f"Key creation result: {result1.stderr}")
        
        # Set the value
        result2 = subprocess.run(set_value_cmd, shell=True, capture_output=True, text=True)
        if result2.returncode == 0:
            print("✓ Policy value set")
            print()
            print("SUCCESS: Edge policy created!")
            
            # Verify
            verify_cmd = f'REG QUERY "{policy_key}" /v "1"'
            verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
            if verify_result.returncode == 0:
                print("✓ Policy verified in registry")
                print()
                print("VERIFICATION:")
                print(verify_result.stdout)
            
            return True
        else:
            print(f"Value setting failed: {result2.stderr}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def print_instructions():
    """Print next steps."""
    print("=" * 50)
    print("NEXT STEPS")
    print("=" * 50)
    print("1. Close ALL Microsoft Edge windows")
    print("2. Wait 10 seconds")
    print("3. Open Microsoft Edge")
    print("4. Wait 1-2 minutes for policy to activate")
    print("5. Go to: edge://policy")
    print("6. Look for 'ExtensionInstallForcelist' policy")
    print("7. Go to: edge://extensions")
    print("8. Extension should appear automatically")
    print()
    print("If extension doesn't appear:")
    print("- Check edge://policy for active policies")
    print("- Restart Edge completely")
    print("- Wait longer (policies can take time)")

def main():
    success = create_edge_policy_manual()
    
    if success:
        print_instructions()
        return True
    else:
        print()
        print("ALTERNATIVE: Run PowerShell as Administrator")
        print("powershell -Command \"Start-Process PowerShell -Verb RunAs\"")
        print("Then run: .\\scripts\\install_edge_policy.ps1")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
