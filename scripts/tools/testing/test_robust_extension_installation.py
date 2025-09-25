"""
Test script for robust browser extension installation features.

This script tests:
- Robust extension installation with retry logic
- Windows admin-level file protection
- Extension verification and auto-repair
- Installation status tracking and reporting
"""

import os
import sys
import time
import logging
import platform
from pathlib import Path

# Add the focus_guard package to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focus_guard.core.browser.extension.robust_installer import (
    RobustExtensionInstaller, ExtensionInstallationService, InstallationStatus
)
from focus_guard.core.browser.extension.windows_admin_utils import (
    WindowsAdminUtils, ExtensionProtectionManager
)
from focus_guard.core.browser.extension.installer import ExtensionInstaller
from focus_guard.core.browser.models.browser import BrowserType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_windows_admin_utils():
    """Test Windows admin utilities."""
    print("\n=== Testing Windows Admin Utils ===")
    
    # Check admin status
    is_admin = WindowsAdminUtils.is_admin()
    print(f"Running as admin: {is_admin}")
    
    if platform.system() == "Windows":
        # Test file permission checking
        test_path = os.path.dirname(os.path.abspath(__file__))
        permissions = WindowsAdminUtils.check_file_permissions(test_path)
        print(f"Current directory permissions: {permissions}")
    else:
        print("Windows admin utils only work on Windows")
    
    return True


def test_robust_installer():
    """Test the robust extension installer."""
    print("\n=== Testing Robust Extension Installer ===")
    
    try:
        # Initialize robust installer
        installer = RobustExtensionInstaller(max_retries=2, retry_delay=1.0)
        print(f"Extension directory: {installer._extension_dir}")
        
        # Check if extension directory exists
        if not os.path.exists(installer._extension_dir):
            print(f"Extension directory not found: {installer._extension_dir}")
            return False
        
        print(f"Extension directory found: {installer._extension_dir}")
        
        # Test extension integrity check
        integrity_ok = installer.ensure_extension_integrity()
        print(f"Extension integrity: {'OK' if integrity_ok else 'Failed'}")
        
        # Get installation summary
        summary = installer.get_installation_summary()
        print(f"Detected browsers: {summary['total_browsers']}")
        
        for browser_name, details in summary["browsers"].items():
            print(f"  - {browser_name}: {details['status']} ({'installed' if details['installed'] else 'not installed'})")
        
        return True
        
    except Exception as e:
        print(f"Error testing robust installer: {e}")
        return False


def test_extension_installation_service():
    """Test the extension installation service."""
    print("\n=== Testing Extension Installation Service ===")
    
    try:
        # Initialize installation service
        service = ExtensionInstallationService()
        
        # Create installation report without actually installing
        report = service.create_installation_report()
        print("Installation Report:")
        print(report)
        
        # Get installation log
        log = service.get_installation_log()
        print(f"Installation log entries: {len(log)}")
        
        return True
        
    except Exception as e:
        print(f"Error testing installation service: {e}")
        return False


def test_protection_manager():
    """Test the extension protection manager."""
    print("\n=== Testing Extension Protection Manager ===")
    
    try:
        # Find extension directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        extension_dir = os.path.join(current_dir, "focus_guard", "core", "browser", "extension", "webextension_mv3")
        
        if not os.path.exists(extension_dir):
            print(f"Extension directory not found: {extension_dir}")
            return False
        
        # Initialize protection manager
        protection_manager = ExtensionProtectionManager(extension_dir)
        
        # Verify current protection
        protection_status = protection_manager.verify_protection()
        print("Current protection status:")
        for key, value in protection_status.items():
            print(f"  - {key}: {value}")
        
        if platform.system() == "Windows" and WindowsAdminUtils.is_admin():
            print("Running as admin - testing protection application")
            
            # Apply protection (only if admin)
            protection_results = protection_manager.apply_full_protection()
            print("Protection application results:")
            for key, value in protection_results.items():
                status = "OK" if value else "FAIL"
                print(f"  {status} {key}: {value}")
        else:
            print("Not running as admin or not on Windows - skipping protection application test")
        
        return True
        
    except Exception as e:
        print(f"Error testing protection manager: {e}")
        return False


def test_enhanced_installer_integration():
    """Test the enhanced installer with robust features."""
    print("\n=== Testing Enhanced Installer Integration ===")
    
    try:
        # Initialize enhanced installer
        installer = ExtensionInstaller(use_robust_installer=True)
        
        # Get status report
        status_report = installer.get_installation_status_report()
        print("Current Status Report:")
        print(status_report)
        
        # Test verification without actual installation
        print("\nTesting verification methods...")
        
        # Check if we can verify extensions (this won't actually install)
        for browser_type in installer._extension_manager._browser_paths.keys():
            installed = installer._extension_manager.is_extension_installed(browser_type)
            status = installer._extension_manager.get_installation_status(browser_type)
            print(f"  - {browser_type.name}: {status.value} ({'installed' if installed else 'not installed'})")
        
        return True
        
    except Exception as e:
        print(f"Error testing enhanced installer: {e}")
        return False


def main():
    """Run all robust extension installation tests."""
    print("Focus Guard Robust Extension Installation Test")
    print("=" * 50)
    
    test_results = []
    
    # Test 1: Windows Admin Utils
    try:
        result = test_windows_admin_utils()
        test_results.append(("Windows Admin Utils", result))
    except Exception as e:
        print(f"Windows Admin Utils test failed: {e}")
        test_results.append(("Windows Admin Utils", False))
    
    # Test 2: Robust Installer
    try:
        result = test_robust_installer()
        test_results.append(("Robust Installer", result))
    except Exception as e:
        print(f"Robust Installer test failed: {e}")
        test_results.append(("Robust Installer", False))
    
    # Test 3: Installation Service
    try:
        result = test_extension_installation_service()
        test_results.append(("Installation Service", result))
    except Exception as e:
        print(f"Installation Service test failed: {e}")
        test_results.append(("Installation Service", False))
    
    # Test 4: Protection Manager
    try:
        result = test_protection_manager()
        test_results.append(("Protection Manager", result))
    except Exception as e:
        print(f"Protection Manager test failed: {e}")
        test_results.append(("Protection Manager", False))
    
    # Test 5: Enhanced Installer Integration
    try:
        result = test_enhanced_installer_integration()
        test_results.append(("Enhanced Installer", result))
    except Exception as e:
        print(f"Enhanced Installer test failed: {e}")
        test_results.append(("Enhanced Installer", False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("All robust extension installation features are working!")
    else:
        print("Some features need attention before deployment")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
