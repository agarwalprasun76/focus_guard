"""
Usage tracker module.

This module provides functionality for tracking browser usage patterns.
"""

import logging
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from focus_guard.core.browser.interfaces import UsageTrackerInterface
from focus_guard.core.browser.models.browser import Browser, BrowserType
from focus_guard.core.browser.models.tab import Tab

logger = logging.getLogger(__name__)


class BrowserUsageTracker(UsageTrackerInterface):
    """Browser usage tracker implementation."""
    
    def __init__(self, storage_dir: str = None):
        """Initialize the browser usage tracker.
        
        Args:
            storage_dir: Directory to store usage data
        """
        self._storage_dir = storage_dir or self._get_default_storage_dir()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}  # browser_id -> session data
        self._domain_usage: Dict[str, Dict[str, float]] = defaultdict(dict)  # domain -> {date -> seconds}
        self._last_active_tab: Optional[Tab] = None
        self._last_active_time: float = time.time()
        
        # Create storage directory if it doesn't exist
        os.makedirs(self._storage_dir, exist_ok=True)
        
        # Load existing usage data
        self._load_usage_data()
    
    def track_active_tab(self, tab: Tab) -> None:
        """Track the active tab.
        
        Args:
            tab: Active tab
        """
        if not tab:
            return
            
        current_time = time.time()
        
        # If there was a previous active tab, update its usage time
        if self._last_active_tab and self._last_active_tab.domain:
            elapsed_seconds = current_time - self._last_active_time
            if elapsed_seconds > 0:
                self._update_domain_usage(self._last_active_tab.domain, elapsed_seconds)
        
        # Update last active tab and time
        self._last_active_tab = tab
        self._last_active_time = current_time
        
        # Log the tab change
        logger.debug(f"Active tab changed to: {tab.url}")
    
    def track_browser_session(self, browser: Browser, is_active: bool) -> None:
        """Track a browser session.
        
        Args:
            browser: Browser instance
            is_active: Whether the browser is active
        """
        if not browser:
            return
            
        current_time = time.time()
        browser_id = browser.id
        
        if is_active:
            # Start or update session
            if browser_id not in self._active_sessions:
                self._active_sessions[browser_id] = {
                    "start_time": current_time,
                    "last_active": current_time,
                    "browser": browser
                }
            else:
                self._active_sessions[browser_id]["last_active"] = current_time
        else:
            # End session
            if browser_id in self._active_sessions:
                session = self._active_sessions[browser_id]
                elapsed_seconds = current_time - session["start_time"]
                
                # Log session end
                logger.debug(f"Browser session ended: {browser.name}, duration: {elapsed_seconds:.2f}s")
                
                # Remove from active sessions
                del self._active_sessions[browser_id]
    
    def get_domain_usage(self, domain: str, days: int = 7) -> Dict[str, float]:
        """Get usage statistics for a domain.
        
        Args:
            domain: Domain to get usage for
            days: Number of days to get usage for
            
        Returns:
            Dict[str, float]: Dictionary mapping date to seconds spent on the domain
        """
        if not domain:
            return {}
            
        domain_lower = domain.lower()
        if domain_lower not in self._domain_usage:
            return {}
            
        # Get usage data for the specified number of days
        usage_data = {}
        today = datetime.now().date()
        
        for i in range(days):
            date_str = (today - timedelta(days=i)).isoformat()
            if date_str in self._domain_usage[domain_lower]:
                usage_data[date_str] = self._domain_usage[domain_lower][date_str]
            else:
                usage_data[date_str] = 0.0
                
        return usage_data
    
    def get_top_domains(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the top domains by usage.
        
        Args:
            days: Number of days to get usage for
            limit: Maximum number of domains to return
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries with domain and usage data
        """
        # Get usage data for all domains
        domain_totals = {}
        today = datetime.now().date()
        
        for domain, dates in self._domain_usage.items():
            total_seconds = 0.0
            
            for i in range(days):
                date_str = (today - timedelta(days=i)).isoformat()
                if date_str in dates:
                    total_seconds += dates[date_str]
                    
            if total_seconds > 0:
                domain_totals[domain] = total_seconds
        
        # Sort domains by usage
        sorted_domains = sorted(domain_totals.items(), key=lambda x: x[1], reverse=True)
        
        # Return top domains
        top_domains = []
        for domain, total_seconds in sorted_domains[:limit]:
            top_domains.append({
                "domain": domain,
                "total_seconds": total_seconds,
                "daily_average": total_seconds / days,
                "usage_by_date": self.get_domain_usage(domain, days)
            })
            
        return top_domains
    
    def save_usage_data(self) -> bool:
        """Save usage data to disk.
        
        Returns:
            bool: True if data was saved successfully
        """
        try:
            # Save domain usage data
            usage_file = os.path.join(self._storage_dir, "domain_usage.json")
            with open(usage_file, "w") as f:
                json.dump(self._domain_usage, f)
                
            logger.debug("Usage data saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving usage data: {e}")
            return False
    
    def _load_usage_data(self) -> None:
        """Load usage data from disk."""
        try:
            # Load domain usage data
            usage_file = os.path.join(self._storage_dir, "domain_usage.json")
            if os.path.exists(usage_file):
                with open(usage_file, "r") as f:
                    self._domain_usage = defaultdict(dict, json.load(f))
                    
                logger.debug("Usage data loaded successfully")
        except Exception as e:
            logger.error(f"Error loading usage data: {e}")
    
    def _update_domain_usage(self, domain: str, seconds: float) -> None:
        """Update usage time for a domain.
        
        Args:
            domain: Domain to update
            seconds: Seconds spent on the domain
        """
        if not domain or seconds <= 0:
            return
            
        domain_lower = domain.lower()
        today = datetime.now().date().isoformat()
        
        # Update domain usage
        if today in self._domain_usage[domain_lower]:
            self._domain_usage[domain_lower][today] += seconds
        else:
            self._domain_usage[domain_lower][today] = seconds
    
    def _get_default_storage_dir(self) -> str:
        """Get the default storage directory.
        
        Returns:
            str: Default storage directory
        """
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Navigate up to the project root and then to the data directory
        project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        storage_dir = os.path.join(project_root, "data", "browser_usage")
        
        return storage_dir
