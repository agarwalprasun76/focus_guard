#!/usr/bin/env python
"""
Browser Window Diagnostic Script

This script checks all active browser windows and prints their information
to help diagnose how blank/empty MS Edge windows appear to the system.
"""

import sys
import os
import time

# Add project root to Python path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.cross_platform.cross_platform import enumerate_top_windows, get_active_window_info
from core.logger.logger import get_logger

# Setup logger
logger = get_logger("browser_diagnostics")

def main():
    """Main diagnostic function to check browser windows"""
    logger.info("=" * 50)
    logger.info("BROWSER WINDOW DIAGNOSTICS")
    logger.info("=" * 50)
    
    # Get active window first
    active = get_active_window_info()
    logger.info(f"\nACTIVE WINDOW: {active.get('app_name', 'Unknown')} | Title: {active.get('window_title', 'Unknown')}")
    
    # Get all windows
    windows = enumerate_top_windows()
    
    # Filter for browser windows
    browsers = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'iexplore.exe', 'safari.exe', 'opera.exe', 'brave.exe']
    browser_windows = [w for w in windows if any(browser in w.get('app_name', '').lower() for browser in browsers)]
    
    # Print browser window info
    logger.info("\nBROWSER WINDOWS:")
    logger.info("-" * 50)
    
    for i, window in enumerate(browser_windows):
        app_name = window.get('app_name', 'Unknown')
        title = window.get('window_title', 'Unknown')
        pid = window.get('pid', 'Unknown')
        hwnd = window.get('hwnd', 'Unknown')
        
        logger.info(f"Window #{i+1}:")
        logger.info(f"  App: {app_name}")
        logger.info(f"  Title: {title}")
        logger.info(f"  PID: {pid}")
        logger.info(f"  HWND: {hwnd}")
        logger.info("-" * 30)
    
    # Special section for MS Edge windows
    edge_windows = [w for w in windows if 'msedge' in w.get('app_name', '').lower()]
    
    if edge_windows:
        logger.info("\nMS EDGE WINDOWS:")
        logger.info("-" * 50)
        
        for i, window in enumerate(edge_windows):
            title = window.get('window_title', 'Unknown')
            logger.info(f"Edge Window #{i+1}: \"{title}\"")
            
            # Check against blank indicators
            blank_indicators = [
                'new tab', 'microsoft edge', 'edge://', 
                'edge://new-tab-page', 'start page', 'start tab',
                'about:blank'
            ]
            
            matched_indicators = []
            for indicator in blank_indicators:
                if indicator in title.lower():
                    matched_indicators.append(indicator)
            
            if matched_indicators:
                logger.info(f"  MATCHED BLANK INDICATORS: {matched_indicators}")
            else:
                logger.info("  NO BLANK INDICATORS MATCHED")
    else:
        logger.info("\nNo Microsoft Edge windows found.")
    
    logger.info("=" * 50)
    logger.info("DIAGNOSTIC COMPLETE")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
