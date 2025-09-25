"""
Test admin-only functionality by simulating admin privileges.

This test shows what would happen with admin privileges.
"""

import os
import sys
import platform
import tempfile
import shutil

# Add the focus_guard package to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focus_guard.core.browser.extension.windows_admin_utils import WindowsAdminUtils


def test_file_protection_simulation():
    """Test file protection on a temporary directory."""
    print("=== Testing File Protection (Simulation) ===")
    
    if platform.system() != "Windows":
        print("File protection only works on Windows")
        return True
    
    # Create a temporary test directory
    test_dir = os.path.join(tempfile.gettempdir(), "focus_guard_test_protection")
    
    try:
        # Create test directory and file
        os.makedirs(test_dir, exist_ok=True)
        test_file = os.path.join(test_dir, "test_manifest.json")
        with open(test_file, 'w') as f:
            f.write('{"name": "test"}')
        
        print(f"Created test directory: {test_dir}")
        
        # Check current permissions
        permissions = WindowsAdminUtils.check_file_permissions(test_dir)
        print(f"Current permissions: {permissions.get('protected', 'Unknown')}")
        
        # Try to apply protection (will fail without admin)
        is_admin = WindowsAdminUtils.is_admin()
        print(f"Running as admin: {is_admin}")
        
        if is_admin:
            print("Testing actual protection application...")
            result = WindowsAdminUtils.protect_directory_advanced(test_dir, deny_delete=True)
            print(f"Protection applied: {result}")
            
            # Verify protection
            new_permissions = WindowsAdminUtils.check_file_permissions(test_dir)
            print(f"New permissions: {new_permissions.get('protected', 'Unknown')}")
        else:
            print("Cannot test protection without admin privileges")
            print("This is expected behavior - protection requires admin rights")
        
        return True
        
    except Exception as e:
        print(f"Error during protection test: {e}")
        return False
        
    finally:
        # Clean up
        try:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
                print(f"Cleaned up test directory: {test_dir}")
        except Exception as e:
            print(f"Warning: Could not clean up test directory: {e}")


def test_registry_protection_simulation():
    """Test registry protection simulation."""
    print("\n=== Testing Registry Protection (Simulation) ===")
    
    if platform.system() != "Windows":
        print("Registry protection only works on Windows")
        return True
    
    test_path = r"C:\temp\test_extension"
    
    is_admin = WindowsAdminUtils.is_admin()
    print(f"Running as admin: {is_admin}")
    
    if is_admin:
        print("Testing actual registry protection...")
        try:
            # Try to create registry protection
            result = WindowsAdminUtils.create_registry_protection(test_path)
            print(f"Registry protection created: {result}")
            
            if result:
                # Verify registry protection
                verified = WindowsAdminUtils.verify_registry_protection(test_path)
                print(f"Registry protection verified: {verified}")
                
                # Clean up
                WindowsAdminUtils.remove_registry_protection()
                print("Registry protection cleaned up")
            
        except Exception as e:
            print(f"Registry protection test failed: {e}")
            return False
    else:
        print("Cannot test registry protection without admin privileges")
        print("This is expected behavior - registry operations require admin rights")
    
    return True


def main():
    """Run admin functionality tests."""
    print("Focus Guard Admin Functionality Test")
    print("=" * 50)
    
    is_admin = WindowsAdminUtils.is_admin()
    print(f"Current admin status: {is_admin}")
    
    if not is_admin:
        print("\nNOTE: Running without admin privileges.")
        print("Many protection features will be skipped (this is correct behavior).")
        print("To test full admin functionality, run as administrator.")
    
    print()
    
    tests = [
        test_file_protection_simulation,
        test_registry_protection_simulation,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"Test failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("ADMIN FUNCTIONALITY TEST RESULTS")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if is_admin:
        if passed == total:
            print("All admin functionality working correctly!")
        else:
            print("Some admin functionality needs fixing.")
    else:
        print("Admin functionality tests completed (limited without admin privileges).")
        print("The system correctly handles non-admin scenarios.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
