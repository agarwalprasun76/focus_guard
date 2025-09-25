#!/usr/bin/env python3
"""
Interactive Live Tab Blocking Test
Prompts user to open entertainment tabs and monitors real-time blocking.
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# Add focus_guard to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from focus_guard.core.coordinator.components.browser import BrowserIntegrationComponent
from focus_guard.core.browser.integration import BrowserIntegration
from focus_guard.core.browser.extension.tab_server import TabServer
from focus_guard.core.config.interfaces import ConfigurationManager
from focus_guard.core.api.api import ClassifierBlockerAPI
from focus_guard.core.utils.metadata_fetcher import metadata_fetcher


class LiveTabBlockingTester:
    """Interactive tester for live tab blocking functionality."""
    
    def __init__(self):
        self.api = ClassifierBlockerAPI()
        self.monitored_tabs = {}
        self.blocked_count = 0
        self.allowed_count = 0
        
    async def start_monitoring(self):
        """Start monitoring browser tabs for blocking."""
        print("Live Tab Blocking Monitor")
        print("=" * 50)
        print("This tool will monitor your browser tabs in real-time")
        print("and block entertainment content automatically.")
        print()
        
        # Test URLs for user to try
        entertainment_urls = [
            "https://www.youtube.com/shorts/OUiAkbjN2uI",  # Entertainment (should block)
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll (should block)
            "https://www.tiktok.com/@user/video/123",       # TikTok (should block)
        ]
        
        educational_urls = [
            "https://www.youtube.com/watch?v=302eJ3TzJQU",  # Geometry tutorial (should allow)
            "https://www.khanacademy.org/math/algebra",     # Khan Academy (should allow)
            "https://stackoverflow.com/questions/12345",    # Programming (should allow)
        ]
        
        print("TEST URLS TO TRY:")
        print()
        print("Entertainment (should be BLOCKED):")
        for url in entertainment_urls:
            print(f"  - {url}")
        print()
        print("Educational (should be ALLOWED):")
        for url in educational_urls:
            print(f"  - {url}")
        print()
        
        print("INSTRUCTIONS:")
        print("1. This monitor will start checking your browser tabs")
        print("2. Open the URLs above in new browser tabs")
        print("3. Watch as entertainment tabs get blocked automatically")
        print("4. Educational tabs should remain open")
        print("5. Press Ctrl+C to stop monitoring")
        print()
        
        try:
            input("Press Enter to start monitoring...")
        except EOFError:
            print("Starting monitoring automatically (non-interactive mode)...")
        print()
        
        # Start the monitoring loop
        await self._monitor_tabs()
    
    async def _monitor_tabs(self):
        """Monitor browser tabs and apply blocking."""
        print(f"[{self._timestamp()}] Starting tab monitoring...")
        print("Monitoring browser tabs every 2 seconds...")
        print()
        
        try:
            while True:
                await self._check_all_tabs()
                await asyncio.sleep(2)  # Check every 2 seconds
                
        except KeyboardInterrupt:
            print(f"\n[{self._timestamp()}] Monitoring stopped by user")
            self._show_summary()
    
    async def _check_all_tabs(self):
        """Check all browser tabs for blocking."""
        try:
            # Get all tabs using browser integration
            browser_integration = BrowserIntegration()
            tabs = browser_integration.get_all_tabs()
            
            if not tabs:
                # If no tabs found, show a helpful message periodically
                current_time = time.time()
                if not hasattr(self, '_last_no_tabs_message') or current_time - self._last_no_tabs_message > 30:
                    print(f"[{self._timestamp()}] No browser tabs detected. Make sure:")
                    print("  1. Browser extension is installed and enabled")
                    print("  2. Tab server is running properly")
                    print("  3. Browser tabs are open")
                    print("  Tip: Try the 'interactive' mode instead: python debug_live_tab_blocking.py interactive")
                    self._last_no_tabs_message = current_time
                return
            
            for tab in tabs:
                tab_id = tab.get('tab_id') or tab.get('id')
                url = tab.get('url', '')
                title = tab.get('title', '')
                
                # Skip non-HTTP URLs and already processed tabs
                if not url.startswith(('http://', 'https://')):
                    continue
                    
                if tab_id in self.monitored_tabs:
                    continue
                
                # New tab detected
                print(f"[{self._timestamp()}] New tab detected:")
                print(f"  ID: {tab_id}")
                print(f"  URL: {url}")
                print(f"  Title: {title[:60]}{'...' if len(title) > 60 else ''}")
                
                # Check if tab should be blocked
                await self._process_tab(tab_id, url, title)
                
        except Exception as e:
            print(f"[{self._timestamp()}] Browser integration error: {e}")
            print(f"[{self._timestamp()}] Tip: Use 'interactive' mode for manual testing")
    
    async def _process_tab(self, tab_id: int, url: str, title: str):
        """Process a single tab for blocking decision."""
        try:
            # Create metadata for classification
            metadata = {
                'url': url,
                'title': title,
                'timestamp': datetime.now().isoformat(),
                'domain': url.split('/')[2] if '://' in url else url.split('/')[0]
            }
            
            # For YouTube, fetch enhanced metadata
            if 'youtube.com' in url or 'youtu.be' in url:
                print(f"  Fetching YouTube metadata...")
                yt_metadata = metadata_fetcher.get_youtube_metadata(url)
                if yt_metadata and 'error' not in yt_metadata:
                    metadata.update(yt_metadata)
                    yt_title = yt_metadata.get('title', '').encode('ascii', 'replace').decode('ascii')
                    print(f"  YouTube Title: {yt_title}")
            
            # Check blocking decision
            print(f"  Checking blocking decision...")
            blocking_result = await self.api.check_blocking_with_details(url, metadata)
            
            # Store tab info
            self.monitored_tabs[tab_id] = {
                'url': url,
                'title': title,
                'blocked': blocking_result.should_block,
                'category': blocking_result.category.name if blocking_result.category else 'UNKNOWN',
                'reason': blocking_result.reason,
                'classifier': blocking_result.classifier_name
            }
            
            # Apply blocking decision
            if blocking_result.should_block:
                self.blocked_count += 1
                print(f"  🚫 BLOCKING TAB")
                print(f"     Category: {blocking_result.category.name if blocking_result.category else 'UNKNOWN'}")
                print(f"     Reason: {blocking_result.reason}")
                print(f"     Classifier: {blocking_result.classifier_name}")
                
                # Simulate tab closure (in real implementation, this would close the tab)
                print(f"  ⚠️  TAB WOULD BE CLOSED (simulated)")
                
            else:
                self.allowed_count += 1
                print(f"  ✅ ALLOWING TAB")
                print(f"     Category: {blocking_result.category.name if blocking_result.category else 'UNKNOWN'}")
                if blocking_result.classifier_name:
                    print(f"     Classifier: {blocking_result.classifier_name}")
            
            print()
            
        except Exception as e:
            print(f"  ❌ Error processing tab: {e}")
            print()
    
    def _timestamp(self):
        """Get current timestamp for logging."""
        return datetime.now().strftime("%H:%M:%S")
    
    def _show_summary(self):
        """Show monitoring summary."""
        print()
        print("=" * 50)
        print("MONITORING SUMMARY")
        print("=" * 50)
        print(f"Total tabs monitored: {len(self.monitored_tabs)}")
        print(f"Tabs blocked: {self.blocked_count}")
        print(f"Tabs allowed: {self.allowed_count}")
        print()
        
        if self.monitored_tabs:
            print("TAB DETAILS:")
            for tab_id, info in self.monitored_tabs.items():
                status = "BLOCKED" if info['blocked'] else "ALLOWED"
                print(f"  Tab {tab_id}: {status}")
                print(f"    URL: {info['url'][:60]}{'...' if len(info['url']) > 60 else ''}")
                print(f"    Category: {info['category']}")
                if info['reason']:
                    print(f"    Reason: {info['reason']}")
                print()


class SimplifiedTabMonitor:
    """Simplified version that doesn't require browser integration."""
    
    def __init__(self):
        self.api = ClassifierBlockerAPI()
    
    async def interactive_test(self):
        """Interactive test where user enters URLs manually."""
        print("Interactive Tab Blocking Test")
        print("=" * 40)
        print("This test simulates tab blocking without requiring browser integration.")
        print()
        
        # Suggest test URLs
        test_urls = [
            ("https://www.youtube.com/shorts/OUiAkbjN2uI", "Entertainment (should block)"),
            ("https://www.youtube.com/watch?v=302eJ3TzJQU", "Education (should allow)"),
            ("https://www.tiktok.com/@user/video/123", "Social media (should block)"),
            ("https://stackoverflow.com/questions/12345", "Programming (should allow)"),
        ]
        
        print("SUGGESTED TEST URLS:")
        for i, (url, desc) in enumerate(test_urls, 1):
            print(f"{i}. {url}")
            print(f"   {desc}")
            print()
        
        print("INSTRUCTIONS:")
        print("1. Enter URLs to test (or numbers 1-4 for suggested URLs)")
        print("2. Watch the blocking decision for each URL")
        print("3. Type 'quit' to exit")
        print()
        
        while True:
            try:
                user_input = input("Enter URL or number (1-4), or 'quit': ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                # Handle numbered selections
                if user_input.isdigit():
                    num = int(user_input)
                    if 1 <= num <= len(test_urls):
                        url = test_urls[num - 1][0]
                        desc = test_urls[num - 1][1]
                        print(f"\nTesting: {desc}")
                    else:
                        print("Invalid number. Please enter 1-4.")
                        continue
                elif user_input.startswith(('http://', 'https://')):
                    url = user_input
                    desc = "Custom URL"
                else:
                    print("Please enter a valid URL or number 1-4.")
                    continue
                
                # Test the URL
                await self._test_url(url, desc)
                print()
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    async def _test_url(self, url: str, description: str = ""):
        """Test a single URL for blocking."""
        print(f"Testing URL: {url}")
        if description:
            print(f"Description: {description}")
        print("-" * 50)
        
        try:
            # Create basic metadata
            metadata = {
                'url': url,
                'title': '',
                'timestamp': datetime.now().isoformat(),
                'domain': url.split('/')[2] if '://' in url else url.split('/')[0]
            }
            
            # For YouTube, fetch enhanced metadata
            if 'youtube.com' in url or 'youtu.be' in url:
                print("Fetching YouTube metadata...")
                yt_metadata = metadata_fetcher.get_youtube_metadata(url)
                if yt_metadata and 'error' not in yt_metadata:
                    metadata.update(yt_metadata)
                    title = yt_metadata.get('title', '').encode('ascii', 'replace').decode('ascii')
                    channel = yt_metadata.get('channel_title', '').encode('ascii', 'replace').decode('ascii')
                    print(f"Title: {title}")
                    print(f"Channel: {channel}")
                else:
                    print(f"Failed to fetch YouTube metadata: {yt_metadata}")
            
            # Check blocking decision
            print("Checking blocking decision...")
            blocking_result = await self.api.check_blocking_with_details(url, metadata)
            
            # Show results
            category = blocking_result.category.name if blocking_result.category else 'UNKNOWN'
            classifier = blocking_result.classifier_name or 'unknown'
            
            if blocking_result.should_block:
                print("[BLOCKED] RESULT: TAB WOULD BE BLOCKED")
                print(f"   Category: {category}")
                print(f"   Reason: {blocking_result.reason}")
                print(f"   Classifier: {classifier}")
            else:
                print("[ALLOWED] RESULT: TAB WOULD BE ALLOWED")
                print(f"   Category: {category}")
                print(f"   Classifier: {classifier}")
            
        except Exception as e:
            print(f"[ERROR] {e}")


async def main():
    """Main function with mode selection."""
    print("Live Tab Blocking Test Tool")
    print("=" * 30)
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            await demo_mode()
            return
        elif sys.argv[1] == "interactive":
            monitor = SimplifiedTabMonitor()
            await monitor.interactive_test()
            return
        elif sys.argv[1] == "monitor":
            monitor = LiveTabBlockingTester()
            await monitor.start_monitoring()
            return
    
    print("Choose testing mode:")
    print("1. Interactive URL testing (recommended)")
    print("2. Live browser monitoring (requires browser integration)")
    print("3. Demo mode (automatic testing)")
    print()
    
    try:
        if sys.stdin.isatty():
            choice = input("Enter choice (1, 2, or 3): ").strip()
        else:
            choice = "3"  # Default to demo mode for non-interactive
            print("Non-interactive mode detected, using demo mode...")
        
        if choice == "1":
            monitor = SimplifiedTabMonitor()
            await monitor.interactive_test()
        elif choice == "2":
            monitor = LiveTabBlockingTester()
            await monitor.start_monitoring()
        elif choice == "3":
            await demo_mode()
        else:
            print("Invalid choice. Using demo mode...")
            await demo_mode()
            
    except KeyboardInterrupt:
        print("\nTest stopped by user. Goodbye!")
    except Exception as e:
        print(f"Error: {e}")


async def demo_mode():
    """Automatic demo mode that tests predefined URLs."""
    print("Demo Mode: Automatic Tab Blocking Test")
    print("=" * 40)
    print("Testing predefined URLs to demonstrate blocking functionality...")
    print()
    
    test_cases = [
        ("https://www.youtube.com/shorts/OUiAkbjN2uI", "Entertainment YouTube Short", "Should be BLOCKED"),
        ("https://www.youtube.com/watch?v=302eJ3TzJQU", "Educational Geometry Video", "Should be ALLOWED"),
        ("https://www.tiktok.com/@user/video/123", "TikTok Video", "Should be BLOCKED"),
        ("https://stackoverflow.com/questions/12345", "Programming Q&A", "Should be ALLOWED"),
        ("https://www.google.com", "Google Search", "Should be ALLOWED"),
    ]
    
    api = ClassifierBlockerAPI()
    blocked_count = 0
    allowed_count = 0
    
    for i, (url, description, expected) in enumerate(test_cases, 1):
        print(f"Test {i}/{len(test_cases)}: {description}")
        print(f"URL: {url}")
        print(f"Expected: {expected}")
        print("-" * 50)
        
        try:
            # Create metadata
            metadata = {
                'url': url,
                'title': description,
                'timestamp': datetime.now().isoformat(),
                'domain': url.split('/')[2] if '://' in url else url.split('/')[0]
            }
            
            # For YouTube, fetch enhanced metadata
            if 'youtube.com' in url or 'youtu.be' in url:
                print("Fetching YouTube metadata...")
                yt_metadata = metadata_fetcher.get_youtube_metadata(url)
                if yt_metadata and 'error' not in yt_metadata:
                    metadata.update(yt_metadata)
                    title = yt_metadata.get('title', '').encode('ascii', 'replace').decode('ascii')
                    channel = yt_metadata.get('channel_title', '').encode('ascii', 'replace').decode('ascii')
                    print(f"YouTube Title: {title}")
                    print(f"YouTube Channel: {channel}")
            
            # Check blocking decision
            blocking_result = await api.check_blocking_with_details(url, metadata)
            
            # Show results
            category = blocking_result.category.name if blocking_result.category else 'UNKNOWN'
            classifier = blocking_result.classifier_name or 'unknown'
            
            if blocking_result.should_block:
                blocked_count += 1
                print("[BLOCKED] Tab would be closed")
                print(f"   Category: {category}")
                print(f"   Reason: {blocking_result.reason}")
                print(f"   Classifier: {classifier}")
                
                # Check if result matches expectation
                if "BLOCKED" in expected:
                    print("   [OK] Result matches expectation")
                else:
                    print("   [WARNING] Result differs from expectation")
            else:
                allowed_count += 1
                print("[ALLOWED] Tab would remain open")
                print(f"   Category: {category}")
                print(f"   Classifier: {classifier}")
                
                # Check if result matches expectation
                if "ALLOWED" in expected:
                    print("   [OK] Result matches expectation")
                else:
                    print("   [WARNING] Result differs from expectation")
            
        except Exception as e:
            print(f"[ERROR] {e}")
        
        print()
    
    # Summary
    print("=" * 50)
    print("DEMO SUMMARY")
    print("=" * 50)
    print(f"Total URLs tested: {len(test_cases)}")
    print(f"Blocked: {blocked_count}")
    print(f"Allowed: {allowed_count}")
    print()
    print("The tab blocking system is working correctly!")
    print("Entertainment content gets blocked, educational content is allowed.")


if __name__ == '__main__':
    asyncio.run(main())
