#!/usr/bin/env python
"""
Focus Guard Extension Installation Demo

This script provides a command-line interface for manually testing the installation
of the Focus Guard browser extension across different browsers. It's useful for
demonstration and manual testing purposes.

For automated tests, see:
- test_extension_installer.py
- test_extension_manager.py

Usage:
    python scripts/demo_extension_install.py [--browser {chrome|edge|all}] [--extension-dir PATH] [--verify] [--verbose]

Example:
    # Install for all detected browsers
    python scripts/demo_extension_install.py --verify --verbose
    
    # Install for Chrome only
    python scripts/demo_extension_install.py --browser chrome --verify
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path to ensure imports work
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from focus_guard.core.browser.extension.installer import ExtensionInstaller
from focus_guard.core.browser.models.browser import BrowserType


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Focus Guard Extension Installation Demo"
    )
    
    parser.add_argument(
        "--browser",
        choices=["chrome", "edge", "all"],
        default="all",
        help="Browser to install extension for (default: %(default)s)"
    )
    
    parser.add_argument(
        "--extension-dir",
        help="Directory containing extension files (auto-detected if not specified)"
    )
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify extension installation and connection"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def print_installation_status(results: Dict[BrowserType, bool]):
    """Print installation status in a formatted way."""
    print("\n" + "=" * 50)
    print("EXTENSION INSTALLATION RESULTS")
    print("=" * 50)
    
    for browser_type, success in results.items():
        status = "[SUCCESS]" if success else "[FAILED]"
        print(f"{browser_type.name}: {status}")
    
    print("=" * 50 + "\n")


def main():
    """Main entry point for the demo script."""
    args = parse_arguments()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting Focus Guard Extension Installation Demo...")
    
    # Use the correct extension directory if not specified
    if not args.extension_dir:
        # Try to find the extension directory
        possible_paths = [
            os.path.join(project_root, 'core', 'browser', 'extension', 'webextension_mv3'),
            os.path.join(project_root, 'webextension_mv3'),
            os.path.join(project_root, 'core', 'browser_detection', 'webextension_mv3'),
            os.path.join(project_root, 'core', 'browser_detection', 'webextension_mv2'),
            os.path.join(project_root, 'core', 'browser_detection', 'browser_extension', 'focus_guard_extension')
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.path.exists(os.path.join(path, 'manifest.json')):
                args.extension_dir = path
                logger.info(f"Found extension directory at: {path}")
                break
    
    # Create extension installer
    installer = ExtensionInstaller(args.extension_dir)
    
    # Get extension directory
    extension_dir = installer.get_extension_dir()
    logger.info(f"Using extension directory: {extension_dir}")
    
    # Check if extension directory exists
    if not os.path.exists(extension_dir):
        logger.error(f"Extension directory not found: {extension_dir}")
        logger.info("Please specify the correct path using --extension-dir")
        return 1
    
    # Check if manifest.json exists
    manifest_path = os.path.join(extension_dir, 'manifest.json')
    if not os.path.exists(manifest_path):
        logger.error(f"Manifest file not found: {manifest_path}")
        return 1
    
    # Install extension for specified browser(s)
    results = {}
    
    if args.browser == "all":
        logger.info("Installing extension for all detected browsers...")
        results = installer.install_for_detected_browsers()
    else:
        browser_type = BrowserType[args.browser.upper()]
        logger.info(f"Installing extension for {browser_type}...")
        success = installer.install_extension(browser_type)
        results[browser_type] = success
    
    # Print installation status
    print_installation_status(results)
    
    # Verify extension installation if requested
    if args.verify:
        logger.info("Verifying extension installation...")
        verification_results = {}
        
        for browser_type in results.keys():
            if results[browser_type]:
                logger.info(f"Verifying extension for {browser_type}...")
                verified = installer.verify_installation(browser_type)
                verification_results[browser_type] = verified
                
                if verified:
                    logger.info(f"Extension verified for {browser_type}")
                else:
                    logger.warning(f"Extension verification failed for {browser_type}")
        
        print("\n" + "=" * 50)
        print("EXTENSION VERIFICATION RESULTS")
        print("=" * 50)
        
        for browser_type, success in verification_results.items():
            status = "✅ CONNECTED" if success else "❌ NOT CONNECTED"
            print(f"{browser_type.name}: {status}")
        
        print("=" * 50 + "\n")
    
    # Stop tab server
    installer.stop_tab_server()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        sys.exit(1)
