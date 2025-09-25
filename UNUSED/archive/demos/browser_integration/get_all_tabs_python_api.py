"""
Get all open tabs from all browsers (Edge, Chrome, etc.) using the FocusGuard Python API.
Prints all available fields for each tab and a basic classification.
Run this script from the FocusGuard root directory, after main.py is running.
"""
from core.browser_integration.tab_server_v2 import get_tab_server
import pprint

def classify_tab(tab):
    url = tab.get("url", "").lower()
    # Basic example rules
    if any(site in url for site in ["youtube.com", "reddit.com", "facebook.com", "twitter.com"]):
        return "distraction"
    elif any(site in url for site in ["docs.google.com", "wikipedia.org", "stackoverflow.com"]):
        return "useful"
    else:
        return "unknown"

def main():
    tab_data = get_tab_server().get_tabs()
    tabs = tab_data.get("tabs", [])
    browser_info = tab_data.get("browser", {})
    print(f"Browser info: {browser_info}")
    print(f"Found {len(tabs)} open tabs:")
    for i, tab in enumerate(tabs, 1):
        print(f"\nTab {i}:")
        pprint.pprint(tab)
        print(f"  Classification: {classify_tab(tab)}")

if __name__ == "__main__":
    main()
