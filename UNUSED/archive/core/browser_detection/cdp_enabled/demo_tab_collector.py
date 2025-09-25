"""
Demo script for Focus Guard tab collector.
Run this script to print a table of all open Chrome/Edge tabs (including Incognito)
that were launched via Focus Guard wrappers.
"""

from tab_collector import all_tabs

if __name__ == "__main__":
    df = all_tabs()
    if df.empty:
        print("No tabs detected. Make sure you have launched Chrome/Edge via the Focus Guard shortcuts.")
    else:
        print("Detected browser tabs:")
        print(df)
