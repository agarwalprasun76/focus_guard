"""
URL-based distraction detection rule.

This module provides a rule for detecting distractions based on URLs and domains.
It integrates with the domain_classifier to determine if a URL is a distraction.
"""
from typing import Dict, Any, List, Optional
import re

from core.domain_classifier.domain_classifier import classify_domain
from core.domain_classifier.domain_utils import extract_domain_from_url
from core.logger.logger import get_logger

# Try to import browser extension integration
try:
    from core.browser_integration.tab_server import get_tab_server
    HAS_EXTENSION_SUPPORT = True
except ImportError:
    HAS_EXTENSION_SUPPORT = False

# Define DistractionRule interface here to avoid circular imports
class DistractionRule:
    def check(self, active_window, top_windows, state) -> list:
        """Return a list of distraction events or an empty list."""
        raise NotImplementedError

# URL pattern to extract URLs from window titles
URL_PATTERN = re.compile(r'https?://[^\s/$.?#].[^\s]*')

class URLRule(DistractionRule):
    """Rule for detecting distractions based on URLs in window titles."""
    
    def __init__(self, productive_categories=None, distracting_categories=None):
        """
        Initialize the URL rule.
        
        Args:
            productive_categories: List of domain categories considered productive
            distracting_categories: List of domain categories considered distracting
        """
        self.logger = get_logger("url_rule")
        
        # Default productive categories
        self.productive_categories = productive_categories or [
            "work", "education", "productivity", "development", "email"
        ]
        
        # Default distracting categories
        self.distracting_categories = distracting_categories or [
            "social", "entertainment", "shopping"
        ]
        
        # Initialize tab server connection if extension support is available
        self.tab_server = None
        if HAS_EXTENSION_SUPPORT:
            try:
                self.tab_server = get_tab_server()
                self.logger.debug("Browser extension support initialized for URL rule")
            except Exception as e:
                self.logger.debug(f"Could not initialize browser extension support: {e}")
                self.tab_server = None
    
    def check(self, active_window, top_windows, state) -> list:
        """
        Check if the active window contains a distracting URL.
        
        Args:
            active_window: Information about the active window
            top_windows: List of top windows
            state: Current state of the distraction detector
            
        Returns:
            List of distraction events or empty list
        """
        events = []
        
        # Skip if no active window
        if not active_window:
            return events
            
        # Get window title
        window_title = active_window.get('window_title', '')
        if not window_title:
            return events
            
        # Check for browser windows
        app_name = active_window.get('app_name', '').lower()
        if not self._is_browser(app_name):
            return events
            
        # Special case for Microsoft Edge with blank/empty tab
        if 'msedge' in app_name or 'msedge.exe' in app_name:
            self.logger.info(f"Detected Edge window: '{window_title}'")
            # Deliberately use INFO for better visibility in logs
            
            # First try to check with browser extension if available
            if self.tab_server and self.tab_server.is_extension_connected():
                try:
                    # Try to get active tab from extension
                    active_tab = self.tab_server.get_active_tab()
                    if active_tab:
                        url = active_tab.get('url', '')
                        title = active_tab.get('title', '')
                        self.logger.debug(f"Edge extension data - URL: {url}, Title: {title}")
                        
                        # Check for blank tab URLs
                        blank_tab_urls = ['about:blank', 'edge://newtab/', 'edge://new-tab-page/', '']
                        if any(blank_url in url for blank_url in blank_tab_urls):
                            self.logger.debug(f"Ignoring blank Microsoft Edge tab (extension data): {url}")
                            return events
                except Exception as e:
                    self.logger.debug(f"Error checking extension data: {e}")
                    
            self.logger.debug("Using window title fallback for Edge blank tab detection")
            
            # Fallback to window title parsing if extension not available
            # Use our robust blank tab detection method
            if self._is_edge_blank_tab(window_title):
                self.logger.debug(f"Ignoring blank Microsoft Edge window: {window_title}")
                return events
            
        # Extract URL from window title
        url = self._extract_url_from_title(window_title)
        if not url:
            return events
            
        # Extract domain from URL
        domain = extract_domain_from_url(url)
        if not domain:
            return events
            
        # Classify domain
        category = classify_domain(domain)
        
        # Log for debugging
        self.logger.debug(f"URL: {url}, Domain: {domain}, Category: {category}")
        
        # Check if domain is distracting
        if category in self.distracting_categories:
            events.append(f"Distracting website: {domain} (category: {category})")
        elif category in self.productive_categories:
            # This is a productive domain, no distraction
            pass
        elif category:
            # Unknown category but classified
            self.logger.debug(f"Domain {domain} has category {category} (neither productive nor distracting)")
        else:
            # Unclassified domain
            self.logger.debug(f"Unclassified domain: {domain}")
            
        return events
    
    def _is_browser(self, app_name):
        """Check if the app is a known browser."""
        # List of known browser process names
        browsers = [
            'chrome.exe', 'firefox.exe', 'msedge.exe', 'iexplore.exe',
            'safari.exe', 'opera.exe', 'brave.exe', 'chromium'
        ]
        
        # Check if the app name contains any of the browser names
        return any(browser.lower() in app_name.lower() for browser in browsers)
        
    def _is_edge_blank_tab(self, window_title):
        """More robust method to detect if an Edge window is a blank/new tab.
        
        Args:
            window_title: The window title to check
            
        Returns:
            bool: True if this is likely a blank or new tab, False otherwise
        """
        if not window_title:
            self.logger.info("  - Not a blank tab: Empty window title")
            return False
            
        lower_title = window_title.lower()
        self.logger.info(f"  - Checking if blank tab: '{lower_title}'")
        
        # Check for standard blank tab indicators
        blank_indicators = [
            'new tab', 'edge://', 'edge://newtab', 'edge://new-tab-page',
            'start page', 'about:blank', 'microsoft edge start'
        ]
        
        # Check each indicator and log if matched
        for indicator in blank_indicators:
            if indicator in lower_title:
                self.logger.info(f"  - Matched blank indicator: '{indicator}'")
                return True
            
        # Check for "new tab and X more pages" pattern
        if 'new tab and ' in lower_title and ' more pages' in lower_title:
            self.logger.info("  - Matched 'new tab and X more pages' pattern")
            return True
            
        # Check for "microsoft edge" in title without other meaningful content
        if 'microsoft edge' in lower_title:
            # If title is just some variation of "Microsoft Edge", it's likely blank
            meaningful_parts = [p.strip() for p in lower_title.split('-') if p.strip() and 'microsoft edge' not in p]
            self.logger.info(f"  - Title contains 'microsoft edge', meaningful parts: {meaningful_parts}")
            if not meaningful_parts:
                self.logger.info("  - No meaningful parts found, considering as blank tab")
                return True
                
        # If none of the above matched, it's not a blank tab
        self.logger.info("  - Not a blank tab: No patterns matched")
        return False
    
    def _extract_url_from_title(self, title):
        """Extract URL from window title."""
        # Try to find URL directly in title first
        match = URL_PATTERN.search(title)
        if match:
            return match.group(0)
        
        # Handle Edge's complex titles with "and X more pages"
        if ' and ' in title and ' more pages' in title:
            # Try to extract domain from email address
            if '@gmail.com' in title:
                return "https://mail.google.com"
            elif '@outlook.com' in title or '@office.com' in title:
                return "https://outlook.office.com"
            
            # Extract service name before "and X more pages"
            parts = title.split(' and ')[0].split(' - ')
            if len(parts) >= 2:
                last_part = parts[-1].lower()
                if 'gmail' in last_part:
                    return "https://mail.google.com"
                elif 'calendar' in last_part:
                    return "https://calendar.google.com"
                elif 'docs' in last_part:
                    return "https://docs.google.com"
                elif 'meet' in last_part:
                    return "https://meet.google.com"
                elif 'zoom' in last_part:
                    return "https://zoom.us"
                elif 'teams' in last_part:
                    return "https://teams.microsoft.com"
            
        # Common patterns in browser titles
        if ' - ' in title:
            # Format: "Page Title - Domain - Browser"
            parts = title.split(' - ')
            if len(parts) >= 2:
                domain_part = parts[-2]
                if '.' in domain_part and not domain_part.startswith('http'):
                    return f"http://{domain_part}"
                
                # Check for common services in any part
                for part in parts:
                    part_lower = part.lower()
                    if 'gmail' in part_lower:
                        return "https://mail.google.com"
                    elif 'calendar' in part_lower and 'google' in part_lower:
                        return "https://calendar.google.com"
                    elif 'docs' in part_lower and 'google' in part_lower:
                        return "https://docs.google.com"
                    elif 'meet' in part_lower and 'google' in part_lower:
                        return "https://meet.google.com"
                    elif 'zoom' in part_lower:
                        return "https://zoom.us"
                    elif 'teams' in part_lower:
                        return "https://teams.microsoft.com"
                    
        return None
