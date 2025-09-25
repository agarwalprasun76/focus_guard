#!/usr/bin/env python3
"""
Test script for browser extension installation.
This script tests the installation of browser extensions for Chrome and Edge.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from focus_guard.core.browser.models.browser import BrowserType
from focus_guard.core.browser.extension.installer import ExtensionInstaller
from focus_guard.core.browser.extension.tab_server import get_tab_server

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_extension_installation():
    """Test the extension installation process."""
    logger.info("Starting extension installation test")
    
    # First, make sure the tab server is running
    tab_server = get_tab_server()
    if not tab_server.is_running():
        logger.info("Starting tab server...")
        tab_server.start()
        time.sleep(2)  # Give it time to start
    
    logger.info(f"Tab server running: {tab_server.is_running()}")
    
    # Create an extension installer
    extension_dir = os.path.join(
        project_root, 
        "focus_guard", 
        "core", 
        "browser", 
        "extension", 
        "webextension_mv3"
    )
    
    logger.info(f"Using extension directory: {extension_dir}")
    installer = ExtensionInstaller(extension_dir=extension_dir)
    
    # Test Chrome extension installation
    logger.info("Testing Chrome extension installation...")
    chrome_success, chrome_guide = installer.install_extension(BrowserType.CHROME)
    logger.info(f"Chrome extension installation: success={chrome_success}, guide_launched={chrome_guide}")
    
    # Test Edge extension installation
    logger.info("Testing Edge extension installation...")
    edge_success, edge_guide = installer.install_extension(BrowserType.EDGE)
    logger.info(f"Edge extension installation: success={edge_success}, guide_launched={edge_guide}")
    
    # Check for extension connections
    logger.info("Checking for extension connections...")
    connections = installer.check_extension_connections(timeout=10)
    logger.info(f"Extension connections: {connections}")
    
    return {
        "chrome_installation": chrome_success,
        "edge_installation": edge_success,
        "connections": connections
    }

if __name__ == "__main__":
    results = test_extension_installation()
    print("\nTest Results:")
    print(f"Chrome installation: {'Success' if results['chrome_installation'] else 'Failed'}")
    print(f"Edge installation: {'Success' if results['edge_installation'] else 'Failed'}")
    print(f"Connected browsers: {list(results['connections'].keys())}")
