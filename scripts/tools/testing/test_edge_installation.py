"""
Test Edge browser extension installation specifically.
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


def test_edge_specific_installation():
    """Test Edge browser extension installation specifically."""
    print("=== Testing Edge Browser Extension Installation ===")
    
    installer = RobustExtensionInstaller()
    
    # Check if Edge is detected
    if BrowserType.EDGE not in installer._browser_paths:
        print("ERROR: Edge browser not detected")
        return False
    
    edge_path = installer._browser_paths[BrowserType.EDGE]
    print(f"Edge detected at: {edge_path}")
    print(f"Edge executable exists: {os.path.exists(edge_path)}")
    
    # Check Edge extensions directory
    extensions_dir = installer._get_browser_extensions_dir(BrowserType.EDGE)
    print(f"Edge extensions directory: {extensions_dir}")
    print(f"Extensions directory exists: {os.path.exists(extensions_dir)}")
    
    if os.path.exists(extensions_dir):
        try:
            contents = os.listdir(extensions_dir)
            print(f"Current extensions count: {len(contents)}")
            
            # Look for Focus Guard extension
            focus_guard_found = False
            for item in contents:
                item_path = os.path.join(extensions_dir, item)
                if os.path.isdir(item_path):
                    # Check if this might be our extension
                    manifest_path = os.path.join(item_path, "manifest.json")
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, 'r') as f:
                                content = f.read()
                                if "Focus Guard" in content or "focus_guard" in content:
                                    print(f"Found Focus Guard extension in: {item}")
                                    focus_guard_found = True
                        except:
                            pass
            
            if not focus_guard_found:
                print("Focus Guard extension not found in Edge extensions directory")
            
        except Exception as e:
            print(f"Error reading extensions directory: {e}")
    
    # Test direct installation
    print("\n--- Testing Direct Edge Installation ---")
    try:
        success = installer._extension_manager.install_extension(BrowserType.EDGE)
        print(f"Direct installation result: {success}")
        
        if success:
            print("Edge should have launched with the extension")
            print("Check if Edge opened with developer mode extension loaded")
        
    except Exception as e:
        print(f"Direct installation error: {e}")
        return False
    
    # Test robust installation
    print("\n--- Testing Robust Edge Installation ---")
    try:
        result = installer.install_extension_robust(BrowserType.EDGE)
        print(f"Robust installation result:")
        print(f"  Success: {result.success}")
        print(f"  Status: {result.status}")
        print(f"  Attempts: {result.attempts}")
        print(f"  Error: {getattr(result, 'error_message', 'None')}")
        
        return result.success
        
    except Exception as e:
        print(f"Robust installation error: {e}")
        return False


def test_edge_manual_check():
    """Manual check for Edge extension installation."""
    print("\n=== Manual Edge Extension Check ===")
    
    installer = RobustExtensionInstaller()
    
    # Check if extension is detected as installed
    installed = installer.is_extension_installed(BrowserType.EDGE)
    print(f"Extension detected as installed: {installed}")
    
    # Check extension status
    status = installer.get_installation_status(BrowserType.EDGE)
    print(f"Installation status: {status.value}")
    
    # Check Edge extensions directory for our extension
    extensions_dir = installer._get_browser_extensions_dir(BrowserType.EDGE)
    if os.path.exists(extensions_dir):
        print(f"\nScanning Edge extensions directory: {extensions_dir}")
        
        try:
            for item in os.listdir(extensions_dir):
                item_path = os.path.join(extensions_dir, item)
                if os.path.isdir(item_path):
                    manifest_path = os.path.join(item_path, "manifest.json")
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, 'r') as f:
                                content = f.read()
                                if "Focus Guard" in content:
                                    print(f"  ✅ Found Focus Guard extension: {item}")
                                    return True
                        except:
                            pass
            
            print("  ❌ Focus Guard extension not found in Edge extensions")
            
        except Exception as e:
            print(f"Error scanning extensions: {e}")
    
    return False


def main():
    """Run Edge-specific installation tests."""
    print("Focus Guard - Edge Browser Extension Test")
    print("=" * 50)
    
    tests = [
        ("Edge Installation Test", test_edge_specific_installation),
        ("Edge Manual Check", test_edge_manual_check),
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
    print("EDGE EXTENSION TEST RESULTS")
    print("=" * 50)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {status}: {test_name}")
    
    # Instructions
    print("\n" + "=" * 50)
    print("MANUAL VERIFICATION STEPS")
    print("=" * 50)
    print("1. Open Microsoft Edge")
    print("2. Go to: edge://extensions/")
    print("3. Enable 'Developer mode' (toggle in left sidebar)")
    print("4. Look for 'Focus Guard' extension")
    print("5. If not found, the installation didn't work properly")
    
    return any(result for _, result in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
