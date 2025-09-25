#!/usr/bin/env python
"""
Browser Tab Blocker Demo

This script demonstrates the integration of the browser tab blocker with both:
- Browser extension-based tab closing (primary method)
- Chrome DevTools Protocol (CDP) as fallback

It shows how to:
1. Connect to browsers via extension or CDP
2. List open tabs
3. Close tabs based on URL patterns
4. Handle blocking signals

To run this demo:
1. Either:
   a. Install the FocusGuard browser extension (recommended)
   OR
   b. Start Chrome/Edge with remote debugging enabled (fallback):
      chrome.exe --remote-debugging-port=9222
      or
      msedge.exe --remote-debugging-port=9223

2. Open some tabs in your browser (including YouTube, Facebook, etc.)
3. Run this demo script
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the browser tab controller, blocker, and browser integration
from core.blocker.browser_tab_controller import BrowserTabController
from core.blocker.browser_tab_blocker import BrowserTabBlocker
from core.browser_detection.browser_integration.browser_integration_v2 import BrowserIntegration, is_extension_connected, start_browser_integration, stop_browser_integration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("demo_chrome_tab_blocker")


def demo_browser_detection():
    """Demonstrate browser detection and listing tabs using both extension and CDP."""
    logger.info("=== Browser Detection Demo ===")
    
    # Check if browser extension is connected
    extension_connected = is_extension_connected()
    if extension_connected:
        logger.info("FocusGuard browser extension is connected!")
        
        # Create a browser integration instance to get tabs via extension
        browser_integration = BrowserIntegration()
        tabs = browser_integration.get_all_tabs()
        
        logger.info(f"Found {len(tabs)} tabs via browser extension:")
        for i, tab in enumerate(tabs):
            browser = tab.get("browser", "Unknown")
            title = tab.get("title", "Unknown")
            url = tab.get("url", "No URL")
            logger.info(f"  {i+1}. [{browser}] {title} - {url}")
        
        return True
    else:
        logger.warning("FocusGuard browser extension is not connected.")
        logger.info("Falling back to CDP method...")
        
        # Create a browser tab controller for CDP fallback
        controller = BrowserTabController()
        
        # Check if any browsers were detected via CDP
        if not controller.clients:
            logger.warning("No browsers with debugging enabled were detected.")
            logger.info("Please start Chrome with: chrome.exe --remote-debugging-port=9222")
            logger.info("Or Edge with: msedge.exe --remote-debugging-port=9223")
            
            # For non-interactive testing, we'll skip launching Chrome
            logger.info("Skipping Chrome launch for non-interactive testing")
            logger.info("To test with CDP, manually start Chrome with: chrome.exe --remote-debugging-port=9222")
            logger.info("To test with extension, ensure the FocusGuard extension is installed and connected")
            return False
        
        # List detected browsers
        for browser_type, instances in controller.detected_browsers.items():
            logger.info(f"Detected {len(instances)} {browser_type} instances:")
            for i, instance in enumerate(instances):
                logger.info(f"  {i+1}. PID: {instance['pid']}, Port: {instance['port']}")
        
        # List all tabs
        tabs = controller.get_all_tabs()
        logger.info(f"Found {len(tabs)} tabs across all browsers:")
        for i, tab in enumerate(tabs):
            browser = tab.get("browser_type", "Unknown")
            title = tab.get("title", "Unknown")
            url = tab.get("url", "No URL")
            logger.info(f"  {i+1}. [{browser}] {title} - {url}")
        
        return True


def demo_tab_closing(controller=None):
    """Demonstrate closing tabs by URL pattern using extension or CDP."""
    logger.info("\n=== Tab Closing Demo ===")
    
    tabs = []
    use_extension = is_extension_connected() and controller is None
    
    # Get tabs based on available methods
    if use_extension:
        # Get tabs via browser integration
        browser_integration = BrowserIntegration()
        tabs = browser_integration.get_all_tabs()
        logger.info("Getting tabs via browser extension")
    elif controller:
        # Fallback to CDP if extension not connected
        tabs = controller.get_all_tabs()
        logger.info("Getting tabs via CDP (fallback)")
    
    if not tabs:
        logger.warning("No tabs found to close.")
        return False
    
    # Print all open tabs before closing
    logger.info("=== All Open Tabs Before Closing ===")
    for i, tab in enumerate(tabs):
        title = tab.get("title", "Unknown")
        url = tab.get("url", "No URL")
        tab_id = tab.get("id", tab.get("tabId", "Unknown"))
        logger.info(f"  {i+1}. [ID: {tab_id}] {title} - {url}")
    
    # Find tabs to close (prefer YouTube, Facebook, Twitter, etc.)
    target_domains = ["youtube.com", "facebook.com", "twitter.com", "instagram.com", "reddit.com"]
    target_tabs = []
    
    # Find all tabs matching target domains
    for tab in tabs:
        url = tab.get("url", "")
        if any(domain in url for domain in target_domains):
            target_tabs.append(tab)
            
    logger.info(f"Found {len(target_tabs)} tabs matching target domains:")
    for i, tab in enumerate(target_tabs):
        title = tab.get("title", "Unknown")
        url = tab.get("url", "No URL")
        tab_id = tab.get("id", tab.get("tabId", "Unknown"))
        logger.info(f"  {i+1}. [ID: {tab_id}] {title} - {url}")
    
    # If no social media tabs found, just use the first tab that's not about:blank
    if not target_tabs:
        for tab in tabs:
            url = tab.get("url", "")
            if "about:blank" not in url and "chrome://" not in url and "edge://" not in url:
                target_tabs.append(tab)
                break
    
    if not target_tabs:
        logger.warning("No suitable tabs found to close.")
        return False
    
    from core.browser_detection.browser_integration.browser_integration_v2 import close_tab
    success = True
    closed_count = 0
    
    # Close all target tabs
    for target_tab in target_tabs:
        # Display the tab we're going to close
        title = target_tab.get("title", "Unknown")
        url = target_tab.get("url", "No URL")
        logger.info(f"Closing tab: {title} - {url}")
        
        tab_success = False
        
        # Close the tab using the appropriate method
        if use_extension:
            # Close tab via browser extension
            tab_info = {
                "tabId": target_tab.get("id", target_tab.get("tabId")),
                "windowId": target_tab.get("windowId", 1),  # Default to 1 if not found
                "url": url,
                "domain": url.split("//")[-1].split("/")[0] if "//" in url else "",
                "reason": "demo_close"
            }
            
            tab_success = close_tab(tab_info)
        elif controller:
            # Close tab via CDP
            tab_success = controller.close_tab(target_tab)
        
        if tab_success:
            logger.info(f"Successfully closed tab: {title}")
            closed_count += 1
        else:
            logger.warning(f"Failed to close tab: {title}")
            success = False
    
    logger.info(f"Closed {closed_count} out of {len(target_tabs)} target tabs.")
    
    # Add a delay to allow the extension to process the close commands
    import time
    logger.info("Waiting 2 seconds for tab close commands to be processed...")
    time.sleep(2)
    
    # Get tabs again to see what's still open
    after_tabs = []
    if use_extension:
        # Get tabs via browser integration
        browser_integration = BrowserIntegration()
        after_tabs = browser_integration.get_all_tabs()
        logger.info("Getting tabs via browser extension after closing")
    elif controller:
        # Fallback to CDP if extension not connected
        after_tabs = controller.get_all_tabs()
        logger.info("Getting tabs via CDP (fallback) after closing")
    
    # Print all open tabs after closing
    logger.info("=== All Open Tabs After Closing ===")
    for i, tab in enumerate(after_tabs):
        title = tab.get("title", "Unknown")
        url = tab.get("url", "No URL")
        tab_id = tab.get("id", tab.get("tabId", "Unknown"))
        logger.info(f"  {i+1}. [ID: {tab_id}] {title} - {url}")
    
    # Check if any target domain tabs are still open
    remaining_target_tabs = []
    for tab in after_tabs:
        url = tab.get("url", "")
        if any(domain in url for domain in target_domains):
            remaining_target_tabs.append(tab)
    
    if remaining_target_tabs:
        logger.warning(f"Still have {len(remaining_target_tabs)} target domain tabs open after closing:")
        for i, tab in enumerate(remaining_target_tabs):
            title = tab.get("title", "Unknown")
            url = tab.get("url", "No URL")
            tab_id = tab.get("id", tab.get("tabId", "Unknown"))
            logger.warning(f"  {i+1}. [ID: {tab_id}] {title} - {url}")
    else:
        logger.info("All target domain tabs successfully closed!")
    
    # Return True if at least one tab was closed successfully
    success = closed_count > 0
    
    return success


def demo_blocker_integration():
    """Demonstrate integration with the browser tab blocker."""
    logger.info("\n=== Browser Tab Blocker Integration Demo ===")
    
    # Create a browser tab blocker with social and entertainment categories blocked
    # Use extension-based tab closing by default, with CDP as fallback
    blocker = BrowserTabBlocker(
        block_categories=["social", "entertainment"],
        approved_only=False,
        use_extension=True
    )
    
    # Get tabs based on available methods
    tabs = []
    
    if is_extension_connected():
        # Get tabs via browser integration
        browser_integration = BrowserIntegration()
        tabs = browser_integration.get_all_tabs()
        logger.info("Getting tabs via browser extension")
    elif blocker.tab_controller:
        # Fallback to CDP if extension not connected
        tabs = blocker.tab_controller.get_all_tabs()
        logger.info("Getting tabs via CDP (fallback)")
    
    if not tabs:
        logger.warning("No tabs found to test blocking.")
        return False
    
    # Find a tab to block
    target_tab = None
    for tab in tabs:
        url = tab.get("url", "")
        if "youtube.com" in url or "facebook.com" in url or "twitter.com" in url:
            target_tab = tab
            break
    
    if not target_tab:
        # If no social media tab found, just use the first tab that's not about:blank
        for tab in tabs:
            url = tab.get("url", "")
            if "about:blank" not in url and "chrome://" not in url and "edge://" not in url:
                target_tab = tab
                break
    
    if not target_tab:
        logger.warning("No suitable tab found to test blocking.")
        return False
    
    # Create a block signal
    tab_id = target_tab.get("id", target_tab.get("tabId", "unknown"))
    window_id = target_tab.get("windowId", 1)  # Default to 1 if not found
    
    # Map the browser tab to a FocusGuard tab format
    focus_guard_tab = {
        "tab_id": tab_id,
        "window_id": window_id,
        "url": target_tab.get("url", ""),
        "domain": target_tab.get("url", "").split("//")[-1].split("/")[0],
        "title": target_tab.get("title", "Unknown")
    }
    
    logger.info(f"Testing blocking for tab: {focus_guard_tab['title']} - {focus_guard_tab['url']}")
    
    # Check if the tab should be blocked
    should_block = blocker.should_block_tab(focus_guard_tab)
    
    if should_block:
        logger.info(f"Tab should be blocked according to blocking rules.")
        
        # Send a block signal
        block_signal = {
            "tab_id": focus_guard_tab["tab_id"],
            "window_id": focus_guard_tab["window_id"],
            "url": focus_guard_tab["url"],
            "domain": focus_guard_tab["domain"],
            "reason": "demo_block"
        }
        
        # Handle the block signal
        success = blocker.handle_tab_block_signal(block_signal)
        
        if success:
            logger.info(f"Successfully blocked tab via blocker integration.")
        else:
            logger.warning(f"Failed to block tab via blocker integration.")
        
        return success
    else:
        logger.info(f"Tab should not be blocked according to blocking rules.")
        logger.info(f"Try with a different tab or adjust blocking categories.")
        return False


def main():
    """Main demo function."""
    try:
        logger.info("Starting Browser Tab Blocker Demo")
        
        # Start the browser integration (tab server)
        logger.info("Starting browser integration and tab server...")
        start_browser_integration()
        time.sleep(1)  # Give it a moment to initialize
        
        try:
            # Run the browser detection demo
            success = demo_browser_detection()
            if not success:
                logger.error("Browser detection failed. Exiting demo.")
                return
            
            # Run the tab closing demo
            if is_extension_connected():
                # Use extension-based tab closing if extension is connected
                success = demo_tab_closing()
            else:
                # Fall back to CDP if extension is not connected
                controller = BrowserTabController()
                success = demo_tab_closing(controller)
            if not success:
                logger.error("Tab closing demo failed. Exiting demo.")
                return
            
            # Run the blocker integration demo
            success = demo_blocker_integration()
            if not success:
                logger.error("Blocker integration demo failed.")
                return
            
            logger.info("Demo completed successfully!")
            
        finally:
            # Always stop the browser integration when done
            logger.info("Stopping browser integration and tab server...")
            
            # Verify server is running and accessible before shutting down
            try:
                import requests
                response = requests.get("http://127.0.0.1:5000/api/status")
                logger.info(f"Server status check: {response.status_code} - {response.text}")
                
                # Test command endpoint
                cmd_response = requests.get("http://127.0.0.1:5000/api/command?browser=Google%20Chrome")
                logger.info(f"Command endpoint check: {cmd_response.status_code} - {cmd_response.text}")
            except Exception as e:
                logger.error(f"Failed to verify server status: {e}")
            
            # Add delay to give extension time to process commands
            logger.info("Waiting 5 seconds for extension to process commands...")
            time.sleep(5)
            stop_browser_integration()
        
    except Exception as e:
        logger.exception(f"Error in demo: {e}")


if __name__ == "__main__":
    main()
