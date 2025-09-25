"""
Top Windows Analysis Demo

This script demonstrates window enumeration and analysis by identifying and displaying information
about windows located in the top portion of the screen. It's particularly useful for understanding
window positioning, sizing, and screen real estate usage.

Features:
- Identifies windows in the top 200px of the screen
- Calculates window area and screen percentage
- Updates every 5 seconds for 1 minute
- Displays window position, dimensions, and application details

Example Output:
    14:30:00 | Top windows:
      - msedge.exe: 'Example - Microsoft Edge' at (x=100, y=0, width=1200, height=200) | area=240000 | frac=12.50%
      - explorer.exe: 'File Explorer' at (x=0, y=0, width=1000, height=200) | area=200000 | frac=10.42%
      ...

Usage:
    python -m demos.cross_platform.demo_enumerate_top_windows

Note: Currently Windows-only implementation.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if sys.platform != "win32":
    print("This demo currently only works on Windows.")
    sys.exit(1)

from utils.cross_platform import enumerate_top_windows, get_screen_area

if __name__ == "__main__":
    print("Enumerating windows at the top of the screen (top 200px)...\n")
    for i in range(12):  # 1 minute, every 5 seconds
        windows = enumerate_top_windows(top_region=200)
        print(f"{time.strftime('%H:%M:%S')} | Top windows:")
        screen_area = get_screen_area()
        for w in windows:
            area = w.get('area', 0)
            frac = f"{area / screen_area:.2%}" if screen_area and area else "N/A"
            print(f"  - {w['app_name']}: '{w['window_title']}' at {w['rect']} | area={area} | frac={frac}")
        print("-")
        time.sleep(5)
