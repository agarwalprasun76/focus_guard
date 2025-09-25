# demos/browser_integration/get_browser_tabs.py
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import using relative path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
from browser_detection import get_browser_windows
from datetime import datetime

def print_tabs(browsers):
    """Print browser tabs in a formatted way."""
    total_tabs = 0
    
    print("\n" + "="*60)
    print("DETECTED BROWSER TABS")
    print("="*60)
    
    for browser in browsers:
        print(f"\n{browser.name} (PID: {browser.pid})")
        print(f"Path: {browser.exe}")
        print(f"Tabs: {len(browser.tabs)}")
        
        for i, tab in enumerate(browser.tabs, 1):
            active = " [ACTIVE]" if tab.active else ""
            print(f"  {i}. {tab.title}{active}")
            if tab.url:
                print(f"     {tab.url}")
        
        total_tabs += len(browser.tabs)
    
    print(f"\nTotal tabs found: {total_tabs}")

def main():
    try:
        input("\nPress Enter to scan for browser tabs...")
    except EOFError:
        print("\nRunning in non-interactive mode...")
    
    print("\nScanning for browser tabs...")
    browsers = get_browser_windows()
    
    if not browsers:
        print("\n[!] No browser windows found.")
    else:
        print_tabs(browsers)

if __name__ == "__main__":
    main()