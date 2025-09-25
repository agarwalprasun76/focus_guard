#!/usr/bin/env python
"""
FocusGuard Enhanced Log Activity Parser

This module provides functionality to analyze browser tab activity from FocusGuard debug logs
with enhanced accuracy by integrating with the activity monitor to determine when
a browser is truly in the foreground.
"""

import os
import re
import ast
import glob
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

# Import text utilities for safe console output
try:
    from core.utils.text_utils import sanitize_console_output
except ImportError:
    # Fallback if text_utils is not available
    def sanitize_console_output(text):
        if isinstance(text, str):
            return text.encode('ascii', 'replace').decode('ascii')
        return str(text)

from collections import defaultdict
from urllib.parse import urlparse

# Import activity monitor components
try:
    from core.activity_monitor.activity_monitor import ActivityMonitor
    from utils.cross_platform import get_active_window_info
    ACTIVITY_MONITOR_AVAILABLE = True
except ImportError:
    ACTIVITY_MONITOR_AVAILABLE = False


@dataclass
class TabActivity:
    """Represents a browser tab's activity over time."""
    tab_id: int
    window_id: int
    url: str
    title: str
    domain: str
    browser_name: str
    first_seen: datetime
    last_seen: datetime
    active_periods: List[Tuple[datetime, datetime]]
    foreground_periods: List[Tuple[datetime, datetime]] = None
    total_active_seconds: int = 0
    total_foreground_seconds: int = 0
    
    def __post_init__(self):
        if self.foreground_periods is None:
            self.foreground_periods = []
    
    def add_activity(self, timestamp: datetime, is_active: bool, is_foreground: bool = False):
        """
        Add an activity record for this tab.
        
        Args:
            timestamp: The timestamp of the activity
            is_active: Whether the tab is active in the browser
            is_foreground: Whether the browser is in the foreground
        """
        self.last_seen = timestamp
        
        # If this is an active tab, record the activity period
        if is_active:
            # If we have active periods and the last one is recent (within 10 seconds),
            # extend the last period instead of creating a new one
            if self.active_periods and (timestamp - self.active_periods[-1][1]).total_seconds() < 10:
                self.active_periods[-1] = (self.active_periods[-1][0], timestamp)
            else:
                self.active_periods.append((timestamp, timestamp))
            
            # If the browser is in the foreground, record the foreground period
            if is_foreground:
                if self.foreground_periods and (timestamp - self.foreground_periods[-1][1]).total_seconds() < 10:
                    self.foreground_periods[-1] = (self.foreground_periods[-1][0], timestamp)
                else:
                    self.foreground_periods.append((timestamp, timestamp))
            
            # Update total active time
            self.calculate_active_time()
    
    def calculate_active_time(self):
        """Calculate the total active time for this tab."""
        # Calculate browser active time
        total_seconds = 0
        for start, end in self.active_periods:
            # Add 5 seconds for each activity period (default interval)
            period_seconds = max(5, (end - start).total_seconds())
            total_seconds += period_seconds
        
        self.total_active_seconds = total_seconds
        
        # Calculate foreground active time
        foreground_seconds = 0
        for start, end in self.foreground_periods:
            # Add 5 seconds for each foreground period (default interval)
            period_seconds = max(5, (end - start).total_seconds())
            foreground_seconds += period_seconds
        
        self.total_foreground_seconds = foreground_seconds


class EnhancedLogParser:
    """Enhanced parser for FocusGuard debug logs to analyze tab activity with foreground detection."""
    
    def __init__(self):
        """Initialize the enhanced log activity parser."""
        self.local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
        self.output_dir = os.path.join(self.local_appdata, "FocusGuard")
        self.tabs_by_id = {}  # Dictionary of tab activities indexed by tab_id
        self.timestamp_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)')
        self.message_pattern = re.compile(r'Received message: ({.*})')
        
        # Initialize activity monitor if available
        self.activity_monitor = ActivityMonitor() if ACTIVITY_MONITOR_AVAILABLE else None
        
        # Browser process name patterns
        self.browser_patterns = {
            'chrome': ['chrome.exe', 'googlechrome.exe'],
            'edge': ['msedge.exe', 'microsoftedge.exe'],
            'firefox': ['firefox.exe'],
            'safari': ['safari.exe'],
            'opera': ['opera.exe'],
            'brave': ['brave.exe']
        }
    
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
    
    def is_browser_in_foreground(self, active_window_info: Dict) -> bool:
        """
        Determine if a browser is in the foreground based on active window info.
        
        Args:
            active_window_info: Dictionary with active window information
            
        Returns:
            bool: True if a browser is in the foreground, False otherwise
        """
        if not active_window_info:
            return False
            
        app_name = active_window_info.get('app_name', '').lower()
        
        # Check if the active window is a known browser
        for browser, patterns in self.browser_patterns.items():
            if any(pattern in app_name for pattern in patterns):
                return True
                
        return False
    
    def parse_log_file(self, file_path: str, activity_log_path: Optional[str] = None) -> Dict[int, TabActivity]:
        """
        Parse a debug log file and extract tab activity information.
        
        Args:
            file_path: Path to the debug log file
            activity_log_path: Optional path to an activity log file for foreground detection
            
        Returns:
            Dict[int, TabActivity]: Dictionary of tab activities indexed by tab_id
        """
        tabs_by_id = {}
        message_count = 0
        snapshot_count = 0
        tab_count = 0
        error_count = 0
        print(f"Parsing log file: {file_path}")
        
        # Load activity log if available
        activity_data = {}
        if activity_log_path and os.path.exists(activity_log_path):
            try:
                activity_data = self.load_activity_log(activity_log_path)
                print(f"Loaded activity data from {activity_log_path}")
            except Exception as e:
                print(f"Error loading activity log: {e}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Extract timestamp
                timestamp_match = self.timestamp_pattern.search(line)
                if not timestamp_match:
                    continue
                    
                timestamp_str = timestamp_match.group(1)
                timestamp = datetime.fromisoformat(timestamp_str)
                
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
                    
                    # Check if browser is in foreground at this timestamp
                    is_browser_foreground = False
                    
                    # Find the closest timestamp in activity data (within 5 seconds)
                    closest_timestamp = None
                    min_diff = float('inf')
                    
                    for activity_timestamp in activity_data:
                        try:
                            activity_time = datetime.fromisoformat(activity_timestamp)
                            diff = abs((timestamp - activity_time).total_seconds())
                            
                            if diff < min_diff and diff <= 5:  # Within 5 seconds
                                min_diff = diff
                                closest_timestamp = activity_timestamp
                        except ValueError:
                            continue
                    
                    if closest_timestamp and activity_data.get(closest_timestamp):
                        is_browser_foreground = True
                        if snapshot_count % 50 == 0:  # Log every 50th match to avoid excessive output
                            print(f"Browser foreground match: {timestamp_str} ~ {closest_timestamp} (diff: {min_diff:.2f}s)")

                    
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
                        
                        # Record activity with foreground status
                        tabs_by_id[tab_id].add_activity(
                            timestamp, 
                            is_active, 
                            is_foreground=(is_active and is_browser_foreground)
                        )
                        
                except (KeyError, TypeError) as e:
                    error_count += 1
                    if error_count <= 5:  # Only show first few errors
                        print(f"Error processing message: {e}")
                    continue
        
        print(f"Parsing complete: {message_count} messages, {snapshot_count} snapshots, {tab_count} tabs, {error_count} errors")
        
        return tabs_by_id
    
    def load_activity_log(self, activity_log_path: str) -> Dict[str, Dict]:
        """
        Load an activity log file with foreground application data.
        
        Args:
            activity_log_path: Path to the activity log file
            
        Returns:
            Dict[str, Dict]: Dictionary mapping timestamps to activity data
        """
        activity_data = {}
        app_usage = defaultdict(lambda: {'total_time': 0, 'entries': 0, 'avg_screen_percent': 0.0})
        last_timestamp = None
        
        with open(activity_log_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 3:  # At least timestamp, app_name, window_title
                    timestamp_str = parts[0].strip()
                    app_name = parts[1].strip()
                    window_title = parts[2].strip()
                    
                    # Get screen percentage if available (newer log format)
                    screen_percent = 0.0
                    if len(parts) >= 4:
                        try:
                            screen_percent = float(parts[3].strip())
                        except ValueError:
                            screen_percent = 0.0
                    
                    # Check if this is a browser
                    is_browser = False
                    for browser, patterns in self.browser_patterns.items():
                        if any(pattern.lower() in app_name.lower() for pattern in patterns):
                            is_browser = True
                            break
                    
                    # Debug output for browser activity
                    if is_browser:
                        print(sanitize_console_output(f"Found browser activity: {timestamp_str} - {app_name}"))
                    
                    # Store activity data with full info
                    activity_data[timestamp_str] = {
                        'is_browser': is_browser,
                        'app_name': app_name,
                        'window_title': window_title,
                        'screen_percent': screen_percent
                    }
                    
                    # Track app usage statistics
                    # Update app usage stats
                    app_usage[app_name]['entries'] += 1
                    
                    # Update running average of screen percentage
                    current_avg = app_usage[app_name]['avg_screen_percent']
                    current_entries = app_usage[app_name]['entries']
                    
                    # Calculate new average
                    if current_entries > 1:
                        # Weighted average: ((avg * (n-1)) + new_value) / n
                        new_avg = ((current_avg * (current_entries - 1)) + screen_percent) / current_entries
                    else:
                        new_avg = screen_percent
                    
                    app_usage[app_name]['avg_screen_percent'] = new_avg
                    
                    # Calculate time difference with previous entry if applicable
                    if last_timestamp:
                        try:
                            last_time = datetime.fromisoformat(last_timestamp)
                            current_time = datetime.fromisoformat(timestamp_str)
                            time_diff = (current_time - last_time).total_seconds()
                            
                            # Only count reasonable time differences (< 30 seconds)
                            if 0 < time_diff < 30:
                                app_usage[app_name]['total_time'] += time_diff
                        except (ValueError, TypeError):
                            pass
                    last_timestamp = timestamp_str
        
        # Store app usage statistics for later use
        self.app_usage = app_usage
        
        print(f"Loaded {len(activity_data)} activity log entries, {sum(1 for v in activity_data.values() if v.get('is_browser'))} browser entries")
        return activity_data
    
    def analyze_log(self, date_str: Optional[str] = None, activity_log_path: Optional[str] = None) -> Dict[int, TabActivity]:
        """
        Analyze log files for the specified date or the most recent log.
        
        Args:
            date_str: Optional date string in YYYY-MM-DD format
            activity_log_path: Optional path to an activity log file for foreground detection
            
        Returns:
            Dict[int, TabActivity]: Dictionary of tab activities
        """
        log_files = self.get_log_files(date_str)
        if not log_files:
            raise FileNotFoundError(f"No log files found for date: {date_str or 'any'}")
        
        # Parse the most recent log file (or the specified date)
        self.tabs_by_id = self.parse_log_file(log_files[0], activity_log_path)
        return self.tabs_by_id
    
    def get_activity_summary(self, use_foreground_time: bool = False) -> pd.DataFrame:
        """
        Get a summary of tab activity as a pandas DataFrame.
        
        Args:
            use_foreground_time: If True, use foreground time instead of active time
            
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
                'active_time_seconds': activity.total_foreground_seconds if use_foreground_time else activity.total_active_seconds,
                'active_time_minutes': round((activity.total_foreground_seconds if use_foreground_time else activity.total_active_seconds) / 60, 2),
                'foreground_time_seconds': activity.total_foreground_seconds,
                'foreground_time_minutes': round(activity.total_foreground_seconds / 60, 2),
                'browser_active_time_seconds': activity.total_active_seconds,
                'browser_active_time_minutes': round(activity.total_active_seconds / 60, 2)
            })
        
        df = pd.DataFrame(data)
        return df.sort_values('active_time_seconds', ascending=False)
    
    def get_domain_summary(self, use_foreground_time: bool = False) -> pd.DataFrame:
        """
        Get a summary of activity by domain.
        
        Args:
            use_foreground_time: If True, use foreground time instead of active time
            
        Returns:
            pd.DataFrame: Summary of domain activity sorted by active time
        """
        if not self.tabs_by_id:
            return pd.DataFrame()
            
        # Aggregate activity by domain
        domain_activity = defaultdict(int)
        domain_foreground = defaultdict(int)
        domain_titles = defaultdict(set)
        domain_browsers = defaultdict(set)
        
        for tab_id, activity in self.tabs_by_id.items():
            domain = activity.domain
            domain_activity[domain] += activity.total_active_seconds
            domain_foreground[domain] += activity.total_foreground_seconds
            domain_titles[domain].add(activity.title)
            domain_browsers[domain].add(activity.browser_name)
        
        data = []
        for domain in domain_activity:
            data.append({
                'domain': domain,
                'active_time_seconds': domain_foreground[domain] if use_foreground_time else domain_activity[domain],
                'active_time_minutes': round((domain_foreground[domain] if use_foreground_time else domain_activity[domain]) / 60, 2),
                'foreground_time_seconds': domain_foreground[domain],
                'foreground_time_minutes': round(domain_foreground[domain] / 60, 2),
                'browser_active_time_seconds': domain_activity[domain],
                'browser_active_time_minutes': round(domain_activity[domain] / 60, 2),
                'tab_count': len([a for a in self.tabs_by_id.values() if a.domain == domain]),
                'browsers': ', '.join(domain_browsers[domain]),
                'sample_titles': ', '.join(list(domain_titles[domain])[:3])
            })
        
        df = pd.DataFrame(data)
        return df.sort_values('active_time_seconds', ascending=False)
        
    def get_application_summary(self) -> pd.DataFrame:
        """
        Get a summary of all application activity (not just browsers).
        
        Returns:
            pd.DataFrame: Summary of application activity sorted by total time
        """
        if not hasattr(self, 'app_usage') or not self.app_usage:
            return pd.DataFrame()
        
        # Convert app usage dictionary to DataFrame
        app_data = []
        for app_name, stats in self.app_usage.items():
            # Check if this is a browser
            is_browser = False
            for browser, patterns in self.browser_patterns.items():
                if any(pattern.lower() in app_name.lower() for pattern in patterns):
                    is_browser = True
                    break
                    
            app_data.append({
                'app_name': app_name,
                'total_time_seconds': stats['total_time'],
                'total_time_minutes': stats['total_time'] / 60,
                'entries': stats['entries'],
                'avg_screen_percent': stats['avg_screen_percent'] * 100,  # Convert to percentage
                'is_browser': is_browser
            })
        
        # Convert to DataFrame
        df = pd.DataFrame(app_data)
        
        # Sort by total time
        df = df.sort_values(by='total_time_seconds', ascending=False).reset_index(drop=True)
        
        return df


# Example usage
if __name__ == "__main__":
    import sys
    
    # Get today's date in YYYY-MM-DD format
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Parse command line arguments
    date_str = today
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    
    activity_log_path = None
    if len(sys.argv) > 2:
        activity_log_path = sys.argv[2]
    
    parser = EnhancedLogParser()
    
    try:
        print(f"Analyzing log activity for {date_str}...")
        parser.analyze_log(date_str, activity_log_path)
        
        # Get tab activity summary
        tab_summary = parser.get_activity_summary(use_foreground_time=True)
        if tab_summary.empty:
            print("No tab activity found.")
        else:
            print("\n=== Tab Activity Summary (Foreground Time) ===")
            print(f"Total tabs tracked: {len(tab_summary)}")
            print("\nTop 10 tabs by foreground time:")
            print(tab_summary[['title', 'domain', 'browser', 'foreground_time_minutes', 'browser_active_time_minutes']].head(10))
        
        # Get domain summary
        domain_summary = parser.get_domain_summary(use_foreground_time=True)
        if not domain_summary.empty:
            print("\n=== Domain Activity Summary (Foreground Time) ===")
            print(f"Total domains: {len(domain_summary)}")
            print("\nTop 10 domains by foreground time:")
            print(domain_summary[['domain', 'foreground_time_minutes', 'browser_active_time_minutes', 'tab_count']].head(10))
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error analyzing logs: {e}")
        import traceback
        traceback.print_exc()
