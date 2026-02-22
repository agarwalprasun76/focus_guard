#!/usr/bin/env python
"""
Native Messaging Host Diagnostics Utility

This script provides diagnostic tools for troubleshooting native messaging host issues.
It checks various aspects of the native messaging host setup and provides detailed
information about any issues found.
"""

import os
import sys
import json
import logging
import argparse
import platform
import subprocess
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

logger = logging.getLogger("native_host_diagnostics")


def setup_argument_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="Native messaging host diagnostics utility")
    
    parser.add_argument(
        "--browser",
        choices=["chrome", "edge", "firefox", "all"],
        default="all",
        help="Browser to diagnose (default: all)"
    )
    
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix issues automatically"
    )
    
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test connection with native messaging host"
    )
    
    parser.add_argument(
        "--check-permissions",
        action="store_true",
        help="Check file and registry permissions"
    )
    
    parser.add_argument(
        "--check-processes",
        action="store_true",
        help="Check for running browser processes"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser


def check_browser_processes():
    """Check for running browser processes."""
    logger.info("Checking for running browser processes...")
    
    browser_processes = {
        "chrome": ["chrome.exe", "Google Chrome"],
        "edge": ["msedge.exe", "Microsoft Edge"],
        "firefox": ["firefox.exe", "Mozilla Firefox"]
    }
    
    results = {}
    
    if platform.system() == "Windows":
        try:
            # Use tasklist to get running processes
            output = subprocess.check_output(["tasklist", "/FO", "CSV"]).decode("utf-8")
            for browser, process_names in browser_processes.items():
                running = any(process_name.lower() in output.lower() for process_name in process_names)
                results[browser] = running
                logger.info(f"{browser}: {'Running' if running else 'Not running'}")
        except Exception as e:
            logger.error(f"Error checking processes: {e}")
    else:
        try:
            # Use ps to get running processes
            output = subprocess.check_output(["ps", "aux"]).decode("utf-8")
            for browser, process_names in browser_processes.items():
                running = any(process_name.lower() in output.lower() for process_name in process_names)
                results[browser] = running
                logger.info(f"{browser}: {'Running' if running else 'Not running'}")
        except Exception as e:
            logger.error(f"Error checking processes: {e}")
    
    return results


def check_file_permissions(path: str) -> Dict[str, Any]:
    """
    Check file permissions.
    
    Args:
        path: Path to file or directory
        
    Returns:
        Dict[str, Any]: Permission information
    """
    if not os.path.exists(path):
        logger.warning(f"Path does not exist: {path}")
        return {"exists": False}
    
    result = {"exists": True}
    
    try:
        # Get basic file stats
        stats = os.stat(path)
        result["is_file"] = os.path.isfile(path)
        result["is_dir"] = os.path.isdir(path)
        result["size"] = stats.st_size
        result["mode"] = stats.st_mode
        
        # Check read/write/execute permissions
        result["readable"] = os.access(path, os.R_OK)
        result["writable"] = os.access(path, os.W_OK)
        result["executable"] = os.access(path, os.X_OK)
        
        logger.info(f"Permissions for {path}:")
        logger.info(f"  Readable: {result['readable']}")
        logger.info(f"  Writable: {result['writable']}")
        logger.info(f"  Executable: {result['executable']}")
        
        if result["is_file"] and not result["executable"] and path.endswith(".py"):
            logger.warning(f"Python script is not executable: {path}")
    except Exception as e:
        logger.error(f"Error checking permissions for {path}: {e}")
        result["error"] = str(e)
    
    return result


def test_native_host_connection():
    """
    Test connection with native messaging host.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    logger.info("Testing connection with native messaging host...")
    
    manager = NativeMessagingHostManager()
    native_host_path = manager.get_native_host_executable()
    
    if not os.path.exists(native_host_path):
        logger.error(f"Native host executable not found at {native_host_path}")
        return False
    
    try:
        # Create a simple message to test the native host
        test_message = {"text": "ping", "type": "test"}
        test_message_json = json.dumps(test_message)
        
        # Encode message length as 4-byte integer (native messaging protocol)
        message_length = len(test_message_json)
        message_length_bytes = message_length.to_bytes(4, byteorder="little")
        
        # Create the full message
        full_message = message_length_bytes + test_message_json.encode("utf-8")
        
        # Call the native host and capture its output
        process = subprocess.Popen(
            [sys.executable, native_host_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Send the message
        stdout, stderr = process.communicate(input=full_message, timeout=5)
        
        # Check if we got a response
        if stdout:
            # Native messaging protocol: first 4 bytes are length
            response_length = int.from_bytes(stdout[:4], byteorder="little")
            response_json = stdout[4:4+response_length].decode("utf-8")
            response = json.loads(response_json)
            
            logger.info(f"Received response: {response}")
            
            if response.get("type") == "pong":
                logger.info("Native host connection successful!")
                return True
            else:
                logger.warning(f"Unexpected response type: {response.get('type')}")
        
        if stderr:
            logger.error(f"Native host error: {stderr.decode('utf-8')}")
        
        return False
    except Exception as e:
        logger.error(f"Error testing native host connection: {e}")
        return False


def diagnose_browser(browser: str, manager: NativeMessagingHostManager, fix: bool = False) -> Dict[str, Any]:
    """
    Diagnose native messaging host setup for a specific browser.
    
    Args:
        browser: Browser name
        manager: Native messaging host manager
        fix: Whether to attempt to fix issues automatically
        
    Returns:
        Dict[str, Any]: Diagnostic results
    """
    logger.info(f"Diagnosing native messaging host for {browser}...")
    
    results = {
        "browser": browser,
        "installed": False,
        "issues": [],
        "fixes_applied": []
    }
    
    # Check if native host executable exists
    native_host_path = manager.get_native_host_executable()
    if not os.path.exists(native_host_path):
        issue = f"Native host executable not found at {native_host_path}"
        logger.error(issue)
        results["issues"].append(issue)
        
        if fix:
            logger.warning("Cannot fix missing native host executable automatically")
        return results
    
    # Check file permissions
    permissions = check_file_permissions(native_host_path)
    if not permissions.get("executable", False):
        issue = f"Native host executable is not executable: {native_host_path}"
        logger.warning(issue)
        results["issues"].append(issue)
        
        if fix and platform.system() != "Windows":
            try:
                os.chmod(native_host_path, 0o755)
                logger.info(f"Fixed permissions for {native_host_path}")
                results["fixes_applied"].append("Fixed executable permissions")
            except Exception as e:
                logger.error(f"Failed to fix permissions: {e}")
    
    # Check if native host is installed
    is_installed = manager.is_installed(browser)
    results["installed"] = is_installed
    
    if not is_installed:
        issue = f"Native messaging host not installed for {browser}"
        logger.warning(issue)
        results["issues"].append(issue)
        
        if fix:
            logger.info(f"Installing native messaging host for {browser}...")
            if manager.install_manifest(browser):
                logger.info(f"Successfully installed native messaging host for {browser}")
                results["fixes_applied"].append(f"Installed native messaging host for {browser}")
                results["installed"] = True
            else:
                logger.error(f"Failed to install native messaging host for {browser}")
    
    # Validate installation
    if results["installed"]:
        success, message = manager.validate_installation(browser)
        if success:
            logger.info(f"Validation successful: {message}")
        else:
            issue = f"Validation failed: {message}"
            logger.error(issue)
            results["issues"].append(issue)
    
    # Check for browser-specific issues
    browser_issues = manager.diagnose_issues(browser)
    if browser_issues:
        logger.warning("Browser-specific issues found:")
        for issue in browser_issues:
            logger.warning(f"  - {issue}")
            results["issues"].append(issue)
    
    return results


def main():
    """Main function."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create native messaging host manager
    manager = NativeMessagingHostManager()
    
    # Determine browsers to diagnose
    browsers = ["chrome", "edge", "firefox"] if args.browser == "all" else [args.browser]
    
    # Check for running browser processes
    if args.check_processes or args.verbose:
        process_results = check_browser_processes()
    
    # Check file permissions
    if args.check_permissions or args.verbose:
        native_host_path = manager.get_native_host_executable()
        permission_results = check_file_permissions(native_host_path)
        
        # Check manifest locations
        for browser in browsers:
            manifest_path = manager.get_manifest_path(browser)
            if manifest_path:
                logger.info(f"Checking manifest for {browser} at {manifest_path}")
                check_file_permissions(manifest_path)
    
    # Test connection with native messaging host
    if args.test_connection or args.verbose:
        connection_success = test_native_host_connection()
    
    # Diagnose each browser
    diagnostic_results = {}
    for browser in browsers:
        diagnostic_results[browser] = diagnose_browser(browser, manager, args.fix)
    
    # Print summary
    logger.info("Diagnostic summary:")
    all_ok = True
    for browser, results in diagnostic_results.items():
        status = "OK" if results["installed"] and not results["issues"] else "ISSUES FOUND"
        if status != "OK":
            all_ok = False
        
        logger.info(f"  {browser}: {status}")
        
        if results["issues"]:
            for issue in results["issues"]:
                logger.info(f"    - {issue}")
        
        if results["fixes_applied"]:
            for fix in results["fixes_applied"]:
                logger.info(f"    - {fix}")
    
    # Return exit code
    if all_ok:
        logger.info("All diagnostics passed")
        return 0
    else:
        logger.warning("Some issues were found")
        return 1


if __name__ == "__main__":
    sys.exit(main())
