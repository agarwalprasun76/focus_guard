"""
Activity Log Parser for Focus Guard.

This module provides functionality to parse and correlate application and browser activity logs,
enabling analysis of user activity patterns and focus metrics.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Iterator, Union

from core_v2.activity.models import ActivityEvent
from core_v2.domain.models import URL, Domain


class ActivityLogParser:
    """
    Parser for activity logs that correlates application and browser activity.
    
    This class provides functionality to:
    1. Parse application and browser activity logs
    2. Correlate activities based on timestamps
    3. Generate activity timelines and summaries
    4. Calculate focus metrics and statistics
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize the activity log parser.
        
        Args:
            log_dir: Directory containing log files (defaults to %LOCALAPPDATA%/FocusGuard)
        """
        # Set up logging directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            import os
            local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
            self.log_dir = Path(local_appdata) / "FocusGuard"
            
        # Configure logger
        self.logger = logging.getLogger("activity_parser")
        self._configure_logger()
    
    def _configure_logger(self):
        """Configure the logger with appropriate handlers and format."""
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
    
    def get_available_dates(self) -> List[str]:
        """
        Get a list of dates for which activity logs are available.
        
        Returns:
            List[str]: List of dates in YYYY-MM-DD format
        """
        dates = set()
        
        # Check application logs
        for log_file in self.log_dir.glob("activity_log_*.log"):
            try:
                date_str = log_file.stem.split('_')[-1]
                datetime.strptime(date_str, "%Y-%m-%d")  # Validate format
                dates.add(date_str)
            except (ValueError, IndexError):
                continue
        
        # Check browser logs
        for log_file in self.log_dir.glob("browser_activity_*.log"):
            try:
                date_str = log_file.stem.split('_')[-1]
                datetime.strptime(date_str, "%Y-%m-%d")  # Validate format
                dates.add(date_str)
            except (ValueError, IndexError):
                continue
        
        return sorted(list(dates))
    
    def get_log_paths_for_date(self, date_str: str) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Get the paths to application and browser logs for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Tuple[Optional[Path], Optional[Path]]: Paths to application and browser logs
        """
        app_log = self.log_dir / f"activity_log_{date_str}.log"
        browser_log = self.log_dir / f"browser_activity_{date_str}.log"
        
        app_log = app_log if app_log.exists() else None
        browser_log = browser_log if browser_log.exists() else None
        
        return app_log, browser_log
    
    def load_app_activity(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Load application activity data for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            List[Dict[str, Any]]: List of application activity events
        """
        app_log, _ = self.get_log_paths_for_date(date_str)
        if not app_log:
            self.logger.warning(f"No application activity log found for {date_str}")
            return []
        
        try:
            # Try JSON format first
            json_log = app_log.with_suffix('.json')
            if json_log.exists():
                with open(json_log, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("events", [])
            
            # Fall back to parsing log file
            events = []
            with open(app_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
            
            return events
        except Exception as e:
            self.logger.error(f"Error loading application activity: {e}")
            return []
    
    def load_browser_activity(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Load browser activity data for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            List[Dict[str, Any]]: List of browser activity events
        """
        _, browser_log = self.get_log_paths_for_date(date_str)
        if not browser_log:
            self.logger.warning(f"No browser activity log found for {date_str}")
            return []
        
        try:
            # Try JSON format first
            json_log = browser_log.with_suffix('.json')
            if json_log.exists():
                with open(json_log, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("events", [])
            
            # Fall back to parsing log file
            events = []
            with open(browser_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
            
            return events
        except Exception as e:
            self.logger.error(f"Error loading browser activity: {e}")
            return []
    
    def correlate_activities(self, date_str: str, time_window_seconds: int = 5) -> List[Dict[str, Any]]:
        """
        Correlate application and browser activities for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            time_window_seconds: Time window in seconds for correlating activities
            
        Returns:
            List[Dict[str, Any]]: List of correlated activity events
        """
        app_events = self.load_app_activity(date_str)
        browser_events = self.load_browser_activity(date_str)
        
        if not app_events and not browser_events:
            self.logger.warning(f"No activity data found for {date_str}")
            return []
        
        # Sort events by timestamp
        app_events.sort(key=lambda x: x.get("timestamp", ""))
        browser_events.sort(key=lambda x: x.get("timestamp", ""))
        
        correlated_events = []
        
        # Process application events
        for app_event in app_events:
            app_time = datetime.fromisoformat(app_event.get("timestamp", ""))
            
            # Find browser events within the time window
            matching_browser_events = []
            for browser_event in browser_events:
                browser_time = datetime.fromisoformat(browser_event.get("timestamp", ""))
                time_diff = abs((browser_time - app_time).total_seconds())
                
                if time_diff <= time_window_seconds:
                    matching_browser_events.append(browser_event)
            
            # Create correlated event
            correlated_event = {
                "timestamp": app_event.get("timestamp"),
                "app_activity": app_event,
                "browser_activities": matching_browser_events,
                "is_browser_app": self._is_browser_app(app_event)
            }
            
            correlated_events.append(correlated_event)
        
        return correlated_events
    
    def generate_activity_timeline(self, date_str: str, time_window_seconds: int = 5) -> List[Dict[str, Any]]:
        """
        Generate a timeline of user activity for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            time_window_seconds: Time window in seconds for correlating activities
            
        Returns:
            List[Dict[str, Any]]: Activity timeline with app and browser info
        """
        correlated_events = self.correlate_activities(date_str, time_window_seconds)
        
        # Group events by application to create activity sessions
        timeline = []
        current_app = None
        session_start = None
        session_browser_activities = []
        
        for event in correlated_events:
            app_name = event["app_activity"].get("app_name", "")
            
            # Start a new session if app changes
            if app_name != current_app:
                # Save the previous session if it exists
                if current_app and session_start:
                    timeline.append({
                        "app_name": current_app,
                        "start_time": session_start,
                        "end_time": event["timestamp"],
                        "duration_seconds": (datetime.fromisoformat(event["timestamp"]) - 
                                           datetime.fromisoformat(session_start)).total_seconds(),
                        "is_browser": event["is_browser_app"],
                        "browser_activities": session_browser_activities
                    })
                
                # Start a new session
                current_app = app_name
                session_start = event["timestamp"]
                session_browser_activities = event["browser_activities"]
            else:
                # Update the current session's browser activities
                session_browser_activities.extend(event["browser_activities"])
        
        # Add the last session
        if current_app and session_start and correlated_events:
            last_event = correlated_events[-1]
            timeline.append({
                "app_name": current_app,
                "start_time": session_start,
                "end_time": last_event["timestamp"],
                "duration_seconds": (datetime.fromisoformat(last_event["timestamp"]) - 
                                   datetime.fromisoformat(session_start)).total_seconds(),
                "is_browser": last_event["is_browser_app"],
                "browser_activities": session_browser_activities
            })
        
        return timeline
    
    def calculate_app_usage_stats(self, date_str: str) -> Dict[str, Any]:
        """
        Calculate application usage statistics for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Dict[str, Any]: Application usage statistics
        """
        timeline = self.generate_activity_timeline(date_str)
        
        # Calculate total time spent in each application
        app_usage = {}
        total_time = 0
        
        for session in timeline:
            app_name = session["app_name"]
            duration = session["duration_seconds"]
            
            if app_name not in app_usage:
                app_usage[app_name] = 0
            
            app_usage[app_name] += duration
            total_time += duration
        
        # Calculate percentages
        app_percentages = {}
        for app, time_spent in app_usage.items():
            if total_time > 0:
                app_percentages[app] = (time_spent / total_time) * 100
            else:
                app_percentages[app] = 0
        
        # Sort by time spent
        sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "date": date_str,
            "total_time_seconds": total_time,
            "app_usage": app_usage,
            "app_percentages": app_percentages,
            "top_apps": sorted_apps[:5]
        }
    
    def calculate_domain_usage_stats(self, date_str: str) -> Dict[str, Any]:
        """
        Calculate domain usage statistics for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Dict[str, Any]: Domain usage statistics
        """
        timeline = self.generate_activity_timeline(date_str)
        
        # Extract all browser activities
        browser_activities = []
        for session in timeline:
            if session["is_browser"]:
                browser_activities.extend(session["browser_activities"])
        
        # Calculate time spent on each domain
        domain_usage = {}
        total_browser_time = 0
        
        # Process browser activities
        for activity in browser_activities:
            domain = activity.get("domain", "")
            url = activity.get("url", "")
            
            # Skip empty domains
            if not domain and url:
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc
                except:
                    continue
            
            if not domain:
                continue
                
            duration = activity.get("duration_seconds", 0)
            
            if domain not in domain_usage:
                domain_usage[domain] = 0
            
            domain_usage[domain] += duration
            total_browser_time += duration
        
        # Calculate percentages
        domain_percentages = {}
        for domain, time_spent in domain_usage.items():
            if total_browser_time > 0:
                domain_percentages[domain] = (time_spent / total_browser_time) * 100
            else:
                domain_percentages[domain] = 0
        
        # Sort by time spent
        sorted_domains = sorted(domain_usage.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "date": date_str,
            "total_browser_time_seconds": total_browser_time,
            "domain_usage": domain_usage,
            "domain_percentages": domain_percentages,
            "top_domains": sorted_domains[:10]
        }
    
    def _is_browser_app(self, app_event: Dict[str, Any]) -> bool:
        """
        Check if an application event is from a web browser.
        
        Args:
            app_event: Application activity event
            
        Returns:
            bool: True if the application is a web browser, False otherwise
        """
        app_name = app_event.get("app_name", "").lower()
        browsers = ["chrome", "firefox", "msedge", "edge", "opera", "safari", "brave"]
        return any(browser in app_name for browser in browsers)


# Singleton instance
_parser_instance = None

def get_activity_parser(**kwargs) -> ActivityLogParser:
    """
    Get the singleton activity parser instance.
    
    Args:
        **kwargs: Arguments to pass to the ActivityLogParser constructor
        
    Returns:
        ActivityLogParser: The singleton instance
    """
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = ActivityLogParser(**kwargs)
    return _parser_instance


def get_activity_timeline(date_str: str, time_window_seconds: int = 5) -> List[Dict[str, Any]]:
    """
    Generate a timeline of user activity for a specific date.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        time_window_seconds: Time window in seconds for correlating activities
        
    Returns:
        List[Dict[str, Any]]: Activity timeline with app and browser info
    """
    parser = get_activity_parser()
    return parser.generate_activity_timeline(date_str, time_window_seconds)


def get_app_usage_stats(date_str: str) -> Dict[str, Any]:
    """
    Calculate application usage statistics for a specific date.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        Dict[str, Any]: Application usage statistics
    """
    parser = get_activity_parser()
    return parser.calculate_app_usage_stats(date_str)


def get_domain_usage_stats(date_str: str) -> Dict[str, Any]:
    """
    Calculate domain usage statistics for a specific date.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        Dict[str, Any]: Domain usage statistics
    """
    parser = get_activity_parser()
    return parser.calculate_domain_usage_stats(date_str)
