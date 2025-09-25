#!/usr/bin/env python3
"""
Simple User Testing for Focus Guard Domain Blocking
Manual testing instructions for domain blocking
"""

import os
import time
from focus_guard.core.platform_utils.windows.windows_config import WindowsConfig

def setup_test_config():
    """Setup test configuration with blocked domains"""
    
    print("Focus Guard Domain Blocking Test Setup")
    print("=" * 40)
    
    # Load configuration
    config = WindowsConfig()
    config_data = config.load_config()
    
    # Set up test domains
    test_domains = [
        'facebook.com',
        'twitter.com',
        'instagram.com',
        'youtube.com',
        'reddit.com',
        'tiktok.com'
    ]
    
    config_data['blocked_domains'] = test_domains
    config_data['check_interval'] = 5  # Check every 5 seconds
    config.save_config(config_data)
    
    print("Test configuration created!")
    print(f"Blocked domains: {test_domains}")
    print(f"Config file: {config.get_config_path()}")
    
    return test_domains

def manual_testing_instructions():
    """Print manual testing instructions"""
    
    domains = setup_test_config()
    
    print("\n" + "=" * 40)
    print("MANUAL TESTING INSTRUCTIONS")
    print("=" * 40)
    
    print("\n1. Start Focus Guard:")
    print("   Run: python -m focus_guard.cli.main start")
    
    print("\n2. Test domain blocking:")
    for domain in domains:
        print(f"   - Try visiting: https://{domain}")
    
    print("\n3. Expected behavior:")
    print("   - Tabs with blocked domains should be closed")
    print("   - You should see blocking notifications")
    print("   - Check system tray for monitoring status")
    
    print("\n4. Check status:")
    print("   Run: python -m focus_guard.cli.main status")
    
    print("\n5. Stop monitoring:")
    print("   Run: python -m focus_guard.cli.main stop")
    
    print("\n6. Edit configuration:")
    print("   Run: python -m focus_guard.cli.main config")
    
    print("\n" + "=" * 40)
    print("CONFIGURATION FILE LOCATION:")
    config = WindowsConfig()
    print(f"   {config.get_config_path()}")
    print("=" * 40)

if __name__ == "__main__":
    manual_testing_instructions()
