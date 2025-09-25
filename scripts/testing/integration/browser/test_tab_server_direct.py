#!/usr/bin/env python3
"""
Direct test of tab server functionality.
"""

import time
import requests
import logging
import threading
from focus_guard.core.browser.extension.tab_server import TabServer, TabServerConfig

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_tab_server():
    """Test tab server startup and response."""
    print("=== Direct Tab Server Test ===")
    
    # Create tab server
    config = TabServerConfig(host="127.0.0.1", port=5001)
    server = TabServer(config)
    
    print(f"Starting tab server on {config.host}:{config.port}...")
    
    # Start server
    if not server.start():
        print("❌ Failed to start tab server")
        return False
    
    # Wait a moment for server to fully start
    time.sleep(2)
    
    # Test if server is running
    print(f"Server running: {server.is_running()}")
    
    # Test direct HTTP request
    try:
        url = f"http://{config.host}:{config.port}/api/status"
        print(f"Testing GET {url}")
        
        response = requests.get(url, timeout=5)
        print(f"[OK] Response status: {response.status_code}")
        print(f"[OK] Response body: {response.text}")
        
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] Connection error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"[ERROR] Timeout error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Request error: {e}")
        return False
    
    # Test tabs endpoint
    try:
        url = f"http://{config.host}:{config.port}/api/tabs"
        print(f"Testing GET {url}")
        
        response = requests.get(url, timeout=5)
        print(f"[OK] Tabs response status: {response.status_code}")
        print(f"[OK] Tabs response body: {response.text}")
        
    except Exception as e:
        print(f"[ERROR] Tabs request error: {e}")
    
    # Stop server
    print("Stopping server...")
    server.stop()
    
    return True

if __name__ == "__main__":
    test_tab_server()
