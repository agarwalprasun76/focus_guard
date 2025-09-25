#!/usr/bin/env python
"""
FocusGuard Tab Data Parser Demo

This script demonstrates how to use the TabDataParser to analyze browser tab data.
"""

import os
import sys
from datetime import datetime
from collections import Counter
from urllib.parse import urlparse

# Add parent directory to path to allow importing tab_data_parser
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from browser_integration.tab_data_parser import TabDataParser


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {text} ".center(60, "="))
    print("=" * 60)


def print_section(text):
    """Print a formatted section header."""
    print("\n" + "-" * 60)
    print(f" {text} ".center(60, "-"))
    print("-" * 60)


def extract_domain(url):
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        return domain.lower()
    except Exception:
        return "unknown"


def main():
    """Main demo function."""
    parser = TabDataParser()
    
    print_header("FOCUSGUARD TAB DATA PARSER DEMO")
    
    # List available snapshot files
    print_section("Available Snapshot Files")
    snapshot_files = parser.get_snapshot_files()
    if snapshot_files:
        for i, file in enumerate(snapshot_files, 1):
            file_size = os.path.getsize(file) / 1024  # KB
            file_time = datetime.fromtimestamp(os.path.getmtime(file))
            print(f"{i}. {os.path.basename(file)}")
            print(f"   Size: {file_size:.1f} KB")
            print(f"   Modified: {file_time}")
    else:
        print("No snapshot files found.")
    
    # Try to load the latest snapshots
    try:
        print_section("Browser Tab Summary")
        snapshots = parser.get_latest_browser_snapshots()
        
        if not snapshots:
            print("No browser snapshots found.")
            return
        
        # Print summary for each browser
        for snapshot in snapshots:
            print(f"\nBrowser: {snapshot.browser_name}")
            print(f"Snapshot Time: {snapshot.snapshot_time}")
            print(f"Tab Count: {snapshot.tab_count}")
            
            # Count tabs by domain
            domain_counter = Counter()
            for tab in snapshot.tabs:
                domain = extract_domain(tab.url)
                domain_counter[domain] += 1
            
            # Print top domains
            print("\nTop domains:")
            for domain, count in domain_counter.most_common(5):
                print(f"  - {domain}: {count} tabs")
            
            # Print active tabs
            active_tabs = [tab for tab in snapshot.tabs if tab.active]
            print("\nActive tabs:")
            for tab in active_tabs:
                print(f"  - {tab.title[:50]}{'...' if len(tab.title) > 50 else ''}")
                print(f"    URL: {tab.url[:60]}{'...' if len(tab.url) > 60 else ''}")
        
        # Analyze all tabs across browsers
        print_section("Cross-Browser Analysis")
        all_tabs = []
        for snapshot in snapshots:
            all_tabs.extend(snapshot.tabs)
        
        # Count total tabs
        print(f"Total tabs across all browsers: {len(all_tabs)}")
        
        # Count tabs by browser
        browser_counts = {}
        for tab in all_tabs:
            browser_counts[tab.browser_name] = browser_counts.get(tab.browser_name, 0) + 1
        
        for browser, count in browser_counts.items():
            print(f"  - {browser}: {count} tabs")
        
        # Find duplicate tabs (same URL open in multiple browsers)
        print("\nDuplicate tabs (same URL in multiple browsers):")
        url_counter = Counter()
        for tab in all_tabs:
            url_counter[tab.url] += 1
        
        duplicates = {url: count for url, count in url_counter.items() if count > 1}
        if duplicates:
            for url, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {url[:60]}{'...' if len(url) > 60 else ''} ({count} instances)")
        else:
            print("  No duplicate tabs found.")
        
        # Domain analysis
        print("\nDomain analysis across all browsers:")
        all_domains = [extract_domain(tab.url) for tab in all_tabs]
        domain_counter = Counter(all_domains)
        
        for domain, count in domain_counter.most_common(10):
            if domain and domain != "unknown":
                print(f"  - {domain}: {count} tabs")
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure the browser extension is running and has collected tab data.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
