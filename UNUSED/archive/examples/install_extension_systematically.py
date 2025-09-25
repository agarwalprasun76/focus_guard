#!/usr/bin/env python
"""
Extension installation utility for Focus Guard.

This script provides a command-line interface for installing and verifying
the Focus Guard browser extension using the new programmatic installation approach.
"""

import os
import sys
import time
import logging
import argparse
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_v2.browser.extension.installer import ExtensionInstaller
from core_v2.browser.models.browser import BrowserType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Focus Guard Browser Extension Installer"
    )
    
    parser.add_argument(
        "--browser", "-b",
        choices=[b.name.lower() for b in BrowserType],
        help="Specific browser to install extension for"
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Install extension for all detected browsers"
    )
    
    parser.add_argument(
        "--verify", "-v",
        action="store_true",
        help="Verify extension installation and connection"
    )
    
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=30,
        help="Timeout in seconds for verification (default: 30)"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=5000,
        help="Port for tab server (default: 5000)"
    )
    
    return parser.parse_args()


def print_installation_status(results: Dict[BrowserType, bool]) -> None:
    """Print installation status for each browser.
    
    Args:
        results: Dictionary mapping browser types to installation success
    """
    print("\n" + "="*60)
    print("EXTENSION INSTALLATION RESULTS")
    print("="*60)
    
    for browser_type, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{browser_type.name:<10}: {status}")
    
    print("="*60 + "\n")


def print_verification_status(results: Dict[BrowserType, bool]) -> None:
    """Print verification status for each browser.
    
    Args:
        results: Dictionary mapping browser types to verification success
    """
    print("\n" + "="*60)
    print("EXTENSION VERIFICATION RESULTS")
    print("="*60)
    
    for browser_type, connected in results.items():
        status = "✅ CONNECTED" if connected else "❌ NOT CONNECTED"
        print(f"{browser_type.name:<10}: {status}")
    
    print("="*60 + "\n")


def print_next_steps() -> None:
    """Print next steps for the user."""
    print("\nNext steps:")
    print("1. Run the diagnostic script to verify tab detection:")
    print("   python examples/diagnose_tab_server.py")
    print("2. Run the integration test script:")
    print("   python examples/test_browser_integration.py")
    print("\nIf tabs are still not detected, check browser console for extension errors.")


def main():
    """Main function."""
    args = parse_arguments()
    
    logger.info("Starting Focus Guard Extension Installer...")
    
    # Create extension installer
    installer = ExtensionInstaller()
    
    # Get extension directory
    extension_dir = installer.get_extension_dir()
    logger.info(f"Using extension directory: {extension_dir}")
    
    # Ensure tab server is running
    logger.info(f"Starting tab server on port {args.port}...")
    if not installer.ensure_tab_server_running(port=args.port):
        logger.error("Failed to start tab server. Exiting.")
        return 1
    
    logger.info("Tab server started successfully")
    
    # Install extension(s)
    results = {}
    
    if args.browser:
        # Install for specific browser
        browser_type = BrowserType[args.browser.upper()]
        logger.info(f"Installing extension for {browser_type}...")
        success = installer.install_extension(browser_type)
        results[browser_type] = success
    elif args.all:
        # Install for all detected browsers
        logger.info("Installing extension for all detected browsers...")
        results = installer.install_for_detected_browsers()
    else:
        # Default: install for all detected browsers
        logger.info("No browser specified. Installing for all detected browsers...")
        results = installer.install_for_detected_browsers()
    
    # Print installation results
    print_installation_status(results)
    
    # Verify installation if requested
    if args.verify:
        logger.info(f"Verifying extension connections (timeout: {args.timeout}s)...")
        print("Waiting for extensions to connect to tab server...")
        
        # Wait for extensions to connect
        verification_results = {}
        for browser_type in results.keys():
            if results[browser_type]:  # Only verify browsers that were successfully installed
                logger.info(f"Verifying connection for {browser_type}...")
                connected = installer.verify_installation(browser_type, timeout=args.timeout)
                verification_results[browser_type] = connected
        
        # Print verification results
        print_verification_status(verification_results)
    
    # Print next steps
    print_next_steps()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
