#!/usr/bin/env python
"""
Native Messaging Host Validation Script

This script validates the native messaging host setup for different browsers.
It checks if the native messaging host is properly installed and functioning.
"""

import os
import sys
import json
import logging
import argparse
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add parent directory to path to allow importing native_host
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from native_host import NativeMessagingHostManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("validate_native_host")


def setup_argument_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="Validate native messaging host setup")
    
    parser.add_argument(
        "--browser",
        choices=["chrome", "edge", "firefox", "all"],
        default="all",
        help="Browser to validate (default: all)"
    )
    
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install native messaging host if not already installed"
    )
    
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall native messaging host before validation"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser


def validate_browser(browser: str, manager: NativeMessagingHostManager, install: bool = False) -> bool:
    """
    Validate native messaging host setup for a specific browser.
    
    Args:
        browser: Browser name
        manager: Native messaging host manager
        install: Whether to install the native messaging host if not already installed
        
    Returns:
        bool: True if validation passed, False otherwise
    """
    logger.info(f"Validating native messaging host for {browser}...")
    
    # Check if native host executable exists
    native_host_path = manager.get_native_host_executable()
    if not os.path.exists(native_host_path):
        logger.error(f"Native host executable not found at {native_host_path}")
        return False
    
    # Check if native host is installed
    is_installed = manager.is_installed(browser)
    logger.info(f"Native messaging host for {browser}: {'Installed' if is_installed else 'Not installed'}")
    
    if not is_installed and install:
        logger.info(f"Installing native messaging host for {browser}...")
        if manager.install_manifest(browser):
            logger.info(f"Successfully installed native messaging host for {browser}")
            is_installed = True
        else:
            logger.error(f"Failed to install native messaging host for {browser}")
            return False
    
    if not is_installed:
        logger.warning(f"Native messaging host not installed for {browser}")
        return False
    
    # Validate installation
    success, message = manager.validate_installation(browser)
    if success:
        logger.info(f"Validation successful: {message}")
    else:
        logger.error(f"Validation failed: {message}")
    
    # Check for issues
    issues = manager.diagnose_issues(browser)
    if issues:
        logger.warning("Issues found:")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("No issues found")
    
    return success and not issues


def main():
    """Main function."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create native messaging host manager
    manager = NativeMessagingHostManager()
    
    # Determine browsers to validate
    browsers = ["chrome", "edge", "firefox"] if args.browser == "all" else [args.browser]
    
    # Uninstall if requested
    if args.uninstall:
        logger.info("Uninstalling native messaging host...")
        for browser in browsers:
            if manager.uninstall_manifest(browser):
                logger.info(f"Successfully uninstalled native messaging host for {browser}")
            else:
                logger.error(f"Failed to uninstall native messaging host for {browser}")
    
    # Validate each browser
    results = {}
    for browser in browsers:
        results[browser] = validate_browser(browser, manager, args.install)
    
    # Print summary
    logger.info("Validation summary:")
    for browser, success in results.items():
        status = "PASSED" if success else "FAILED"
        logger.info(f"  {browser}: {status}")
    
    # Return exit code
    if all(results.values()):
        logger.info("All validations passed")
        return 0
    else:
        logger.error("Some validations failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
