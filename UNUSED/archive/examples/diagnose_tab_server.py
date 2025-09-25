"""
Diagnostic script for tab server communication.

This script checks if the tab server is running correctly and receiving data
from the browser extension.
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.browser_detection.browser_integration.tab_server_v2 import TabServer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_server_running(host="127.0.0.1", port=5000):
    """Check if the tab server is running and accessible."""
    try:
        response = requests.get(f"http://{host}:{port}/api/status", timeout=2)
        if response.status_code == 200:
            logger.info(f"Server is running: {response.json()}")
            return True
        else:
            logger.error(f"Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(f"Could not connect to server at {host}:{port}")
        return False
    except Exception as e:
        logger.error(f"Error checking server: {e}")
        return False

def send_test_data(host="127.0.0.1", port=5000):
    """Send test tab data to the server."""
    test_data = {
        "browser": {
            "name": "Test Browser",
            "version": "1.0.0",
            "platform": "Test Platform"
        },
        "tabs": [
            {
                "id": 1,
                "windowId": 1,
                "url": "https://example.com",
                "title": "Test Tab",
                "active": True,
                "pinned": False,
                "lastAccessed": datetime.now().timestamp(),
                "incognito": False
            }
        ],
        "timestamp": datetime.now().timestamp()
    }
    
    try:
        response = requests.post(
            f"http://{host}:{port}/api/tabs",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            logger.info(f"Successfully sent test data: {response.json()}")
            return True
        else:
            logger.error(f"Server returned status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error sending test data: {e}")
        return False

def get_tabs_from_server(host="127.0.0.1", port=5000):
    """Get tabs from the server."""
    try:
        response = requests.get(f"http://{host}:{port}/api/tabs", timeout=2)
        if response.status_code == 200:
            tabs = response.json()
            logger.info(f"Retrieved {len(tabs.get('tabs', []))} tabs from server")
            return tabs
        else:
            logger.error(f"Server returned status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error getting tabs: {e}")
        return None

def start_local_server():
    """Start a local tab server instance."""
    logger.info("Starting local tab server...")
    tab_server = TabServer(host="127.0.0.1", port=5000)
    if tab_server.start():
        logger.info("Tab server started successfully")
        return tab_server
    else:
        logger.error("Failed to start tab server")
        return None

def main():
    """Main diagnostic function."""
    logger.info("Starting tab server diagnostics")
    
    # Check if server is already running
    if check_server_running():
        logger.info("Tab server is already running")
    else:
        logger.info("Tab server is not running, starting a new instance")
        tab_server = start_local_server()
        if not tab_server:
            logger.error("Could not start tab server, exiting")
            return
        
        # Give the server time to start
        time.sleep(1)
        
        if not check_server_running():
            logger.error("Server started but is not responding, exiting")
            return
    
    # Send test data
    logger.info("Sending test data to server")
    if send_test_data():
        logger.info("Test data sent successfully")
    else:
        logger.error("Failed to send test data")
    
    # Get tabs from server
    logger.info("Getting tabs from server")
    tabs = get_tabs_from_server()
    if tabs:
        logger.info(f"Server has {len(tabs.get('tabs', []))} tabs")
        logger.info(f"Last update time: {datetime.fromtimestamp(tabs.get('last_update', 0))}")
    else:
        logger.error("Failed to get tabs from server")
    
    # Check if extension is connected
    logger.info("Checking if extension is connected")
    try:
        response = requests.get("http://127.0.0.1:5000/api/status", timeout=2)
        if response.status_code == 200:
            status = response.json()
            if status.get("extension_connected", False):
                logger.info("Extension is connected to the server")
            else:
                logger.warning("Extension is NOT connected to the server")
                logger.info("Last update time: " + 
                           datetime.fromtimestamp(status.get("last_update", 0)).strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        logger.error(f"Error checking extension connection: {e}")
    
    logger.info("Diagnostic complete")

if __name__ == "__main__":
    main()
