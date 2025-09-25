#!/usr/bin/env python
"""
Tab Server Diagnostic Script

This script checks the status of the tab server connection and verifies if 
the browser extension is sending data properly.
"""

import sys
import os
import time
import json
import requests

# Add project root to Python path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from core.browser_integration.tab_server import get_tab_server
from core.logger.logger import get_logger

# Setup logger
logger = get_logger("tab_server.diagnostics")

def check_tab_server_status():
    """Check if the tab server is running and responding"""
    tab_server = get_tab_server()
    
    logger.info("=" * 50)
    logger.info("TAB SERVER DIAGNOSTICS")
    logger.info("=" * 50)
    
    # Check if extension is connected according to our API
    connected = tab_server.is_extension_connected()
    logger.info(f"Extension connected according to API: {connected}")
    
    # Get the last update time
    last_update = tab_server.get_last_update_time()
    if last_update > 0:
        time_diff = time.time() - last_update
        logger.info(f"Last update from extension: {time_diff:.1f} seconds ago")
    else:
        logger.info("No updates have been received from extension")
    
    # Get current tabs from tab server
    tabs = tab_server.get_tabs()
    logger.info(f"Number of tabs tracked: {len(tabs)}")
    
    # Check if server is actually running
    try:
        response = requests.get("http://localhost:5000/api/status", timeout=1)
        logger.info(f"Server status endpoint response: {response.status_code}")
        logger.info(f"Response data: {response.text}")
    except Exception as e:
        logger.info(f"Failed to connect to server status endpoint: {e}")
    
    # Try to manually update tab data
    try:
        logger.info("\nAttempting to manually send tab data to server...")
        test_data = {
            "browser": "test_script",
            "tabs": [
                {"id": 1, "url": "http://test.com", "title": "Test Tab", "active": True}
            ]
        }
        response = requests.post(
            "http://localhost:5000/api/tabs", 
            json=test_data,
            timeout=1
        )
        logger.info(f"Manual update response: {response.status_code}")
        
        # Check if our test data was received
        time.sleep(0.5)
        tabs = tab_server.get_tabs()
        if tabs and len(tabs) > 0:
            logger.info("Test data successfully received by server!")
        else:
            logger.info("Server did not receive test data")
    except Exception as e:
        logger.info(f"Failed to send test data: {e}")
    
    logger.info("\n--- DEBUGGING ADVICE ---")
    
    if not connected:
        logger.info("1. Make sure the extension is enabled in Edge")
        logger.info("2. Check Edge DevTools console for JavaScript errors (press F12 in Edge)")
        logger.info("3. Verify the extension has permission to access localhost:5000")
        logger.info("4. Try restarting Edge and then Focus Guard")
        
    logger.info("=" * 50)

if __name__ == "__main__":
    check_tab_server_status()
