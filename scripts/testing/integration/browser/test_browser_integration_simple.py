#!/usr/bin/env python3
"""
Simple test of browser integration functionality.
"""

import sys
import time
from pathlib import Path

# Add focus_guard to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from focus_guard.core.browser.integration.browser_integration import BrowserIntegration

def test_browser_integration():
    """Test browser integration startup and basic functionality."""
    print("=== Browser Integration Test ===")
    
    # Create browser integration with auto-start
    print("Creating browser integration with auto-start...")
    integration = BrowserIntegration(auto_start=True)
    
    # Test server startup
    print("Testing server startup...")
    if integration._ensure_tab_server_running():
        print("[OK] Tab server is running")
    else:
        print("[ERROR] Failed to start tab server")
        return False
    
    # Test getting tabs
    print("Testing tab retrieval...")
    try:
        tabs = integration.get_all_tabs()
        print(f"[OK] Retrieved {len(tabs)} tabs")
        
        if tabs:
            print("Sample tabs:")
            for i, tab in enumerate(tabs[:3]):  # Show first 3 tabs
                print(f"  {i+1}. {tab.get('title', 'No title')[:50]}...")
                print(f"     URL: {tab.get('url', 'No URL')[:60]}...")
    except Exception as e:
        print(f"[ERROR] Failed to get tabs: {e}")
        return False
    
    # Test extension connectivity
    print("Testing extension connectivity...")
    try:
        connected = integration.is_extension_connected()
        print(f"[INFO] Extension connected: {connected}")
    except Exception as e:
        print(f"[ERROR] Failed to check extension connectivity: {e}")
    
    print("\n[SUCCESS] Browser integration test completed")
    return True

if __name__ == "__main__":
    test_browser_integration()
