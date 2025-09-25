#!/usr/bin/env python3
"""Test live tab classification."""

import sys
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from focus_guard.core.api.api import ClassifierBlockerAPI
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration

async def test_live_classification():
    print("=== Live Tab Classification Test ===")
    
    # Initialize API and browser integration
    api = ClassifierBlockerAPI()
    browser = BrowserIntegration(auto_start=True)
    
    # Get current tabs
    tabs = browser.get_all_tabs()
    print(f"Found {len(tabs)} tabs")
    
    if tabs:
        print("\nSample tabs:")
        for i, tab in enumerate(tabs[:3]):
            url = tab.get('url', 'No URL')
            title = tab.get('title', 'No title')
            # Handle Unicode encoding issues
            try:
                print(f"  {i+1}. {title[:50]}...")
                print(f"     URL: {url[:70]}...")
            except UnicodeEncodeError:
                print(f"  {i+1}. [Unicode title]")
                print(f"     URL: {url[:70]}...")
            
            # Test classification
            try:
                result = await api.classify_domain(url)
                if result:
                    print(f"     Classification: {result.category}")
                else:
                    print("     Classification: Not classified")
            except Exception as e:
                print(f"     Classification error: {e}")
            print()
    
    print("Now open a new tab with a YouTube video and wait...")
    time.sleep(5)
    
    # Check for new tabs
    new_tabs = browser.get_all_tabs()
    print(f"Tabs after 5 seconds: {len(new_tabs)}")
    
    if len(new_tabs) > len(tabs):
        print("New tabs detected!")
        for tab in new_tabs[len(tabs):]:
            url = tab.get('url', 'No URL')
            title = tab.get('title', 'No title')
            try:
                print(f"New tab: {title[:50]}")
                print(f"URL: {url[:70]}")
            except UnicodeEncodeError:
                print(f"New tab: [Unicode title]")
                print(f"URL: {url[:70]}")
            
            # Test classification of new tab
            try:
                result = await api.classify_domain(url)
                if result:
                    print(f"Classification: {result.category}")
                    should_block = await api.should_block_domain(url)
                    print(f"Should block: {should_block}")
                else:
                    print("Classification: Not classified")
            except Exception as e:
                print(f"Classification error: {e}")

if __name__ == "__main__":
    asyncio.run(test_live_classification())
