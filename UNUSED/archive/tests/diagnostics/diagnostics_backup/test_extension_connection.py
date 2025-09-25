#!/usr/bin/env python
"""
Test script for browser extension connection

This script initializes the tab server and waits for browser extension connections.
"""

import sys
import os
import time

# Add project root to Python path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.browser_integration.tab_server import get_tab_server
from core.logger.logger import get_logger

# Setup logger
logger = get_logger("extension_test")

def test_extension_connection():
    """Test browser extension connection"""
    logger.info("=" * 50)
    logger.info("BROWSER EXTENSION CONNECTION TEST")
    logger.info("=" * 50)
    
    # Get tab server instance
    tab_server = get_tab_server()
    
    # Start the server
    logger.info("Starting tab server...")
    tab_server.start()
    
    # Wait for connections
    logger.info("Waiting for browser extension connections...")
    logger.info("Please make sure the browser extension is enabled in Edge")
    logger.info("Press Ctrl+C to stop the test")
    
    try:
        last_status = False
        while True:
            # Check connection status
            connected = tab_server.is_extension_connected()
            tabs = tab_server.get_tabs()
            
            # Only log when status changes or every 5 seconds
            if connected != last_status or int(time.time()) % 5 == 0:
                logger.info(f"Extension connected: {connected}")
                logger.info(f"Number of tabs: {len(tabs)}")
                
                if tabs:
                    # Show tab data
                    logger.info("Current tabs:")
                    for i, tab in enumerate(tabs):
                        url = tab.get('url', 'Unknown')
                        title = tab.get('title', 'Unknown')
                        is_active = tab.get('active', False)
                        logger.info(f"  Tab #{i+1}: {title} - {url} {'[ACTIVE]' if is_active else ''}")
                
                last_status = connected
            
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nTest stopped by user")
    finally:
        # Stop the server
        logger.info("Stopping tab server...")
        tab_server.stop()
        logger.info("Test complete")

if __name__ == "__main__":
    test_extension_connection()
