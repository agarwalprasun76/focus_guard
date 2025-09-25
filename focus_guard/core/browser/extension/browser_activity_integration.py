"""
Browser Activity Integration

This module integrates the browser extension with the activity tracking system.
It provides functionality for forwarding browser events to the activity system
and ensuring proper domain classification and usage tracking.
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class BrowserActivityIntegration:
    """
    Integration between browser extensions and the activity tracking system.
    
    This class provides methods for:
    - Forwarding browser events to the activity system
    - Processing tab snapshots from the native messaging host
    - Classifying domains based on Focus Guard categories
    - Tracking browser usage for activity reporting
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize the BrowserActivityIntegration.
        
        Args:
            output_dir: Directory where native host outputs tab snapshots.
                       If None, the default directory is used.
        """
        self._output_dir = output_dir or self._get_default_output_dir()
        self._activity_monitor = None
        self._tab_monitor = None
        self._domain_classifier = None
        
    def _get_default_output_dir(self) -> str:
        """
        Get the default output directory for native host files.
        
        Returns:
            str: Path to the output directory
        """
        if os.name == "nt":  # Windows
            local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
            return os.path.join(local_appdata, "FocusGuard")
        else:  # Unix-like systems
            home_dir = os.path.expanduser("~")
            return os.path.join(home_dir, ".focusguard")
    
    @property
    def activity_monitor(self):
        """
        Get the activity monitor instance.
        
        Returns:
            ActivityMonitor: The activity monitor instance
        """
        if self._activity_monitor is None:
            try:
                from focus_guard.core.activity import ActivityMonitor
                self._activity_monitor = ActivityMonitor()
                logger.info("Activity monitor initialized")
            except ImportError as e:
                logger.warning(f"Activity monitor not available: {e}")
                self._activity_monitor = None
        return self._activity_monitor
    
    @property
    def tab_monitor(self):
        """
        Get the browser tab monitor instance.
        
        Returns:
            BrowserTabMonitor: The browser tab monitor instance
        """
        if self._tab_monitor is None:
            try:
                from focus_guard.core.activity.browser import BrowserTabMonitor
                self._tab_monitor = BrowserTabMonitor()
                logger.info("Tab monitor initialized")
            except ImportError as e:
                logger.warning(f"Tab monitor not available: {e}")
                self._tab_monitor = None
        return self._tab_monitor
    
    @property
    def domain_classifier(self):
        """
        Get the domain classifier instance.
        
        Returns:
            DomainClassifier: The domain classifier instance
        """
        if self._domain_classifier is None:
            try:
                # Import the domain classifier from the appropriate module
                # This is a placeholder for the actual domain classifier
                from focus_guard.core.domain import DomainClassifier
                self._domain_classifier = DomainClassifier()
                logger.info("Domain classifier initialized")
            except ImportError as e:
                logger.warning(f"Domain classifier not available: {e}")
                self._domain_classifier = None
        return self._domain_classifier
    
    def process_tab_snapshots(self) -> Dict[str, Any]:
        """
        Process tab snapshots from the native messaging host.
        
        Returns:
            Dict[str, Any]: Dictionary containing processed tab data
        """
        # Find the most recent snapshot file
        snapshot_file = self._find_latest_snapshot()
        if not snapshot_file:
            logger.warning("No snapshot file found")
            return {}
        
        # Read the snapshot file
        try:
            with open(snapshot_file, "r", encoding="utf-8") as f:
                snapshot_data = json.load(f)
            
            logger.info(f"Loaded tab snapshot from {snapshot_file}")
            return self._process_snapshot_data(snapshot_data)
        except Exception as e:
            logger.error(f"Error processing tab snapshot: {e}")
            return {}
    
    def _find_latest_snapshot(self) -> Optional[str]:
        """
        Find the most recent tab snapshot file.
        
        Returns:
            Optional[str]: Path to the most recent snapshot file, or None if not found
        """
        if not os.path.exists(self._output_dir):
            logger.warning(f"Output directory does not exist: {self._output_dir}")
            return None
        
        # First try to find today's snapshot
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        daily_snapshot = os.path.join(self._output_dir, f"tabs_snapshot_{today_str}.json")
        
        if os.path.exists(daily_snapshot):
            return daily_snapshot
        
        # If today's snapshot doesn't exist, find the most recent snapshot
        snapshot_files = []
        for fname in os.listdir(self._output_dir):
            if fname.startswith("tabs_snapshot_") and fname.endswith(".json"):
                full_path = os.path.join(self._output_dir, fname)
                snapshot_files.append((full_path, os.path.getmtime(full_path)))
        
        if snapshot_files:
            # Sort by modification time (most recent first)
            snapshot_files.sort(key=lambda x: x[1], reverse=True)
            return snapshot_files[0][0]
        
        return None
    
    def _process_snapshot_data(self, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the snapshot data and forward events to the activity system.
        
        Args:
            snapshot_data: Raw snapshot data from the native messaging host
            
        Returns:
            Dict[str, Any]: Processed tab data
        """
        processed_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "browsers": {},
            "total_tabs": 0,
            "active_tabs": [],
            "domains": {}
        }
        
        browsers_data = snapshot_data.get("browsers", {})
        
        for browser_name, browser_data in browsers_data.items():
            tabs = browser_data.get("tabs", [])
            processed_data["total_tabs"] += len(tabs)
            
            # Process tabs for this browser
            browser_info = {
                "name": browser_name,
                "tab_count": len(tabs),
                "active_tab": None,
                "domains": {}
            }
            
            # Process each tab
            for tab in tabs:
                # Extract domain from URL
                url = tab.get("url", "")
                domain = self._extract_domain(url)
                
                # Classify domain if classifier is available
                category = None
                if self.domain_classifier and domain:
                    category = self.domain_classifier.classify_domain(domain)
                
                # Add domain to browser info
                if domain:
                    if domain not in browser_info["domains"]:
                        browser_info["domains"][domain] = {
                            "count": 0,
                            "category": category,
                            "tabs": []
                        }
                    
                    browser_info["domains"][domain]["count"] += 1
                    browser_info["domains"][domain]["tabs"].append(tab)
                    
                    # Add to global domains
                    if domain not in processed_data["domains"]:
                        processed_data["domains"][domain] = {
                            "count": 0,
                            "category": category,
                            "browsers": {}
                        }
                    
                    processed_data["domains"][domain]["count"] += 1
                    if browser_name not in processed_data["domains"][domain]["browsers"]:
                        processed_data["domains"][domain]["browsers"][browser_name] = 0
                    processed_data["domains"][domain]["browsers"][browser_name] += 1
                
                # Check if this is an active tab
                if tab.get("active", False):
                    browser_info["active_tab"] = tab
                    processed_data["active_tabs"].append(tab)
            
            processed_data["browsers"][browser_name] = browser_info
        
        # Forward events to activity system if available
        if self.activity_monitor:
            self._forward_to_activity_system(processed_data)
        
        return processed_data
    
    def _extract_domain(self, url: str) -> str:
        """
        Extract the domain from a URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            str: Domain name
        """
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Remove port if present
            if ":" in domain:
                domain = domain.split(":")[0]
            
            # Remove www. prefix if present
            if domain.startswith("www."):
                domain = domain[4:]
            
            return domain.lower()
        except Exception as e:
            logger.error(f"Error extracting domain from URL {url}: {e}")
            return ""
    
    def _forward_to_activity_system(self, processed_data: Dict[str, Any]):
        """
        Forward browser activity data to the activity tracking system.
        
        Args:
            processed_data: Processed tab data
        """
        try:
            # Create activity events for active tabs
            for tab in processed_data["active_tabs"]:
                url = tab.get("url", "")
                title = tab.get("title", "")
                browser_name = tab.get("browser", "Unknown Browser")
                
                # Create metadata for the activity event
                metadata = {
                    "url": url,
                    "title": title,
                    "browser": browser_name,
                    "tab_id": tab.get("id"),
                    "window_id": tab.get("windowId")
                }
                
                # Extract domain and add to metadata
                domain = self._extract_domain(url)
                if domain:
                    metadata["domain"] = domain
                
                # Add domain category if available
                if self.domain_classifier and domain:
                    category = self.domain_classifier.classify_domain(domain)
                    if category:
                        metadata["category"] = category
                
                # Create the activity event
                self.activity_monitor.create_activity_event(
                    event_type="browser_tab_active",
                    metadata=metadata
                )
                
                logger.debug(f"Created activity event for active tab: {title} ({url})")
        except Exception as e:
            logger.error(f"Error forwarding to activity system: {e}")
    
    def track_browser_usage(self) -> Dict[str, Any]:
        """
        Track browser usage and return statistics.
        
        Returns:
            Dict[str, Any]: Browser usage statistics
        """
        # Process tab snapshots to get current state
        snapshot_data = self.process_tab_snapshots()
        
        # Calculate usage statistics
        usage_stats = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_tabs": snapshot_data.get("total_tabs", 0),
            "active_tabs": len(snapshot_data.get("active_tabs", [])),
            "browsers": {},
            "domains": {},
            "categories": {}
        }
        
        # Process browser statistics
        for browser_name, browser_info in snapshot_data.get("browsers", {}).items():
            usage_stats["browsers"][browser_name] = {
                "tab_count": browser_info.get("tab_count", 0),
                "domain_count": len(browser_info.get("domains", {}))
            }
        
        # Process domain statistics
        for domain, domain_info in snapshot_data.get("domains", {}).items():
            category = domain_info.get("category")
            count = domain_info.get("count", 0)
            
            usage_stats["domains"][domain] = {
                "count": count,
                "category": category
            }
            
            # Aggregate by category if available
            if category:
                if category not in usage_stats["categories"]:
                    usage_stats["categories"][category] = {
                        "count": 0,
                        "domains": []
                    }
                
                usage_stats["categories"][category]["count"] += count
                usage_stats["categories"][category]["domains"].append(domain)
        
        return usage_stats
    
    def close_tab_by_domain(self, domain: str) -> int:
        """
        Close all tabs with the specified domain.
        
        Args:
            domain: Domain to close tabs for
            
        Returns:
            int: Number of tabs closed
        """
        if not self.tab_monitor:
            logger.warning("Tab monitor not available, cannot close tabs")
            return 0
        
        # Get all tabs with the specified domain
        tabs = self.tab_monitor.get_tabs_by_domain(domain)
        closed_count = 0
        
        # Close each tab
        for tab in tabs:
            tab_id = tab.get("tab_id")
            window_id = tab.get("window_id")
            browser_name = tab.get("browser")
            
            if tab_id:
                try:
                    # Use the extension integration to close the tab
                    extension_integration = self.tab_monitor.extension_integration
                    if extension_integration and extension_integration.close_tab(tab_id, window_id, browser_name):
                        closed_count += 1
                        logger.info(f"Closed tab with domain {domain}: {tab.get('title')}")
                except Exception as e:
                    logger.error(f"Error closing tab: {e}")
        
        return closed_count
    
    def close_tab_by_category(self, category: str) -> int:
        """
        Close all tabs with the specified category.
        
        Args:
            category: Category to close tabs for
            
        Returns:
            int: Number of tabs closed
        """
        if not self.domain_classifier:
            logger.warning("Domain classifier not available, cannot close tabs by category")
            return 0
        
        # Process tab snapshots to get current state
        snapshot_data = self.process_tab_snapshots()
        closed_count = 0
        
        # Find domains in the specified category
        domains_to_close = []
        for domain, domain_info in snapshot_data.get("domains", {}).items():
            if domain_info.get("category") == category:
                domains_to_close.append(domain)
        
        # Close tabs for each domain
        for domain in domains_to_close:
            closed_count += self.close_tab_by_domain(domain)
        
        return closed_count
