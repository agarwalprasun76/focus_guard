"""
Test script for browser integration with existing extension.

This script tests the new browser detection components with the existing extension.
It focuses on the core functionality:
1. Detecting browsers and tabs
2. Blocking domains and closing tabs
"""

import os
import sys
import time
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_v2.browser.factory import BrowserComponentFactory
from core_v2.browser.models.enhanced_models import TabEvent, EnhancedBrowserDetector, EnhancedTabTracker, EnhancedTabBlocker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function."""
    logger.info("Starting browser integration test")
    
    # Create components using the factory
    config = {
        "extension_server_url": "http://localhost:5000",  # Default port for the legacy tab server
    }
    
    # Create only the components we need for testing
    base_tab_tracker = BrowserComponentFactory.create_tab_tracker(config, use_extension=True)
    base_tab_blocker = BrowserComponentFactory.create_tab_blocker(config, use_extension=True)
    
    # Wrap with enhanced models
    tab_tracker = EnhancedTabTracker(base_tab_tracker)
    tab_blocker = EnhancedTabBlocker(base_tab_blocker)
    
    # Register event handlers for tab events
    def on_tab_created(tab):
        logger.info(f"Tab created: {tab.url} ({tab.title})")
    
    def on_tab_updated(tab):
        logger.info(f"Tab updated: {tab.url} ({tab.title})")
    
    def on_tab_removed(tab):
        logger.info(f"Tab removed: {tab.url} ({tab.title if hasattr(tab, 'title') else 'Unknown'})")
    
    def on_tab_activated(tab):
        logger.info(f"Tab activated: {tab.url} ({tab.title})")
        
        # Example: Block social media domains
        if any(domain in tab.domain for domain in ["facebook.com", "twitter.com", "instagram.com"]):
            logger.info(f"Social media domain detected: {tab.domain}")
            # Uncomment to actually block the domain
            # tab_blocker.block_domain(tab.domain)
            # tab_blocker.close_tab(tab, reason="Social media blocked")
    
    # Start tab tracking
    if hasattr(tab_tracker, "start"):
        tab_tracker.start()
        logger.info("Tab tracker started")
        
        # Register event handlers
        tab_tracker.register_tab_event_handler(TabEvent.CREATED, on_tab_created)
        tab_tracker.register_tab_event_handler(TabEvent.UPDATED, on_tab_updated)
        tab_tracker.register_tab_event_handler(TabEvent.REMOVED, on_tab_removed)
        tab_tracker.register_tab_event_handler(TabEvent.ACTIVATED, on_tab_activated)
    
    try:
        # Print instructions
        print("\n" + "="*80)
        print("BROWSER INTEGRATION TEST")
        print("="*80)
        print("\nThe tab tracker is now monitoring your browser tabs.")
        print("Try the following actions to test the integration:")
        print("1. Open new tabs in your browser")
        print("2. Navigate to different websites")
        print("3. Close tabs")
        print("4. Switch between tabs")
        print("\nYou should see log messages for each action.")
        print("\nTo test domain blocking (disabled by default):")
        print("- Uncomment the blocking code in the on_tab_activated handler")
        print("- Navigate to a social media site (facebook.com, twitter.com, etc.)")
        print("\nPress Ctrl+C to stop the test.")
        print("="*80 + "\n")
        
        # Get initial tabs
        tabs = tab_tracker.get_all_tabs()
        if tabs:
            logger.info(f"Found {len(tabs)} existing tabs:")
            for tab in tabs:
                logger.info(f"  - {tab.url} ({tab.title})")
        else:
            logger.info("No tabs found. Open some browser tabs to see them tracked.")
        
        # Main loop - just keep the script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    finally:
        # Stop tab tracking
        if hasattr(tab_tracker, "stop"):
            tab_tracker.stop()
            logger.info("Tab tracker stopped")
        
        logger.info("Browser integration test completed")


if __name__ == "__main__":
    main()
