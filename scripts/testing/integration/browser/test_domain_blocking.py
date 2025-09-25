#!/usr/bin/env python3
"""
User Testing Script for Focus Guard Domain Blocking
Run this script to test domain blocking functionality
"""

import asyncio
import time
import webbrowser
import threading
from focus_guard.core.platform_utils.windows.windows_config import WindowsConfig
from focus_guard.core.coordinator import FocusGuardCoordinator

def test_domain_blocking():
    """Test domain blocking with user interaction"""
    
    print("Focus Guard Domain Blocking Test")
    print("=" * 50)
    
    # Load test configuration
    config = WindowsConfig()
    config_data = config.load_config()
    
    # Ensure we have blocked domains for testing
    if not config_data.get('blocked_domains'):
        config_data['blocked_domains'] = [
            'facebook.com',
            'twitter.com', 
            'instagram.com',
            'youtube.com',
            'reddit.com',
            'tiktok.com'
        ]
        config.save_config(config_data)
    
    print("[OK] Configuration loaded")
    print(f"Blocked domains: {config_data['blocked_domains']}")
    print(f"Check interval: {config_data.get('check_interval', 30)}s")
    
    print("\nStarting Focus Guard...")
    
    try:
        # Initialize coordinator
        coordinator = FocusGuardCoordinator(config)
        
        # Start monitoring
        asyncio.run(coordinator.start())
        print("[OK] Focus Guard started successfully!")
        
        print("\nTesting Instructions:")
        print("1. Open your web browser")
        print("2. Try visiting any of these blocked domains:")
        for domain in config_data['blocked_domains']:
            print(f"   - https://{domain}")
        print("3. Watch for blocking notifications")
        print("4. Check system tray for status updates")
        
        print("\nMonitoring active...")
        print("Press Ctrl+C to stop testing")
        
        # Keep running for testing
        try:
            while True:
                time.sleep(5)
                status = coordinator.get_status()
                print(f"Status: {status}")
                
        except KeyboardInterrupt:
            print("\nStopping test...")
            asyncio.run(coordinator.stop())
            print("[OK] Test completed")
            
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure all dependencies are installed")

if __name__ == "__main__":
    test_domain_blocking()
