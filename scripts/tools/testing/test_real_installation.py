"""
Test the actual extension installation functionality.
"""

import os
import sys
import logging
import time

# Add the focus_guard package to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focus_guard.core.browser.extension.robust_installer import RobustExtensionInstaller
from focus_guard.core.browser.models.browser import BrowserType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_tab_server_requirement():
    """Test if tab server is actually required and running."""
    print("=== Testing Tab Server Requirement ===")
    
    installer = RobustExtensionInstaller()
    
    # Check if tab server is running
    tab_server_running = installer.ensure_tab_server_running()
    print(f"Tab server running: {tab_server_running}")
    
    if not tab_server_running:
        print("ERROR: Tab server is not running - this is why installation fails!")
        print("The system requires the tab server to be running for extension installation.")
        return False
    
    return True


def test_actual_installation_attempt():
    """Test actual installation attempt with detailed logging."""
    print("\n=== Testing Actual Installation Attempt ===")
    
    installer = RobustExtensionInstaller()
    
    # Get first detected browser
    if not installer._browser_paths:
        print("ERROR: No browsers detected")
        return False
    
    browser_type = list(installer._browser_paths.keys())[0]
    print(f"Testing installation for: {browser_type.name}")
    
    # Try installation with detailed logging
    try:
        result = installer.install_extension_robust(browser_type)
        print(f"Installation result: {result}")
        print(f"  Success: {result.success}")
        print(f"  Status: {result.status}")
        print(f"  Attempts: {result.attempts}")
        print(f"  Protection Applied: {result.protection_applied}")
        
        return result.success
        
    except Exception as e:
        print(f"Installation failed with exception: {e}")
        return False


def test_browser_extensions_directory():
    """Test if browser extensions directories exist."""
    print("\n=== Testing Browser Extensions Directories ===")
    
    installer = RobustExtensionInstaller()
    
    for browser_type in installer._browser_paths.keys():
        extensions_dir = installer._get_browser_extensions_dir(browser_type)
        exists = os.path.exists(extensions_dir) if extensions_dir else False
        
        print(f"{browser_type.name}:")
        print(f"  Extensions dir: {extensions_dir}")
        print(f"  Exists: {exists}")
        
        if exists:
            # List contents
            try:
                contents = os.listdir(extensions_dir)
                print(f"  Contains {len(contents)} items")
            except Exception as e:
                print(f"  Error reading directory: {e}")
    
    return True


def test_extension_manager_directly():
    """Test the underlying extension manager directly."""
    print("\n=== Testing Extension Manager Directly ===")
    
    installer = RobustExtensionInstaller()
    
    for browser_type in installer._browser_paths.keys():
        print(f"Testing {browser_type.name}:")
        
        # Check if extension is installed
        installed = installer._extension_manager.is_extension_installed(browser_type)
        print(f"  Currently installed: {installed}")
        
        # Try direct installation
        try:
            success = installer._extension_manager.install_extension(browser_type)
            print(f"  Direct install result: {success}")
        except Exception as e:
            print(f"  Direct install error: {e}")
    
    return True


def main():
    """Run real installation tests."""
    print("Focus Guard - REAL Installation Test")
    print("=" * 50)
    
    tests = [
        ("Tab Server Requirement", test_tab_server_requirement),
        ("Browser Extensions Directory", test_browser_extensions_directory),
        ("Extension Manager Direct", test_extension_manager_directly),
        ("Actual Installation Attempt", test_actual_installation_attempt),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print()
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("REAL INSTALLATION TEST RESULTS")
    print("=" * 50)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {status}: {test_name}")
    
    # Diagnosis
    print("\n" + "=" * 50)
    print("DIAGNOSIS")
    print("=" * 50)
    
    installer = RobustExtensionInstaller()
    tab_server_running = installer.ensure_tab_server_running()
    
    if not tab_server_running:
        print("ROOT CAUSE: Tab server is not running")
        print("SOLUTION: Start the tab server before attempting installation")
        print("COMMAND: python scripts/dev/start_tab_server.py")
    else:
        print("Tab server is running - other issues may exist")
    
    return all(result for _, result in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
