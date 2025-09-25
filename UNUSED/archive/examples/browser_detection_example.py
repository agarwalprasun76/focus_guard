"""
Example script demonstrating the browser detection components.

This script shows how to use the browser detection components to:
1. Detect active browsers
2. Track browser tabs
3. Block domains and close tabs
4. Track browser usage
"""

import logging
import time
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_v2.browser.factory import BrowserComponentFactory
from core_v2.browser.models.tab import TabEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function."""
    logger.info("Starting browser detection example")
    
    # Create components using the factory
    config = {
        "extension_server_url": "http://localhost:8000",  # Default port for the legacy tab server
        "storage_dir": "./data/browser_usage"
    }
    
    components = BrowserComponentFactory.create_all_components(config)
    
    browser_detector = components["browser_detector"]
    tab_tracker = components["tab_tracker"]
    tab_blocker = components["tab_blocker"]
    extension_manager = components["extension_manager"]
    usage_tracker = components["usage_tracker"]
    
    # Start tab tracking
    if hasattr(tab_tracker, "start"):
        tab_tracker.start()
        logger.info("Tab tracker started")
    
    # Register tab event handlers
    def on_tab_created(tab):
        logger.info(f"Tab created: {tab.url}")
        usage_tracker.track_active_tab(tab)
    
    def on_tab_updated(tab):
        logger.info(f"Tab updated: {tab.url}")
        
        # Check if the domain is blocked
        if tab_blocker.is_domain_blocked(tab.domain):
            logger.info(f"Closing tab with blocked domain: {tab.domain}")
            tab_blocker.close_tab(tab, reason="Blocked domain")
    
    def on_tab_removed(tab):
        logger.info(f"Tab removed: {tab.url}")
    
    def on_tab_activated(tab):
        logger.info(f"Tab activated: {tab.url}")
        usage_tracker.track_active_tab(tab)
    
    # Register event handlers if supported
    if hasattr(tab_tracker, "register_tab_event_handler"):
        tab_tracker.register_tab_event_handler(TabEvent.CREATED, on_tab_created)
        tab_tracker.register_tab_event_handler(TabEvent.UPDATED, on_tab_updated)
        tab_tracker.register_tab_event_handler(TabEvent.REMOVED, on_tab_removed)
        tab_tracker.register_tab_event_handler(TabEvent.ACTIVATED, on_tab_activated)
    
    try:
        # Detect active browsers
        logger.info("Detecting active browsers...")
        browsers = browser_detector.get_active_browsers()
        
        for browser in browsers:
            logger.info(f"Found browser: {browser.name} ({browser.type})")
            
            # Check if extension is installed
            is_installed = extension_manager.is_extension_installed(browser.type)
            logger.info(f"Extension installed for {browser.name}: {is_installed}")
            
            if not is_installed:
                logger.info(f"Installing extension for {browser.name}...")
                extension_manager.install_extension(browser.type)
        
        # Get active browser window
        active_browser = browser_detector.get_active_browser_window()
        if active_browser:
            logger.info(f"Active browser window: {active_browser.name} ({active_browser.window_title})")
            
            # Track browser session
            usage_tracker.track_browser_session(active_browser, True)
        
        # Get all tabs
        logger.info("Getting all tabs...")
        tabs = tab_tracker.get_all_tabs()
        
        for tab in tabs:
            logger.info(f"Tab: {tab.title} - {tab.url}")
        
        # Get active tab
        active_tab = tab_tracker.get_active_tab()
        if active_tab:
            logger.info(f"Active tab: {active_tab.title} - {active_tab.url}")
        
        # Block a domain (example.com)
        logger.info("Blocking domain: example.com for 60 seconds")
        tab_blocker.block_domain("example.com", 60)
        
        # Check if domain is blocked
        is_blocked = tab_blocker.is_domain_blocked("example.com")
        logger.info(f"Domain example.com is blocked: {is_blocked}")
        
        # Close tabs for blocked domain
        if is_blocked:
            logger.info("Closing tabs for blocked domain: example.com")
            tab_blocker.close_tabs_by_domain("example.com", reason="Example domain blocked")
        
        # Get usage statistics
        logger.info("Getting domain usage statistics...")
        top_domains = usage_tracker.get_top_domains(days=7, limit=5)
        
        for domain_data in top_domains:
            domain = domain_data["domain"]
            total_seconds = domain_data["total_seconds"]
            logger.info(f"Domain usage: {domain} - {total_seconds:.2f} seconds")
        
        # Run for a while to collect data
        logger.info("Running for 60 seconds to collect data...")
        time.sleep(60)
        
        # Save usage data
        logger.info("Saving usage data...")
        usage_tracker.save_usage_data()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Stop tab tracking
        if hasattr(tab_tracker, "stop"):
            tab_tracker.stop()
            logger.info("Tab tracker stopped")
        
        logger.info("Browser detection example completed")


if __name__ == "__main__":
    main()
