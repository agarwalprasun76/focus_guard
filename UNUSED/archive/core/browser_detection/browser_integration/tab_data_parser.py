#!/usr/bin/env python
"""
FocusGuard Tab Data Parser

This module provides functionality to load and parse browser tab data collected
by the FocusGuard browser extensions and native host application.
"""

import os
import json
import glob
import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass


@dataclass
class TabData:
    """Represents a browser tab with its properties."""
    id: int
    window_id: int
    url: str
    title: str
    active: bool
    pinned: bool
    incognito: bool
    last_accessed: Optional[int] = None
    timestamp: Optional[int] = None
    browser_name: Optional[str] = None


@dataclass
class BrowserSnapshot:
    """Represents a snapshot of all tabs from a specific browser."""
    browser_name: str
    timestamp: int
    snapshot_time: str
    tab_count: int
    tabs: List[TabData]


class TabDataParser:
    """Parser for browser tab data collected by FocusGuard."""
    
    def __init__(self):
        """Initialize the tab data parser."""
        self.local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
        self.output_dir = os.path.join(self.local_appdata, "FocusGuard")
        
    def get_snapshot_files(self) -> List[str]:
        """
        Get a list of all available tab snapshot files.
        
        Returns:
            List[str]: List of paths to snapshot files
        """
        # Look for both naming patterns
        pattern1 = os.path.join(self.output_dir, "tabs_snapshot_*.json")
        pattern2 = os.path.join(self.output_dir, "tabs_snapshot.json")
        
        files = glob.glob(pattern1)
        if os.path.exists(pattern2):
            files.append(pattern2)
            
        return sorted(files, key=os.path.getmtime, reverse=True)
    
    def get_latest_snapshot_file(self) -> Optional[str]:
        """
        Get the path to the most recent snapshot file.
        
        Returns:
            Optional[str]: Path to the most recent snapshot file, or None if no files found
        """
        files = self.get_snapshot_files()
        return files[0] if files else None
    
    def load_snapshot(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load a snapshot file.
        
        Args:
            file_path: Path to the snapshot file. If None, uses the most recent file.
            
        Returns:
            Dict[str, Any]: The loaded snapshot data
            
        Raises:
            FileNotFoundError: If no snapshot file is found
            json.JSONDecodeError: If the snapshot file contains invalid JSON
        """
        if file_path is None:
            file_path = self.get_latest_snapshot_file()
            
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"No snapshot file found in {self.output_dir}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def parse_snapshot(self, snapshot_data: Dict[str, Any]) -> List[BrowserSnapshot]:
        """
        Parse snapshot data into structured browser snapshots.
        
        Args:
            snapshot_data: Raw snapshot data loaded from a JSON file
            
        Returns:
            List[BrowserSnapshot]: List of parsed browser snapshots
        """
        browser_snapshots = []
        
        # Handle the structure used by the newer native host
        if "browsers" in snapshot_data:
            for browser_name, browser_data in snapshot_data["browsers"].items():
                tabs = []
                for tab_data in browser_data.get("tabs", []):
                    tabs.append(TabData(
                        id=tab_data.get("id", 0),
                        window_id=tab_data.get("windowId", 0),
                        url=tab_data.get("url", ""),
                        title=tab_data.get("title", ""),
                        active=tab_data.get("active", False),
                        pinned=tab_data.get("pinned", False),
                        incognito=tab_data.get("incognito", False),
                        last_accessed=tab_data.get("lastAccessed"),
                        timestamp=browser_data.get("timestamp"),
                        browser_name=browser_name
                    ))
                
                browser_snapshots.append(BrowserSnapshot(
                    browser_name=browser_name,
                    timestamp=browser_data.get("timestamp", 0),
                    snapshot_time=browser_data.get("snapshot_time", ""),
                    tab_count=browser_data.get("tab_count", 0),
                    tabs=tabs
                ))
        # Handle the older structure (for backward compatibility)
        else:
            for snap in snapshot_data:
                browser_info = snap.get("browser", {})
                browser_name = browser_info.get("name", "Unknown Browser")
                tabs = []
                
                for tab_data in snap.get("tabs", []):
                    tabs.append(TabData(
                        id=tab_data.get("id", 0),
                        window_id=tab_data.get("windowId", 0),
                        url=tab_data.get("url", ""),
                        title=tab_data.get("title", ""),
                        active=tab_data.get("active", False),
                        pinned=tab_data.get("pinned", False),
                        incognito=tab_data.get("incognito", False),
                        last_accessed=tab_data.get("lastAccessed"),
                        timestamp=snap.get("timestamp"),
                        browser_name=browser_name
                    ))
                
                browser_snapshots.append(BrowserSnapshot(
                    browser_name=browser_name,
                    timestamp=snap.get("timestamp", 0),
                    snapshot_time=datetime.datetime.fromtimestamp(
                        snap.get("timestamp", 0) / 1000
                    ).isoformat() if snap.get("timestamp") else "",
                    tab_count=len(tabs),
                    tabs=tabs
                ))
                
        return browser_snapshots
    
    def get_latest_browser_snapshots(self) -> List[BrowserSnapshot]:
        """
        Get the most recent browser snapshots.
        
        Returns:
            List[BrowserSnapshot]: List of the most recent browser snapshots
            
        Raises:
            FileNotFoundError: If no snapshot file is found
        """
        snapshot_data = self.load_snapshot()
        return self.parse_snapshot(snapshot_data)
    
    def get_tabs_by_domain(self, domain: str) -> List[TabData]:
        """
        Get all tabs that match a specific domain.
        
        Args:
            domain: Domain to filter by (e.g., "example.com")
            
        Returns:
            List[TabData]: List of tabs matching the domain
        """
        all_tabs = []
        try:
            for snapshot in self.get_latest_browser_snapshots():
                all_tabs.extend(snapshot.tabs)
        except FileNotFoundError:
            return []
            
        return [tab for tab in all_tabs if domain.lower() in tab.url.lower()]
    
    def get_active_tabs(self) -> List[TabData]:
        """
        Get all currently active tabs across browsers.
        
        Returns:
            List[TabData]: List of active tabs
        """
        active_tabs = []
        try:
            for snapshot in self.get_latest_browser_snapshots():
                active_tabs.extend([tab for tab in snapshot.tabs if tab.active])
        except FileNotFoundError:
            return []
            
        return active_tabs
    
    def get_tab_counts_by_browser(self) -> Dict[str, int]:
        """
        Get the number of tabs open in each browser.
        
        Returns:
            Dict[str, int]: Dictionary mapping browser names to tab counts
        """
        counts = {}
        try:
            for snapshot in self.get_latest_browser_snapshots():
                counts[snapshot.browser_name] = snapshot.tab_count
        except FileNotFoundError:
            return {}
            
        return counts


# Example usage
if __name__ == "__main__":
    parser = TabDataParser()
    
    try:
        # Print available snapshot files
        print("Available snapshot files:")
        for file in parser.get_snapshot_files():
            print(f"  - {file}")
        print()
        
        # Get the latest snapshots
        snapshots = parser.get_latest_browser_snapshots()
        
        # Print summary of each browser's tabs
        for snapshot in snapshots:
            print(f"Browser: {snapshot.browser_name}")
            print(f"Snapshot Time: {snapshot.snapshot_time}")
            print(f"Tab Count: {snapshot.tab_count}")
            
            # Print details of each tab
            for i, tab in enumerate(snapshot.tabs, 1):
                print(f"  [{i}] {'[ACTIVE] ' if tab.active else ''}{tab.title}")
                print(f"      URL: {tab.url}")
                print(f"      {'Pinned, ' if tab.pinned else ''}{'Incognito' if tab.incognito else 'Normal'}")
                print()
            
            print("-" * 50)
            
        # Example of filtering tabs by domain
        google_tabs = parser.get_tabs_by_domain("google.com")
        print(f"\nFound {len(google_tabs)} tabs on Google domains:")
        for tab in google_tabs:
            print(f"  - {tab.title} ({tab.browser_name})")
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except json.JSONDecodeError:
        print("Error: Invalid JSON in snapshot file")
