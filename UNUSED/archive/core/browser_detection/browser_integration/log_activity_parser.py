#!/usr/bin/env python
"""
FocusGuard Log Activity Parser

This module provides functionality to analyze browser tab activity from FocusGuard debug logs.
It tracks tab usage over time and provides summaries of which tabs/websites were active
for the longest periods.
"""

import os
import re
import json
import glob
import datetime
import ast
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import pandas as pd
from urllib.parse import urlparse


@dataclass
class TabActivity:
    """Represents a browser tab's activity over time."""
    tab_id: int
    window_id: int
    url: str
    title: str
    domain: str
    browser_name: str
    first_seen: datetime.datetime
    last_seen: datetime.datetime
    active_periods: List[Tuple[datetime.datetime, datetime.datetime]]
    total_active_seconds: int = 0
    
    def add_activity(self, timestamp: datetime.datetime, is_active: bool):
        """Add an activity record for this tab."""
        self.last_seen = timestamp
        
        # If this is an active tab, record the activity period
        if is_active:
            # If we have active periods and the last one is recent (within 10 seconds),
            # extend the last period instead of creating a new one
            if self.active_periods and (timestamp - self.active_periods[-1][1]).total_seconds() < 10:
                self.active_periods[-1] = (self.active_periods[-1][0], timestamp)
            else:
                self.active_periods.append((timestamp, timestamp))
            
            # Update total active time
            self.calculate_active_time()
    
    def calculate_active_time(self):
        """Calculate the total active time for this tab."""
        total_seconds = 0
        for start, end in self.active_periods:
            # Add 5 seconds for each activity period (default interval)
            period_seconds = max(5, (end - start).total_seconds())
            total_seconds += period_seconds
        
        self.total_active_seconds = total_seconds


class LogActivityParser:
    """Parser for FocusGuard debug logs to analyze tab activity."""
    
    def __init__(self):
        """Initialize the log activity parser."""
        self.local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
        self.output_dir = os.path.join(self.local_appdata, "FocusGuard")
        self.tabs_by_id = {}  # Dictionary of tab activities indexed by tab_id
        self.timestamp_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)')
        self.message_pattern = re.compile(r'Received message: ({.*})')
        
    def get_log_files(self, date_str: Optional[str] = None) -> List[str]:
        """
        Get a list of available debug log files.
        
        Args:
            date_str: Optional date string in YYYY-MM-DD format. If provided,
                      only returns logs for that date.
        
        Returns:
            List[str]: List of paths to log files
        """
        if date_str:
            pattern = os.path.join(self.output_dir, f"focusguard_debug_{date_str}.log")
            files = glob.glob(pattern)
        else:
            pattern = os.path.join(self.output_dir, "focusguard_debug_*.log")
            files = glob.glob(pattern)
            
        return sorted(files, key=os.path.getmtime, reverse=True)
    
    def extract_domain(self, url: str) -> str:
        """Extract the domain from a URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Handle special cases like chrome:// URLs
            if not domain and parsed.scheme:
                return f"{parsed.scheme}://{parsed.path.split('/')[0]}"
                
            return domain.lower()
        except Exception:
            return "unknown"
    
    def parse_log_file(self, file_path: str) -> Dict[int, TabActivity]:
        """
        Parse a debug log file and extract tab activity information.
        
        Args:
            file_path: Path to the debug log file
            
        Returns:
            Dict[int, TabActivity]: Dictionary of tab activities indexed by tab_id
        """
        tabs_by_id = {}
        message_count = 0
        snapshot_count = 0
        tab_count = 0
        error_count = 0
        print(f"Parsing log file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Extract timestamp
                timestamp_match = self.timestamp_pattern.search(line)
                if not timestamp_match:
                    continue
                    
                timestamp_str = timestamp_match.group(1)
                timestamp = datetime.datetime.fromisoformat(timestamp_str)
                
                # Look for received message lines with tab data
                message_match = self.message_pattern.search(line)
                if not message_match:
                    continue
                
                try:
                    message_count += 1
                    message_text = message_match.group(1)
                    
                    # Use ast.literal_eval to safely parse the Python dictionary representation
                    # This handles the single quotes and escaped backslashes properly
                    try:
                        message_data = ast.literal_eval(message_text)
                    except (SyntaxError, ValueError) as e:
                        error_count += 1
                        if error_count <= 5:  # Only show first few errors
                            print(f"Parse error: {e}")
                            print(f"Problematic text: {message_text[:100]}...")
                        continue
                    
                    # Only process snapshot messages
                    if message_data.get('type') != 'snapshot':
                        continue
                    
                    snapshot_count += 1
                    # Process each tab in the snapshot
                    browser_info = message_data.get('browser', {})
                    browser_name = browser_info.get('name', 'Unknown Browser')
                    
                    tabs = message_data.get('tabs', [])
                    if not tabs and snapshot_count <= 5:
                        print(f"No tabs found in snapshot: {message_text[:100]}...")
                        
                    for tab_data in tabs:
                        tab_count += 1
                        tab_id = tab_data.get('id')
                        if not tab_id:
                            continue
                            
                        url = tab_data.get('url', '')
                        title = tab_data.get('title', '')
                        window_id = tab_data.get('windowId', 0)
                        is_active = tab_data.get('active', False)
                        
                        # Extract domain from URL
                        domain = self.extract_domain(url)
                        
                        # Create or update tab activity
                        if tab_id not in tabs_by_id:
                            tabs_by_id[tab_id] = TabActivity(
                                tab_id=tab_id,
                                window_id=window_id,
                                url=url,
                                title=title,
                                domain=domain,
                                browser_name=browser_name,
                                first_seen=timestamp,
                                last_seen=timestamp,
                                active_periods=[]
                            )
                        else:
                            # Update existing tab if URL or title changed
                            if tabs_by_id[tab_id].url != url or tabs_by_id[tab_id].title != title:
                                tabs_by_id[tab_id].url = url
                                tabs_by_id[tab_id].title = title
                                tabs_by_id[tab_id].domain = domain
                        
                        # Record activity
                        tabs_by_id[tab_id].add_activity(timestamp, is_active)
                        
                except (KeyError, TypeError) as e:
                    error_count += 1
                    if error_count <= 5:  # Only show first few errors
                        print(f"Error processing message: {e}")
                    continue
        
        print(f"Parsing complete: {message_count} messages, {snapshot_count} snapshots, {tab_count} tabs, {error_count} errors")
        
        return tabs_by_id
    
    def analyze_log(self, date_str: Optional[str] = None) -> Dict[int, TabActivity]:
        """
        Analyze log files for the specified date or the most recent log.
        
        Args:
            date_str: Optional date string in YYYY-MM-DD format
            
        Returns:
            Dict[int, TabActivity]: Dictionary of tab activities
        """
        log_files = self.get_log_files(date_str)
        if not log_files:
            raise FileNotFoundError(f"No log files found for date: {date_str or 'any'}")
        
        # Parse the most recent log file (or the specified date)
        self.tabs_by_id = self.parse_log_file(log_files[0])
        return self.tabs_by_id
    
    def get_activity_summary(self) -> pd.DataFrame:
        """
        Get a summary of tab activity as a pandas DataFrame.
        
        Returns:
            pd.DataFrame: Summary of tab activity sorted by active time
        """
        if not self.tabs_by_id:
            return pd.DataFrame()
            
        data = []
        for tab_id, activity in self.tabs_by_id.items():
            data.append({
                'tab_id': tab_id,
                'title': activity.title,
                'url': activity.url,
                'domain': activity.domain,
                'browser': activity.browser_name,
                'first_seen': activity.first_seen,
                'last_seen': activity.last_seen,
                'active_time_seconds': activity.total_active_seconds,
                'active_time_minutes': round(activity.total_active_seconds / 60, 2)
            })
        
        df = pd.DataFrame(data)
        return df.sort_values('active_time_seconds', ascending=False)
    
    def get_domain_summary(self) -> pd.DataFrame:
        """
        Get a summary of activity by domain.
        
        Returns:
            pd.DataFrame: Summary of domain activity sorted by active time
        """
        if not self.tabs_by_id:
            return pd.DataFrame()
            
        # Aggregate activity by domain
        domain_activity = defaultdict(int)
        domain_titles = defaultdict(set)
        domain_browsers = defaultdict(set)
        
        for tab_id, activity in self.tabs_by_id.items():
            domain = activity.domain
            domain_activity[domain] += activity.total_active_seconds
            domain_titles[domain].add(activity.title)
            domain_browsers[domain].add(activity.browser_name)
        
        data = []
        for domain, seconds in domain_activity.items():
            data.append({
                'domain': domain,
                'active_time_seconds': seconds,
                'active_time_minutes': round(seconds / 60, 2),
                'tab_count': len([a for a in self.tabs_by_id.values() if a.domain == domain]),
                'browsers': ', '.join(domain_browsers[domain]),
                'sample_titles': ', '.join(list(domain_titles[domain])[:3])
            })
        
        df = pd.DataFrame(data)
        return df.sort_values('active_time_seconds', ascending=False)


# Example usage
if __name__ == "__main__":
    import sys
    
    # Get today's date in YYYY-MM-DD format
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Parse command line arguments
    date_str = today
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    
    parser = LogActivityParser()
    
    try:
        print(f"Analyzing log activity for {date_str}...")
        parser.analyze_log(date_str)
        
        # Get tab activity summary
        tab_summary = parser.get_activity_summary()
        if tab_summary.empty:
            print("No tab activity found.")
        else:
            print("\n=== Tab Activity Summary ===")
            print(f"Total tabs tracked: {len(tab_summary)}")
            print("\nTop 10 tabs by active time:")
            print(tab_summary[['title', 'domain', 'browser', 'active_time_minutes']].head(10))
        
        # Get domain summary
        domain_summary = parser.get_domain_summary()
        if not domain_summary.empty:
            print("\n=== Domain Activity Summary ===")
            print(f"Total domains: {len(domain_summary)}")
            print("\nTop 10 domains by active time:")
            print(domain_summary[['domain', 'active_time_minutes', 'tab_count']].head(10))
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error analyzing logs: {e}")
