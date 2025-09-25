import sys
import json
import requests

# This script assumes the FocusGuard tab server is running and accessible
# at the default localhost endpoint (as used by your integration tests).
# It queries the tab server for all open tabs in Microsoft Edge (msedge).

TAB_SERVER_URL = "http://127.0.0.1:5000/api/tabs"

def main():
    try:
        response = requests.get(TAB_SERVER_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        tabs = data.get("tabs", [])
        print(f"Found {len(tabs)} open tabs in msedge:")
        for i, tab in enumerate(tabs, 1):
            url = tab.get("url", "<no url>")
            title = tab.get("title", "<no title>")
            print(f"{i}. {title} - {url}")
    except Exception as e:
        print(f"Error retrieving tabs: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
