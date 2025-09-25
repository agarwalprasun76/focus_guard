"""
Enhanced installation script with robust browser extension protection.

This script provides a Python-based installation process that includes:
- Robust extension installation with retry logic
- Windows admin-level file protection
- Extension verification and auto-repair
- Comprehensive installation reporting
"""

import os
import sys
import platform
import subprocess
import logging
from pathlib import Path

# Add the focus_guard package to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from focus_guard.core.browser.extension.installer import ExtensionInstaller
from focus_guard.core.browser.extension.robust_installer import ExtensionInstallationService
from focus_guard.core.browser.extension.windows_admin_utils import WindowsAdminUtils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_admin_privileges():
    """Check if running with admin privileges on Windows."""
    if platform.system() == "Windows":
        return WindowsAdminUtils.is_admin()
    return True  # Non-Windows systems don't need admin for this


def install_extensions_robust():
    """Install browser extensions with robust protection."""
    print("=" * 60)
    print("Focus Guard Robust Extension Installation")
    print("=" * 60)
    
    # Check admin privileges
    is_admin = check_admin_privileges()
    if platform.system() == "Windows":
        print(f"Admin privileges: {'Yes' if is_admin else 'No'}")
        if not is_admin:
            print("WARNING: Running without admin privileges.")
            print("File protection features will be limited.")
            print("For full protection, run as administrator.")
        print()
    
    try:
        # Initialize robust installer
        print("Initializing robust extension installer...")
        installer = ExtensionInstaller(use_robust_installer=True)
        
        # Install with full protection
        print("Installing extensions with protection...")
        result = installer.install_with_protection()
        
        if 'error' not in result:
            print("\nExtension installation completed!")
            print("\nProtection Status:")
            for key, value in result['protection'].items():
                status = "APPLIED" if value else "FAILED"
                print(f"  {status}: {key}")
            
            # Show detailed installation report
            print("\n" + "=" * 60)
            print("INSTALLATION REPORT")
            print("=" * 60)
            report = installer.get_installation_status_report()
            print(report)
            
            # Show verification results
            if installer._installation_service:
                verification_results = installer._installation_service.verify_all_extensions()
                print("\nExtension Verification:")
                for browser_type, verified in verification_results.items():
                    status = "CONNECTED" if verified else "NOT CONNECTED"
                    print(f"  {status}: {browser_type.name}")
            
        else:
            print(f"\nRobust installation failed: {result['error']}")
            print("Falling back to standard installation...")
            
            # Fall back to standard installation
            results = installer.install_for_detected_browsers()
            print("\nStandard Installation Results:")
            for browser, result in results.items():
                status = "SUCCESS" if result['success'] else "FAILED"
                guide = " (User guide launched)" if result.get('user_guide_launched') else ""
                print(f"  {status}: {browser.name}{guide}")
        
        return True
        
    except Exception as e:
        print(f"\nError during extension installation: {e}")
        logger.error(f"Extension installation failed: {e}")
        return False


def verify_and_repair_extensions():
    """Verify and repair extensions if needed."""
    print("\n" + "=" * 60)
    print("Extension Verification and Repair")
    print("=" * 60)
    
    try:
        installer = ExtensionInstaller(use_robust_installer=True)
        
        # Verify and repair
        repair_results = installer.verify_and_repair_extensions()
        
        print("Repair Results:")
        for browser_type, success in repair_results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"  {status}: {browser_type.name}")
        
        return all(repair_results.values())
        
    except Exception as e:
        print(f"Error during verification/repair: {e}")
        return False


def main():
    """Main installation function."""
    print("Focus Guard Enhanced Installation with Robust Extensions")
    print("=" * 60)
    print()
    
    # Step 1: Install extensions with protection
    print("Step 1: Installing browser extensions with robust protection")
    extension_success = install_extensions_robust()
    
    if not extension_success:
        print("\nExtension installation encountered issues.")
        
        # Offer repair option
        response = input("\nWould you like to attempt verification and repair? (y/n): ")
        if response.lower() in ['y', 'yes']:
            repair_success = verify_and_repair_extensions()
            if repair_success:
                print("Extension repair completed successfully!")
            else:
                print("Extension repair encountered issues.")
    
    # Step 2: Show final status
    print("\n" + "=" * 60)
    print("FINAL STATUS")
    print("=" * 60)
    
    try:
        installer = ExtensionInstaller(use_robust_installer=True)
        final_report = installer.get_installation_status_report()
        print(final_report)
    except Exception as e:
        print(f"Error generating final report: {e}")
    
    print("\n" + "=" * 60)
    print("Installation Complete!")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("1. Start Focus Guard using the CLI or system tray")
    print("2. Configure your blocking preferences")
    print("3. Test browser extension functionality")
    
    if platform.system() == "Windows" and not check_admin_privileges():
        print("\nNote: For maximum security, consider running the installer")
        print("as administrator to enable full file protection features.")
    
    return extension_success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        logger.error(f"Installation failed with unexpected error: {e}")
        sys.exit(1)
