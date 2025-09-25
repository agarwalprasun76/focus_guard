#!/usr/bin/env python
"""
Demo for Browser Tab Blocker

This demo shows how the browser tab blocker can be used to:
1. Detect and block distracting tabs (e.g., YouTube)
2. Integrate with the FocusGuard coordinator
3. Process blocking signals

Usage:
    python demo_browser_tab_blocker.py
"""

import os
import sys
import time
import json
import logging
from pathlib import Path

# Add the parent directory to the path so we can import the core modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the browser block manager
from core.blocker.browser_block_manager import BrowserBlockManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("demo_browser_tab_blocker")


def simulate_browser_tabs():
    """Simulate a set of browser tabs for testing."""
    return [
        {
            "tab_id": 1,
            "window_id": 1,
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "domain": "youtube.com",
            "title": "YouTube Video"
        },
        {
            "tab_id": 2,
            "window_id": 1,
            "url": "https://www.github.com/user/repo",
            "domain": "github.com",
            "title": "GitHub Repository"
        },
        {
            "tab_id": 3,
            "window_id": 1,
            "url": "https://www.facebook.com/",
            "domain": "facebook.com",
            "title": "Facebook"
        },
        {
            "tab_id": 4,
            "window_id": 2,
            "url": "https://docs.google.com/document/d/123",
            "domain": "docs.google.com",
            "title": "Google Docs - Work Document"
        }
    ]


def run_demo():
    """Run the browser tab blocker demo."""
    logger.info("Starting Browser Tab Blocker Demo")
    
    # Initialize the browser block manager with categories to block
    block_manager = BrowserBlockManager(
        block_categories=['social', 'entertainment'],
        approved_only=False
    )
    
    # Start the block manager
    block_manager.start()
    logger.info("Browser Block Manager started")
    
    try:
        # Simulate browser tabs
        tabs = simulate_browser_tabs()
        logger.info(f"Simulated {len(tabs)} browser tabs")
        
        # Check which tabs should be blocked
        print("\n=== Tab Blocking Check ===")
        for tab in tabs:
            should_block = block_manager.should_block_tab(tab)
            print(f"Tab: {tab['title']} ({tab['domain']})")
            print(f"  URL: {tab['url']}")
            print(f"  Should block: {'YES' if should_block else 'NO'}")
            print()
        
        # Queue tabs for blocking
        print("\n=== Queuing Tabs for Blocking ===")
        for tab in tabs:
            if block_manager.should_block_tab(tab):
                queued = block_manager.queue_tab_block(tab)
                print(f"Tab: {tab['title']} ({tab['domain']})")
                print(f"  Queued for blocking: {'YES' if queued else 'NO'}")
                print()
        
        # Wait for processing
        print("\nWaiting for blocking queue to process...")
        time.sleep(2)
        
        # Get status
        status = block_manager.get_status()
        print("\n=== Block Manager Status ===")
        print(f"Running: {status['running']}")
        print(f"Queue size: {status['queue_size']}")
        print(f"Block categories: {', '.join(status['block_categories'])}")
        print(f"Approved-only mode: {status['approved_only']}")
        
        # Demonstrate changing settings
        print("\n=== Changing Settings ===")
        block_manager.add_block_category('productivity')
        print("Added 'productivity' to block categories")
        
        block_manager.set_approved_only_mode(True)
        print("Enabled approved-only mode")
        
        # Check status again
        status = block_manager.get_status()
        print("\n=== Updated Block Manager Status ===")
        print(f"Block categories: {', '.join(status['block_categories'])}")
        print(f"Approved-only mode: {status['approved_only']}")
        
        # Check tabs again with new settings
        print("\n=== Tab Blocking Check (Updated Settings) ===")
        for tab in tabs:
            should_block = block_manager.should_block_tab(tab)
            print(f"Tab: {tab['title']} ({tab['domain']})")
            print(f"  URL: {tab['url']}")
            print(f"  Should block: {'YES' if should_block else 'NO'}")
            print()
        
        print("\nDemo completed successfully!")
        
    finally:
        # Stop the block manager
        block_manager.stop()
        logger.info("Browser Block Manager stopped")


def integration_example():
    """
    Example of how to integrate the browser tab blocker with the FocusGuard coordinator.
    
    This is a code snippet that would be added to the FocusGuard coordinator.
    """
    print("\n=== Integration Example (Code Snippet) ===")
    print("# This is how you would integrate the browser tab blocker with the FocusGuard coordinator:")
    print("""
# In focus_guard_coordinator.py:

from core.blocker.browser_block_manager import BrowserBlockManager

class FocusGuardCoordinator:
    def __init__(self, ...):
        # ... existing initialization ...
        
        # Initialize the browser block manager
        self.browser_blocker = BrowserBlockManager(
            block_categories=['social', 'entertainment'],
            approved_only=False,
            log_dir=str(self.log_dir)
        )
    
    def start(self):
        # ... existing start code ...
        
        # Start the browser blocker
        self.browser_blocker.start()
        logger.info("Browser blocker started")
    
    def stop(self):
        # ... existing stop code ...
        
        # Stop the browser blocker
        self.browser_blocker.stop()
        logger.info("Browser blocker stopped")
    
    def handle_tab_activity(self, tab_info):
        '''Handle tab activity from browser integration.'''
        # Check if tab should be blocked
        if self.browser_blocker.should_block_tab(tab_info):
            # Queue the tab for blocking
            self.browser_blocker.queue_tab_block(tab_info)
            logger.info(f"Queued tab for blocking: {tab_info.get('url', 'Unknown URL')}")
    """)


if __name__ == "__main__":
    # Create the demos directory if it doesn't exist
    Path(__file__).parent.mkdir(parents=True, exist_ok=True)
    
    # Run the demo
    run_demo()
    
    # Show integration example
    integration_example()
