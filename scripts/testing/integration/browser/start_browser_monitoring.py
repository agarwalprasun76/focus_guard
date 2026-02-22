#!/usr/bin/env python3
"""
Start Browser Monitoring for Domain Blocking
Fixes the browser extension connectivity issues
"""

import os
import sys
import time
import threading
from focus_guard.core.platform_utils.windows.windows_config import WindowsConfig
from focus_guard.core.browser.extension.tab_server import TabServer, get_tab_server
from focus_guard.core.browser.extension.interfaces import TabServerConfig

def start_browser_monitoring():
    """Start the browser monitoring system for domain blocking"""
    
    print("=" * 60)
    print("STARTING BROWSER MONITORING FOR DOMAIN BLOCKING")
    print("=" * 60)
    
    # Initialize configuration
    config = WindowsConfig()
    
    # Create TabServerConfig
    tab_server_config = TabServerConfig()
    
    # Get the tab server with proper configuration
    tab_server = TabServer(tab_server_config)
    
    print("[1/4] Tab server initialized")
    
    # Start the tab server
    port = 5000
    success = tab_server.start(port)
    
    if success:
        print(f"[2/4] Tab server started on port {port}")
        print(f"[3/4] Extension endpoints available:")
        print(f"      - http://localhost:{port}/api/command")
        print(f"      - http://localhost:{port}/api/tabs")
        print(f"      - http://localhost:{port}/api/status")
        print(f"[4/4] Browser extension should now be able to connect")
        
        # Show current blocked domains
        cfg = config.load_config()
        blocked_domains = cfg.get('blocked_domains', [])
        print(f"\n[CONFIG] Monitoring {len(blocked_domains)} domains:")
        for domain in blocked_domains:
            print(f"      - {domain}")
        
        print(f"\n[TESTING] Open your browser and visit:")
        for domain in blocked_domains:
            print(f"      https://{domain}")
        
        print(f"\n[MONITORING] Server is running... Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping browser monitoring...")
            tab_server.stop()
            print("Browser monitoring stopped")
    else:
        print("[ERROR] Failed to start tab server")
        return False
    
    return True

def test_browser_extension_connectivity():
    """Test browser extension connectivity"""
    import requests
    
    print("\nTesting browser extension connectivity...")
    
    try:
        # Test API endpoints
        endpoints = [
            "http://localhost:58392/api/status",
            "http://localhost:58392/api/command",
            "http://localhost:58392/api/tabs"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=2)
                print(f"✅ {endpoint} - {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"❌ {endpoint} - {e}")
                
    except Exception as e:
        print(f"Error testing connectivity: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_browser_extension_connectivity()
    else:
        start_browser_monitoring()
