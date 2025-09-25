"""Test script for browser tab detection."""
import sys
import os
import time
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.browser_detection import (
    BrowserDetector, 
    WindowsBrowserDetector,
    browser_tab_info
)

def test_browser_detection():
    """Test the browser tab detection."""
    print("Testing browser tab detection...")
    
    # Create detector instance
    detector = WindowsBrowserDetector()
    
    # Get browser windows
    print("\nDetecting browser windows...")
    start_time = time.time()
    
    try:
        browsers = detector.get_browser_windows()
        elapsed = time.time() - start_time
        
        if not browsers:
            print("No browser windows found.")
            return
            
        print(f"\nFound {len(browsers)} browser(s) in {elapsed:.2f} seconds")
        
        for browser in browsers:
            print(f"\n{browser.name} (PID: {browser.pid})")
            print(f"Path: {browser.path}")
            print(f"Open tabs: {len(browser.tabs)}")
            
            for i, tab in enumerate(browser.tabs, 1):
                private = " [PRIVATE]" if tab.is_private else ""
                source = f" (via {tab.source.upper()})" if hasattr(tab, 'source') else ""
                print(f"  {i}. {tab.title}{private}{source}")
                print(f"     URL: {tab.url}")
                
    except Exception as e:
        print(f"Error during browser detection: {e}")
        import traceback
        traceback.print_exc()

def test_low_level_detection():
    """Test the low-level browser tab detection."""
    print("\nTesting low-level browser detection...")
    
    # Create detector instance
    detector = browser_tab_info.BrowserTabDetector()
    
    # Get browser tabs
    print("\nDetecting browser tabs...")
    start_time = time.time()
    
    try:
        browsers = detector.get_browser_tabs()
        elapsed = time.time() - start_time
        
        if not browsers:
            print("No browser tabs found.")
            return
            
        print(f"\nFound {len(browsers)} browser(s) in {elapsed:.2f} seconds")
        
        for browser in browsers:
            print(f"\n{browser.name} (PID: {browser.pid})")
            print(f"Path: {browser.path}")
            print(f"Open tabs: {len(browser.tabs)}")
            
            for i, tab in enumerate(browser.tabs, 1):
                private = " [PRIVATE]" if tab.is_private else ""
                source = f" (via {tab.source.upper()})" if hasattr(tab, 'source') else ""
                print(f"  {i}. {tab.title}{private}{source}")
                print(f"     URL: {tab.url}")
                
    except Exception as e:
        print(f"Error during browser detection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== Browser Tab Detection Test ===")
    test_browser_detection()
    test_low_level_detection()
