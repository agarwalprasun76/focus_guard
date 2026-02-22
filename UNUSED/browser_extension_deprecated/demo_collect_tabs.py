import os
import json
from collections import defaultdict

# Determine the snapshot file location (same logic as native host)
local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
output_dir = os.path.join(local_appdata, "FocusGuard")
out_path = os.path.join(output_dir, 'tabs_snapshot.json')

if not os.path.exists(out_path):
    print(f"No snapshot file found at: {out_path}")
    exit(1)

with open(out_path, 'r', encoding='utf-8') as f:
    snapshots = json.load(f)

# Group tabs by browser
browser_tabs = defaultdict(list)
for snap in snapshots:
    browser = snap.get('browser', {}).get('name', 'Unknown Browser')
    for tab in snap.get('tabs', []):
        browser_tabs[browser].append(tab)

for browser, tabs in browser_tabs.items():
    print(f"\nBrowser: {browser}")
    print(f"Total Tabs: {len(tabs)}")
    for i, tab in enumerate(tabs, 1):
        print(f"  [{i}] {tab.get('title', '(no title)')} - {tab.get('url', '')}")
