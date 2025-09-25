#!/usr/bin/env python
"""
Demo for FocusGuard Coordinator with Browser Tab Blocker

This demo shows the complete end-to-end functionality of:
1. Starting the FocusGuard coordinator with browser blocking enabled
2. Simulating browser tab activity
3. Handling tab blocking decisions through the coordinator
4. Demonstrating the blocking of distracting tabs (e.g., YouTube)

Usage:
    python demo_coordinator_with_blocker.py
"""

import os
import sys
import time
import json
import logging
from pathlib import Path

# Add the parent directory to the path so we can import the core modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the coordinator
from core.coordinator.focus_guard_coordinator import FocusGuardCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("demo_coordinator_with_blocker")


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
    """Run the coordinator with browser tab blocker demo."""
    logger.info("Starting FocusGuard Coordinator with Browser Tab Blocker Demo")
    
    # Initialize the coordinator with browser blocking enabled
    coordinator = FocusGuardCoordinator(
        interval_seconds=5,
        block_categories=['social', 'entertainment'],
        approved_only=False
    )
    
    # Start the coordinator
    coordinator.start()
    logger.info("FocusGuard Coordinator started")
    
    try:
        # Get initial status
        status = coordinator.get_status()
        print("\n=== Coordinator Status ===")
        for key, value in status.items():
            print(f"{key}: {value}")
        
        # Simulate browser tabs
        tabs = simulate_browser_tabs()
        logger.info(f"Simulated {len(tabs)} browser tabs")
        
        # Process each tab through the coordinator
        print("\n=== Tab Processing ===")
        for tab in tabs:
            print(f"\nTab: {tab['title']} ({tab['domain']})")
            print(f"  URL: {tab['url']}")
            
            # Handle tab activity through coordinator
            blocked = coordinator.handle_tab_activity(tab)
            print(f"  Blocked: {'YES' if blocked else 'NO'}")
        
        # Wait for processing
        print("\nWaiting for blocking queue to process...")
        time.sleep(2)
        
        # Get updated status
        status = coordinator.get_status()
        print("\n=== Updated Coordinator Status ===")
        for key, value in status.items():
            print(f"{key}: {value}")
        
        # Demonstrate changing settings
        print("\n=== Changing Block Settings ===")
        if coordinator.browser_blocker:
            coordinator.browser_blocker.add_block_category('productivity')
            print("Added 'productivity' to block categories")
            
            # Process tabs again with new settings
            print("\n=== Tab Processing (Updated Settings) ===")
            for tab in tabs:
                print(f"\nTab: {tab['title']} ({tab['domain']})")
                print(f"  URL: {tab['url']}")
                
                # Handle tab activity through coordinator
                blocked = coordinator.handle_tab_activity(tab)
                print(f"  Blocked: {'YES' if blocked else 'NO'}")
        
        print("\nDemo completed successfully!")
        
    finally:
        # Stop the coordinator
        coordinator.stop()
        logger.info("FocusGuard Coordinator stopped")


def explain_real_world_usage():
    """Explain how this would work in a real-world scenario."""
    print("\n=== Real-World Usage ===")
    print("""
In a real-world implementation, the browser tab blocker would:

1. Receive tab activity from the browser extension through the native host
2. The coordinator would process each tab and check if it should be blocked
3. If a tab should be blocked, it would be queued for blocking
4. The browser blocker would then close the tab using:
   - Chrome DevTools Protocol for Chrome/Edge
   - WebExtension API for Firefox
   - Or a combination of approaches depending on the browser

For Chrome specifically, the actual tab closing would be implemented by:
1. Connecting to Chrome's debugging port
2. Using the Chrome DevTools Protocol to close the specific tab
3. Or sending a message back to the browser extension to close the tab

This demo simulates the decision-making process, but in production,
you would need to implement the actual tab closing mechanism using
browser-specific APIs.
""")


if __name__ == "__main__":
    # Create the demos directory if it doesn't exist
    Path(__file__).parent.mkdir(parents=True, exist_ok=True)
    
    # Run the demo
    run_demo()
    
    # Explain real-world usage
    explain_real_world_usage()
