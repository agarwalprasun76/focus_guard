"""
Standalone browser detection test script.

This script demonstrates the core functionality of the browser detection components
without relying on the tab server or browser extension.
"""

import os
import sys
import time
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_v2.browser.factory import BrowserComponentFactory
from core_v2.browser.models.enhanced_models import EnhancedBrowser, EnhancedTab, TabEvent, BrowserType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_mock_browser():
    """Create a mock browser for testing."""
    browser = EnhancedBrowser(
        browser_id="mock-browser-1",
        browser_name="Mock Browser",
        browser_type=BrowserType.CHROME,
        process_id=12345,
        version="1.0.0",
        executable_path="C:\\Program Files\\Mock Browser\\browser.exe"
    )
    return browser


def create_mock_tabs(browser_id):
    """Create mock tabs for testing."""
    tabs = [
        EnhancedTab(
            tab_id=1,
            window_id=1,
            browser_id=browser_id,
            title="Example Website",
            url="https://example.com",
            domain="example.com",
            favicon="https://example.com/favicon.ico",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        EnhancedTab(
            tab_id=2,
            window_id=1,
            browser_id=browser_id,
            title="GitHub",
            url="https://github.com",
            domain="github.com",
            favicon="https://github.com/favicon.ico",
            is_active=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        EnhancedTab(
            tab_id=3,
            window_id=1,
            browser_id=browser_id,
            title="Stack Overflow",
            url="https://stackoverflow.com",
            domain="stackoverflow.com",
            favicon="https://stackoverflow.com/favicon.ico",
            is_active=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]
    return tabs


class MockBrowserDetector:
    """Mock browser detector for testing."""
    
    def __init__(self):
        self.browsers = [create_mock_browser()]
    
    def get_active_browsers(self):
        """Get active browsers."""
        return self.browsers
    
    def get_browser_by_id(self, browser_id):
        """Get browser by ID."""
        for browser in self.browsers:
            if browser.browser_id == browser_id:
                return browser
        return None


class MockTabTracker:
    """Mock tab tracker for testing."""
    
    def __init__(self):
        self.browser_id = "mock-browser-1"
        self.tabs = create_mock_tabs(self.browser_id)
        self.event_handlers = {
            TabEvent.CREATED: [],
            TabEvent.UPDATED: [],
            TabEvent.REMOVED: [],
            TabEvent.ACTIVATED: []
        }
    
    def start(self):
        """Start tab tracking."""
        logger.info("Mock tab tracker started")
    
    def stop(self):
        """Stop tab tracking."""
        logger.info("Mock tab tracker stopped")
    
    def get_all_tabs(self):
        """Get all tabs."""
        return self.tabs
    
    def get_active_tab(self):
        """Get active tab."""
        for tab in self.tabs:
            if tab.is_active:
                return tab
        return None
    
    def register_tab_event_handler(self, event_type, handler):
        """Register tab event handler."""
        self.event_handlers[event_type].append(handler)
    
    def simulate_tab_created(self):
        """Simulate tab created event."""
        new_tab = EnhancedTab(
            tab_id=4,
            window_id=1,
            browser_id=self.browser_id,
            title="New Tab",
            url="https://example.org",
            domain="example.org",
            favicon="https://example.org/favicon.ico",
            is_active=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.tabs.append(new_tab)
        for handler in self.event_handlers[TabEvent.CREATED]:
            handler(new_tab)
        return new_tab
    
    def simulate_tab_updated(self, tab_id, new_url, new_title):
        """Simulate tab updated event."""
        for tab in self.tabs:
            if tab.tab_id == tab_id:
                tab.url = new_url
                tab.domain = new_url.split("//")[-1].split("/")[0]
                tab.title = new_title
                tab.last_updated = datetime.now()
                for handler in self.event_handlers[TabEvent.UPDATED]:
                    handler(tab)
                return tab
        return None
    
    def simulate_tab_removed(self, tab_id):
        """Simulate tab removed event."""
        for i, tab in enumerate(self.tabs):
            if tab.tab_id == tab_id:
                removed_tab = self.tabs.pop(i)
                for handler in self.event_handlers[TabEvent.REMOVED]:
                    handler(removed_tab)
                return removed_tab
        return None
    
    def simulate_tab_activated(self, tab_id):
        """Simulate tab activated event."""
        # First deactivate all tabs
        for tab in self.tabs:
            tab.is_active = False
        
        # Then activate the specified tab
        for tab in self.tabs:
            if tab.tab_id == tab_id:
                tab.is_active = True
                for handler in self.event_handlers[TabEvent.ACTIVATED]:
                    handler(tab)
                return tab
        return None


class MockTabBlocker:
    """Mock tab blocker for testing."""
    
    def __init__(self):
        self.blocked_domains = {}
    
    def block_domain(self, domain, expiration_time=None):
        """Block a domain."""
        self.blocked_domains[domain] = expiration_time
        logger.info(f"Domain blocked: {domain} (expires: {expiration_time})")
        return True
    
    def unblock_domain(self, domain):
        """Unblock a domain."""
        if domain in self.blocked_domains:
            del self.blocked_domains[domain]
            logger.info(f"Domain unblocked: {domain}")
            return True
        return False
    
    def is_domain_blocked(self, domain):
        """Check if a domain is blocked."""
        return domain in self.blocked_domains
    
    def close_tab(self, tab, reason=None):
        """Close a tab."""
        logger.info(f"Tab closed: {tab.url} (reason: {reason})")
        return True
    
    def close_tabs_by_domain(self, domain, reason=None):
        """Close tabs by domain."""
        logger.info(f"Closing tabs by domain: {domain} (reason: {reason})")
        return True


def main():
    """Main function."""
    logger.info("Starting standalone browser detection test")
    
    # Create mock components
    detector = MockBrowserDetector()
    tracker = MockTabTracker()
    blocker = MockTabBlocker()
    
    # Register event handlers for tab events
    def on_tab_created(tab):
        logger.info(f"Tab created: {tab.url} ({tab.title})")
    
    def on_tab_updated(tab):
        logger.info(f"Tab updated: {tab.url} ({tab.title})")
    
    def on_tab_removed(tab):
        logger.info(f"Tab removed: {tab.url} ({tab.title})")
    
    def on_tab_activated(tab):
        logger.info(f"Tab activated: {tab.url} ({tab.title})")
        
        # Example: Block social media domains
        if "facebook.com" in tab.domain or "twitter.com" in tab.domain:
            logger.info(f"Social media domain detected: {tab.domain}")
            blocker.block_domain(tab.domain)
            blocker.close_tab(tab, reason="Social media blocked")
    
    # Start tab tracking
    tracker.start()
    
    # Register event handlers
    tracker.register_tab_event_handler(TabEvent.CREATED, on_tab_created)
    tracker.register_tab_event_handler(TabEvent.UPDATED, on_tab_updated)
    tracker.register_tab_event_handler(TabEvent.REMOVED, on_tab_removed)
    tracker.register_tab_event_handler(TabEvent.ACTIVATED, on_tab_activated)
    
    try:
        # Print instructions
        print("\n" + "="*80)
        print("STANDALONE BROWSER DETECTION TEST")
        print("="*80)
        print("\nThis script simulates browser detection and tab tracking without requiring")
        print("the tab server or browser extension to be running.")
        print("\nDetected browsers:")
        for browser in detector.get_active_browsers():
            print(f"  - {browser.browser_name} ({browser.browser_type.name})")
        
        # Get initial tabs
        tabs = tracker.get_all_tabs()
        print(f"\nInitial tabs ({len(tabs)}):")
        for tab in tabs:
            print(f"  - {tab.url} ({tab.title})")
        
        # Simulate tab events
        print("\nSimulating tab events:")
        
        # Wait a moment before starting simulations
        time.sleep(1)
        
        # Simulate creating a new tab
        print("\n1. Creating a new tab...")
        new_tab = tracker.simulate_tab_created()
        time.sleep(1)
        
        # Simulate updating a tab
        print("\n2. Updating a tab...")
        updated_tab = tracker.simulate_tab_updated(
            "2", "https://github.com/focus-guard/focus-guard", "Focus Guard GitHub"
        )
        time.sleep(1)
        
        # Simulate activating a tab
        print("\n3. Activating a tab...")
        activated_tab = tracker.simulate_tab_activated("3")
        time.sleep(1)
        
        # Simulate navigating to a social media site
        print("\n4. Navigating to a social media site...")
        social_tab = tracker.simulate_tab_updated(
            "4", "https://facebook.com", "Facebook"
        )
        time.sleep(1)
        
        # Simulate activating the social media tab (should trigger blocking)
        print("\n5. Activating the social media tab...")
        tracker.simulate_tab_activated("4")
        time.sleep(1)
        
        # Simulate removing a tab
        print("\n6. Removing a tab...")
        tracker.simulate_tab_removed("1")
        time.sleep(1)
        
        # Final tab state
        tabs = tracker.get_all_tabs()
        print(f"\nFinal tabs ({len(tabs)}):")
        for tab in tabs:
            print(f"  - {tab.url} ({tab.title})")
        
        # Blocked domains
        print("\nBlocked domains:")
        if blocker.blocked_domains:
            for domain, expiration in blocker.blocked_domains.items():
                print(f"  - {domain} (expires: {expiration})")
        else:
            print("  None")
        
        print("\nTest completed successfully!")
        print("="*80)
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    finally:
        # Stop tab tracking
        tracker.stop()
        logger.info("Standalone browser detection test completed")


if __name__ == "__main__":
    main()
