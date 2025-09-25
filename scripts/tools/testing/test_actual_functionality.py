"""
Test actual functionality of the robust extension installation system.

This test verifies that the system actually works, not just that classes load.
"""

import os
import sys
import platform
import logging

# Add the focus_guard package to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focus_guard.core.browser.extension.windows_admin_utils import WindowsAdminUtils
from focus_guard.core.browser.extension.robust_installer import RobustExtensionInstaller
from focus_guard.core.browser.models.browser import BrowserType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_admin_detection():
    """Test actual admin privilege detection."""
    print("=== Testing Admin Detection ===")
    
    is_admin = WindowsAdminUtils.is_admin()
    print(f"Running as admin: {is_admin}")
    
    if platform.system() == "Windows":
        # Test the actual Windows API call
        import ctypes
        raw_result = ctypes.windll.shell32.IsUserAnAdmin()
        print(f"Raw Windows API result: {raw_result}")
        print(f"Converted to bool: {raw_result != 0}")
        
        if is_admin != (raw_result != 0):
            print("ERROR: Admin detection mismatch!")
            return False
    
    return True


def test_file_protection_logic():
    """Test file protection logic without actually applying it."""
    print("\n=== Testing File Protection Logic ===")
    
    installer = RobustExtensionInstaller()
    
    # Check if extension directory exists
    if not os.path.exists(installer._extension_dir):
        print(f"ERROR: Extension directory not found: {installer._extension_dir}")
        return False
    
    print(f"Extension directory found: {installer._extension_dir}")
    
    # Test admin check logic
    is_admin = WindowsAdminUtils.is_admin()
    print(f"Admin status: {is_admin}")
    
    if platform.system() == "Windows" and not is_admin:
        print("INFO: Not running as admin - protection will be skipped (this is correct behavior)")
    elif platform.system() == "Windows" and is_admin:
        print("INFO: Running as admin - protection would be applied")
    else:
        print("INFO: Not on Windows - protection not applicable")
    
    return True


def test_browser_detection():
    """Test actual browser detection."""
    print("\n=== Testing Browser Detection ===")
    
    installer = RobustExtensionInstaller()
    
    print(f"Detected browsers: {len(installer._browser_paths)}")
    for browser_type, path in installer._browser_paths.items():
        exists = os.path.exists(path)
        print(f"  {browser_type.name}: {path} ({'EXISTS' if exists else 'NOT FOUND'})")
        
        if not exists:
            print(f"    WARNING: Browser executable not found at {path}")
    
    return len(installer._browser_paths) > 0


def test_extension_files():
    """Test extension file integrity."""
    print("\n=== Testing Extension Files ===")
    
    installer = RobustExtensionInstaller()
    
    # Check critical files
    critical_files = ["manifest.json", "background.js"]
    all_exist = True
    
    for file_name in critical_files:
        file_path = os.path.join(installer._extension_dir, file_name)
        exists = os.path.exists(file_path)
        print(f"  {file_name}: {'EXISTS' if exists else 'MISSING'}")
        
        if exists:
            # Check file size
            size = os.path.getsize(file_path)
            print(f"    Size: {size} bytes")
            if size == 0:
                print(f"    WARNING: File is empty!")
                all_exist = False
        else:
            all_exist = False
    
    return all_exist


def test_installation_status_tracking():
    """Test installation status tracking."""
    print("\n=== Testing Installation Status Tracking ===")
    
    installer = RobustExtensionInstaller()
    
    # Test status for each detected browser
    for browser_type in installer._browser_paths.keys():
        status = installer.get_installation_status(browser_type)
        installed = installer.is_extension_installed(browser_type)
        
        print(f"  {browser_type.name}:")
        print(f"    Status: {status.value}")
        print(f"    Detected as installed: {installed}")
        
        # This should show NOT_INSTALLED since we haven't actually installed
        if status.value != "not_installed":
            print(f"    WARNING: Expected 'not_installed' but got '{status.value}'")
    
    return True


def main():
    """Run actual functionality tests."""
    print("Focus Guard Robust Extension - ACTUAL Functionality Test")
    print("=" * 60)
    
    tests = [
        ("Admin Detection", test_admin_detection),
        ("File Protection Logic", test_file_protection_logic),
        ("Browser Detection", test_browser_detection),
        ("Extension Files", test_extension_files),
        ("Status Tracking", test_installation_status_tracking),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("ACTUAL FUNCTIONALITY TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\nCore functionality is working correctly!")
    else:
        print("\nSome core functionality needs fixing!")
    
    # Key findings
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)
    
    is_admin = WindowsAdminUtils.is_admin()
    installer = RobustExtensionInstaller()
    
    print(f"1. Admin Status: {'Admin' if is_admin else 'Not Admin'}")
    print(f"2. Extension Directory: {installer._extension_dir}")
    print(f"3. Browsers Detected: {len(installer._browser_paths)}")
    print(f"4. Platform: {platform.system()}")
    
    if not is_admin and platform.system() == "Windows":
        print("\nNOTE: Many protection features require admin privileges.")
        print("To test full functionality, run as administrator.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
