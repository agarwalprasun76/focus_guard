#!/usr/bin/env python
"""
Test script to verify fixes for browser extension installation and communication issues.

This script tests:
1. User installation guide launching with different browser types
2. Extension connection checking with the tab server
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from focus_guard.core.browser.extension.installer import ExtensionInstaller
from focus_guard.core.browser.extension.manager import BrowserExtensionManager, BrowserType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_user_installation_guide():
    """Test launching the user installation guide for different browser types."""
    logger.info("Testing user installation guide launching...")
    
    # Create extension installer
    installer = ExtensionInstaller()
    
    # Test with supported browsers
    for browser_type in [BrowserType.CHROME, BrowserType.EDGE, BrowserType.FIREFOX]:
        logger.info(f"Testing user guide for {browser_type.name}")
        try:
            result = installer.launch_user_installation_guide_for_browser(browser_type)
            logger.info(f"User guide launch for {browser_type.name}: {'Success' if result else 'Failed'}")
        except Exception as e:
            logger.error(f"Error launching user guide for {browser_type.name}: {e}")
    
    # Test with unsupported browser (should not raise an exception)
    try:
        # Create a browser type that doesn't exist in the guide
        # This should fall back to the generic guide
        result = installer.launch_user_installation_guide_for_browser(BrowserType.SAFARI)
        logger.info(f"User guide launch for SAFARI: {'Success' if result else 'Failed'}")
    except Exception as e:
        logger.error(f"Error launching user guide for SAFARI: {e}")
        
    logger.info("User installation guide test completed")

def test_extension_connection_check():
    """Test extension connection checking with the tab server."""
    logger.info("Testing extension connection checking...")
    
    # Create extension installer and ensure tab server is running
    installer = ExtensionInstaller()
    if not installer.ensure_tab_server_running():
        logger.error("Failed to start tab server")
        return False
    
    # Get the tab server instance
    tab_server = installer._tab_server
    
    # Simulate a browser connection by updating tabs
    browser_name = "chrome"
    tab_server.update_tabs({
        "browser": browser_name,
        "tabs": [
            {"id": 1, "url": "https://example.com", "title": "Example", "active": True}
        ]
    })
    
    # Check if the extension is detected as connected
    logger.info("Checking extension connections...")
    connections = installer.check_extension_connections(timeout=5)
    
    # Log the results
    if connections:
        for browser_type, connected in connections.items():
            logger.info(f"Browser {browser_type.name} connection status: {connected}")
    else:
        logger.warning("No browser connections detected")
    
    # Get status directly from tab server to verify
    status = tab_server.get_status()
    logger.info(f"Tab server status: {status}")
    
    # Stop the tab server
    installer.stop_tab_server()
    logger.info("Extension connection check test completed")

def main():
    """Run all tests."""
    logger.info("Starting extension fixes verification tests")
    
    # Test user installation guide
    test_user_installation_guide()
    
    # Test extension connection check
    test_extension_connection_check()
    
    logger.info("All tests completed")

if __name__ == "__main__":
    main()
