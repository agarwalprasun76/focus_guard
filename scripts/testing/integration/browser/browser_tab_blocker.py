#!/usr/bin/env python3
"""
Browser Tab Blocker for User Testing
This provides a simple demonstration of domain blocking
"""

import time
import json
import os
from typing import List, Dict, Any
from focus_guard.core.platform_utils.windows.windows_config import WindowsConfig

class SimpleBrowserTabBlocker:
    """Simple browser tab blocker for user testing demonstration"""
    
    def __init__(self):
        self.config = WindowsConfig()
        self.running = False
        
    def start_monitoring(self):
        """Start monitoring browser tabs"""
        print("Starting browser tab monitoring...")
        self.running = True
        
        # Load configuration
        cfg = self.config.load_config()
        blocked_domains = cfg.get('blocked_domains', [])
        check_interval = cfg.get('check_interval', 30)
        
        print(f"Monitoring {len(blocked_domains)} blocked domains:")
        for domain in blocked_domains:
            print(f"  - {domain}")
        
        print("\nTo test domain blocking:")
        print("1. Open your browser")
        print("2. Visit any of the blocked domains")
        print("3. The script will simulate tab closure")
        print("4. Check console output for blocking notifications")
        
        # Simulate monitoring loop
        try:
            while self.running:
                # In a real implementation, this would check actual browser tabs
                time.sleep(check_interval)
                print(f"[{time.strftime('%H:%M:%S')}] Checking for blocked domains...")
                
        except KeyboardInterrupt:
            print("Stopping monitoring...")
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        print("Browser tab monitoring stopped")
    
    def block_domain(self, domain: str) -> bool:
        """Check if a domain should be blocked"""
        cfg = self.config.load_config()
        blocked_domains = cfg.get('blocked_domains', [])
        
        # Check if domain is in blocked list
        if domain in blocked_domains:
            print(f"[BLOCKED] Domain {domain} is blocked")
            return True
        
        # Check for subdomain matches
        for blocked_domain in blocked_domains:
            if domain.endswith(f".{blocked_domain}") or domain == blocked_domain:
                print(f"[BLOCKED] Domain {domain} matches blocked {blocked_domain}")
                return True
        
        return False
    
    def simulate_tab_blocking(self, url: str):
        """Simulate blocking a browser tab"""
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            if self.block_domain(domain):
                print(f"[TAB BLOCKED] Would close tab for: {url}")
                return True
            else:
                print(f"[ALLOWED] Domain {domain} is not blocked")
                return False
                
        except Exception as e:
            print(f"Error parsing URL {url}: {e}")
            return False

def run_user_test():
    """Run user testing for domain blocking"""
    blocker = SimpleBrowserTabBlocker()
    
    print("=" * 60)
    print("FOCUS GUARD DOMAIN BLOCKING - USER TEST")
    print("=" * 60)
    
    # Show current configuration
    config = WindowsConfig()
    cfg = config.load_config()
    
    print(f"\n[CONFIGURATION] {len(cfg.get('blocked_domains', []))} domains blocked:")
    for domain in cfg.get('blocked_domains', []):
        print(f"  - {domain}")
    
    print("\n[TESTING INSTRUCTIONS]")
    print("1. This script simulates browser tab blocking")
    print("2. Enter URLs to test if they would be blocked")
    print("3. Type 'quit' to exit testing")
    
    while True:
        url = input("\nEnter URL to test (or 'quit'): ").strip()
        
        if url.lower() == 'quit':
            print("Testing complete!")
            break
            
        if url:
            blocker.simulate_tab_blocking(url)

if __name__ == "__main__":
    run_user_test()
