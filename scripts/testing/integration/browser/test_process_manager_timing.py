#!/usr/bin/env python3
"""
Test process manager timing issues with tab server startup.
"""

import time
import requests
import logging
import threading
from focus_guard.core.browser.extension.process_manager import get_tab_server_process_manager
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_process_manager_timing():
    """Test the timing between process manager startup and availability."""
    print("=== Process Manager Timing Test ===")
    
    # Get process manager
    process_manager = get_tab_server_process_manager()
    
    # Ensure any existing process is stopped
    if process_manager.is_running():
        print("Stopping existing process...")
        process_manager.stop()
        time.sleep(2)
    
    print("Starting tab server via process manager...")
    start_time = time.time()
    
    # Start the process
    if not process_manager.start():
        print("[ERROR] Failed to start process manager")
        return False
    
    print(f"Process manager started in {time.time() - start_time:.2f}s")
    
    # Test availability at different intervals
    test_intervals = [0.1, 0.5, 1.0, 2.0, 3.0, 5.0]
    
    for interval in test_intervals:
        time.sleep(interval - (test_intervals[test_intervals.index(interval) - 1] if interval != test_intervals[0] else 0))
        
        try:
            response = requests.get("http://localhost:5000/api/status", timeout=1.0)
            if response.status_code == 200:
                print(f"[OK] Server responding after {interval}s - Status: {response.status_code}")
                data = response.json()
                print(f"     Server info: {data.get('server', 'unknown')} - Uptime: {data.get('uptime', 0):.2f}s")
                break
            else:
                print(f"[WARN] Server responded with {response.status_code} after {interval}s")
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] Connection refused after {interval}s")
        except requests.exceptions.Timeout:
            print(f"[ERROR] Timeout after {interval}s")
        except Exception as e:
            print(f"[ERROR] Request failed after {interval}s: {e}")
    
    # Test browser integration startup
    print("\nTesting browser integration startup...")
    integration = BrowserIntegration(auto_start=False)  # Don't auto-start, we already started
    
    # Test the internal check method
    if integration._check_tab_server_status(timeout=2.0):
        print("[OK] Browser integration can connect to tab server")
    else:
        print("[ERROR] Browser integration cannot connect to tab server")
    
    # Test getting tabs
    try:
        tabs = integration.get_all_tabs()
        print(f"[OK] Retrieved {len(tabs)} tabs")
    except Exception as e:
        print(f"[ERROR] Failed to get tabs: {e}")
    
    # Clean up
    print("\nCleaning up...")
    process_manager.stop()
    
    return True

if __name__ == "__main__":
    test_process_manager_timing()
