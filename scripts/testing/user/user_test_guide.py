#!/usr/bin/env python3
"""
User Testing Guide for Focus Guard Domain Blocking
This script provides step-by-step instructions for testing domain blocking
"""

from focus_guard.core.platform_utils.windows.windows_config import WindowsConfig
import os

def show_user_testing_guide():
    """Display user testing instructions for domain blocking"""
    
    # Get current configuration
    config = WindowsConfig()
    cfg = config.load_config()
    
    print("=" * 60)
    print("FOCUS GUARD DOMAIN BLOCKING - USER TESTING")
    print("=" * 60)
    
    print(f"\n[STATUS] Focus Guard is currently running")
    print(f"[CONFIG] Configuration file: {config.get_config_path()}")
    
    print(f"\n[CURRENT BLOCKED DOMAINS] ({len(cfg.get('blocked_domains', []))} domains)")
    for i, domain in enumerate(cfg.get('blocked_domains', []), 1):
        print(f"  {i}. {domain}")
    
    print(f"\n[SETTINGS] Check interval: {cfg.get('check_interval', 30)} seconds")
    
    print("\n" + "=" * 60)
    print("STEP-BY-STEP USER TESTING")
    print("=" * 60)
    
    print("\n1. [TEST] Open your web browser (Chrome, Firefox, Edge, etc.)")
    
    print("\n2. [TEST] Try visiting these blocked domains:")
    for domain in cfg.get('blocked_domains', []):
        print(f"   - https://{domain}")
    
    print("\n3. [EXPECTED] You should see:")
    print("   - Browser tabs being automatically closed")
    print("   - System notifications about blocked sites")
    print("   - Activity in system tray (if running)")
    
    print("\n4. [VERIFY] Check blocking effectiveness:")
    print("   - Open multiple tabs with blocked domains")
    print("   - Try different browsers")
    print("   - Test both http and https versions")
    
    print("\n5. [MONITOR] Real-time monitoring:")
    print("   - Run: python -m focus_guard.cli.main status")
    print("   - Check system tray for activity indicators")
    
    print("\n6. [CUSTOMIZE] Add your own blocked sites:")
    print("   - Run: python -m focus_guard.cli.main config")
    print("   - Edit the configuration file")
    print("   - Add domains to the 'blocked_domains' list")
    
    print("\n7. [CONTROL] Manage monitoring:")
    print("   - Stop: python -m focus_guard.cli.main stop")
    print("   - Start: python -m focus_guard.cli.main start")
    print("   - Restart: python -m focus_guard.cli.main stop && python -m focus_guard.cli.main start")
    
    print("\n" + "=" * 60)
    print("TROUBLESHOOTING")
    print("=" * 60)
    print("- If tabs aren't closing: check browser extension permissions")
    print("- If no notifications: check Windows notification settings")
    print("- If domains aren't blocked: check configuration file syntax")
    print("- For system tray: look for Focus Guard icon in taskbar")
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    show_user_testing_guide()
