#!/usr/bin/env python
"""
Browser Tab Monitor

This module monitors and displays browser tabs with their URLs and productivity classifications.
It can use browser extension data when available for more accurate results.
"""

import os
import sys
import time
import argparse
import re
from urllib.parse import urlparse
from datetime import datetime

# Fix console encoding on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from core.distraction_detector.browser_tracker import BrowserTabTracker
from core.cross_platform.cross_platform import get_active_window_info, enumerate_top_windows
from core.logger.logger import get_logger
from core.domain_classifier.domain_classifier import classify_domain

# Try to import browser extension integration
try:
    from core.browser_integration.tab_server import get_tab_server
    from core.browser_integration.tab_tracker_integration import get_tab_tracker_integration
    HAS_EXTENSION_SUPPORT = True
except ImportError:
    HAS_EXTENSION_SUPPORT = False

def extract_domain_from_url(url):
    """
    Extract domain from URL safely.
    
    Args:
        url (str): URL to extract domain from
        
    Returns:
        str: Domain name or 'Unknown' if extraction fails
    """
    if not url or not isinstance(url, str):
        return 'Unknown'
        
    try:
        # Handle URLs without scheme
        if not url.startswith('http') and not url.startswith('https'):
            url = 'https://' + url
            
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Handle edge cases
        if not domain or domain == 'localhost':
            return domain or 'Unknown'
            
        # Handle IP addresses
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', domain):
            return domain
            
        # Extract domain from netloc (e.g., sub.example.com -> example.com)
        parts = domain.split('.')
        if len(parts) > 2:
            # Handle special cases like co.uk, com.au, etc.
            if parts[-2] in ['co', 'com', 'org', 'net', 'edu', 'gov'] and parts[-1] in ['uk', 'au', 'ca', 'nz', 'jp']:
                return '.'.join(parts[-3:])
            return '.'.join(parts[-2:])
        
        return domain
    except Exception as e:
        return 'Unknown'

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='List browser tabs with their classifications')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--stop-server', action='store_true', help='Stop the tab server after execution')
    return parser.parse_args()

def monitor_tabs(debug=False, stop_server=False):
    """
    Monitor and display browser tabs with their productivity classifications.
    
    Args:
        debug (bool): Enable debug output
        stop_server (bool): Stop the tab server after execution
    
    Returns:
        dict: Summary of tab information
    """
    logger = get_logger("browser_tabs")
    
    if debug:
        logger.info("Debug mode enabled")
    
    # Create a browser tab tracker
    browser_tracker = BrowserTabTracker()
    
    # Check if browser extension is available and connected
    extension_tabs = []
    using_extension = False
    tab_server = None
    
    if HAS_EXTENSION_SUPPORT:
        logger.info("Browser extension support is available")
        tab_server = get_tab_server()
        tab_server.start()
        
        # Wait a moment for any extension connections
        logger.info("Waiting for browser extension connections...")
        time.sleep(2)
        
        if tab_server.is_extension_connected():
            using_extension = True
            extension_tabs = tab_server.get_tabs()
            logger.info(f"Connected to browser extension! Found {len(extension_tabs)} tabs.")
        else:
            logger.info("No browser extension connected. Using window title parsing instead.")
    else:
        logger.info("Browser extension support is not available. Using window title parsing.")
    
    # Get all top-level windows
    windows = enumerate_top_windows()
    
    # Track browser windows
    browser_windows = []
    browsers = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'iexplore.exe', 'safari.exe', 'opera.exe', 'brave.exe']
    
    # Process windows to update the browser tracker
    for window in windows:
        app_name = window.get('app_name', '').lower()
        window_title = window.get('window_title', '')
        
        if any(browser in app_name for browser in browsers) and window_title:
            browser_windows.append(window)
            browser_tracker.update_tabs(window_title)
    
    # Print header
    logger.info("\n" + "=" * 100)
    logger.info(f"BROWSER TAB REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 100)
    
    # Prepare result data
    result = {
        "using_extension": using_extension,
        "extension_tabs": [],
        "window_tabs": [],
        "active_tab": None
    }
    
    # Display tabs based on data source
    if using_extension:
        # Display extension-based tab information
        logger.info("\nTABS FROM BROWSER EXTENSION:")
        logger.info("-" * 100)
        logger.info(f"{'URL':<50} | {'Title':<30} | {'Domain':<20} | {'Productive':<10}")
        logger.info("-" * 100)
        
        for tab in extension_tabs:
            url = tab.get('url', 'Unknown')
            title = tab.get('title', 'Unknown')
            domain = extract_domain_from_url(url) if url else 'Unknown'
            if domain is None:
                domain = 'Unknown'
            is_productive = browser_tracker._is_productive_domain(domain) if domain and domain != 'Unknown' else False
            productive_str = "Yes" if is_productive else "No"
            
            # Truncate long values for display
            url_display = url[:47] + '...' if len(url) > 50 else url
            title_display = title[:27] + '...' if len(title) > 30 else title
            
            logger.info(f"{url_display:<50} | {title_display:<30} | {domain:<20} | {productive_str:<10}")
            
            # Add to result
            result["extension_tabs"].append({
                "url": url,
                "title": title,
                "domain": domain,
                "is_productive": is_productive
            })
        
        logger.info("-" * 100)
        logger.info(f"Total tabs from extension: {len(extension_tabs)}")
        
        # Show active tab
        active_tab = next((tab for tab in extension_tabs if tab.get('active')), None)
        if active_tab:
            url = active_tab.get('url', 'Unknown')
            title = active_tab.get('title', 'Unknown')
            domain = extract_domain_from_url(url) if url else 'Unknown'
            if domain is None:
                domain = 'Unknown'
            is_productive = browser_tracker._is_productive_domain(domain) if domain and domain != 'Unknown' else False
            
            logger.info("\nCURRENT ACTIVE TAB:")
            logger.info(f"Title: {title}")
            logger.info(f"URL: {url}")
            logger.info(f"Domain: {domain}")
            logger.info(f"Productive: {'Yes' if is_productive else 'No'}")
            
            # Add to result
            result["active_tab"] = {
                "url": url,
                "title": title,
                "domain": domain,
                "is_productive": is_productive
            }
            
            if debug and domain:
                try:
                    category = classify_domain(domain) or "Unclassified"
                    logger.debug(f"Category: {category}")
                    logger.debug(f"In Whitelist: {'Yes' if domain in browser_tracker.domain_whitelist else 'No'}")
                    logger.debug(f"Known Domain: {'Yes' if domain in browser_tracker.known_productivity_domains else 'No'}")
                except Exception as e:
                    logger.error(f"Error classifying domain: {e}")
    else:
        # Display window-title-based tab information
        logger.info("\nTABS FROM WINDOW TITLES:")
        logger.info("-" * 100)
        logger.info(f"{'Window Title':<50} | {'Domain':<20} | {'Productive':<10}")
        logger.info("-" * 100)
        
        # Get tab info from browser tracker
        tab_info = browser_tracker.get_tab_info()
        
        if not tab_info:
            logger.info("No browser tabs detected.")
        else:
            for title, info in tab_info.items():
                domain = info.get('domain', 'Unknown')
                if domain is None:
                    domain = 'Unknown'
                is_productive = info.get('is_productive', False)
                productive_str = "Yes" if is_productive else "No"
                
                # Truncate long titles for display
                title_display = title[:47] + '...' if len(title) > 50 else title
                
                logger.info(f"{title_display:<50} | {domain:<20} | {productive_str:<10}")
                
                # Add to result
                result["window_tabs"].append({
                    "title": title,
                    "domain": domain,
                    "is_productive": is_productive
                })
            
            logger.info("-" * 100)
            logger.info(f"Total tabs: {len(tab_info)}")
    
    # Print additional information in debug mode
    if debug:
        logger.debug("\nDEBUG INFORMATION:")
        logger.debug("-" * 100)
        logger.debug("Known Productivity Domains:")
        for domain, name in browser_tracker.known_productivity_domains.items():
            logger.debug(f"  - {domain}: {name}")
        
        logger.debug("\nProductivity Keywords:")
        logger.debug(f"  {', '.join(browser_tracker.productivity_keywords)}")
    
    # Print installation instructions if extension not connected
    if not using_extension:
        logger.info("\nINSTALLATION INSTRUCTIONS:")
        logger.info("To get more accurate tab information, install the FocusGuard browser extension:")
        logger.info("1. Open Microsoft Edge and navigate to edge://extensions/")
        logger.info("2. Enable 'Developer mode' in the bottom-left corner")
        logger.info("3. Click 'Load unpacked' and select the folder:")
        logger.info(f"   {os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'browser_extension', 'focus_guard_extension'))}")
    
    # Clean up
    if HAS_EXTENSION_SUPPORT and tab_server and stop_server:
        logger.info("Stopping tab server...")
        tab_server.stop()
        
    return result

def main():
    """Main function to monitor browser tabs."""
    args = parse_args()
    monitor_tabs(debug=args.debug, stop_server=args.stop_server)

if __name__ == "__main__":
    main()
