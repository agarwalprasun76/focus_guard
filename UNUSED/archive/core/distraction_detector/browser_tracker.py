"""
Browser Tab Tracker

This module tracks browser tabs and their productivity status.
It maintains a state dictionary of browser tabs and their domains.
It can integrate with browser extensions for more accurate tab tracking.
"""

from typing import Dict, List, Set, Optional, Tuple
import re
import time
import threading

from core.domain_classifier.domain_classifier import classify_domain
from core.domain_classifier.domain_utils import extract_domain_from_url, normalize_domain
from core.logger.logger import get_logger

class BrowserTabTracker:
    """Tracks browser tabs and their productivity status."""
    
    def __init__(self, productive_categories=None, distracting_categories=None, domain_whitelist=None):
        """Initialize the browser tab tracker."""
        self.logger = get_logger("browser_tracker")
        
        # Tab tracking state
        self.browser_tabs = {}
        self.last_seen_tabs = set()
        self.current_tabs = set()
        
        # Domain classification
        self.productive_categories = productive_categories or ["work", "education", "productivity", "development", "email"]
        self.distracting_categories = distracting_categories or ["social", "entertainment", "shopping"]
        self.domain_whitelist = domain_whitelist or set()
        
        # URL pattern to extract URLs from window titles
        self.url_pattern = re.compile(r'https?://[^\s/$.?#].[^\s]*')
        
        # Known productivity domains
        self.known_productivity_domains = {
            "mail.google.com": "Gmail",
            "calendar.google.com": "Google Calendar",
            "docs.google.com": "Google Docs",
            "drive.google.com": "Google Drive",
            "sheets.google.com": "Google Sheets",
            "slides.google.com": "Google Slides",
            "meet.google.com": "Google Meet",
            "zoom.us": "Zoom",
            "zoom.com": "Zoom",
            "teams.microsoft.com": "Microsoft Teams",
            "outlook.office.com": "Outlook",
            "github.com": "GitHub",
            "gitlab.com": "GitLab",
            "bitbucket.org": "Bitbucket",
            "stackoverflow.com": "Stack Overflow"
        }
        
        # Known productivity keywords in titles
        self.productivity_keywords = [
            "gmail", "calendar", "docs", "sheets", "slides", "meet", "zoom", 
            "teams", "outlook", "github", "gitlab", "bitbucket", "stackoverflow"
        ]
        
        # Browser extension integration
        self.use_extension = False
        self.extension_integration = None
        
        # Try to initialize extension integration
        try:
            from core.browser_integration.tab_tracker_integration import get_tab_tracker_integration
            self.extension_integration = get_tab_tracker_integration(self)
            self.extension_integration.start()
            self.use_extension = True
            self.logger.info("Browser extension integration enabled")
        except ImportError:
            self.logger.debug("Browser extension integration not available")
        except Exception as e:
            self.logger.error(f"Failed to initialize browser extension integration: {e}")
            self.use_extension = False
    
    def update_tabs(self, window_title: str) -> None:
        """Update the browser tabs based on the window title."""
        # Reset current tabs
        self.current_tabs = set()
        
        # Extract tabs from title
        if " and " in window_title and " more pages" in window_title:
            # Edge format: "Tab Title - Domain and X more pages - Profile - Microsoft Edge"
            main_tab = window_title.split(" and ")[0]
            self._process_tab(main_tab)
            self.current_tabs.add(main_tab)
            
            # We don't have details about other tabs, but we know they exist
            self.logger.debug(f"Multiple tabs detected in Edge: {window_title}")
        else:
            # Single tab or other browser
            self._process_tab(window_title)
            self.current_tabs.add(window_title)
        
        # Detect closed tabs
        closed_tabs = self.last_seen_tabs - self.current_tabs
        for tab in closed_tabs:
            if tab in self.browser_tabs:
                self.logger.debug(f"Tab closed: {tab}")
                del self.browser_tabs[tab]
        
        # Update last seen tabs
        self.last_seen_tabs = self.current_tabs.copy()
    
    def _process_tab(self, tab_title: str) -> None:
        """Process a single tab and update the browser_tabs dictionary."""
        if tab_title in self.browser_tabs:
            # Tab already tracked
            return
            
        # Try to extract domain from tab title
        domain = self._extract_domain_from_title(tab_title)
        
        if domain:
            # Determine if domain is productive
            is_productive = self._is_productive_domain(domain)
            
            # Add to browser tabs
            self.browser_tabs[tab_title] = {
                "domain": domain,
                "is_productive": is_productive,
                "first_seen": time.time()
            }
            
            self.logger.debug(f"New tab: {tab_title}, Domain: {domain}, Productive: {is_productive}")
        else:
            # Check for productivity keywords in title
            is_productive = any(keyword in tab_title.lower() for keyword in self.productivity_keywords)
            
            # Add to browser tabs with unknown domain
            self.browser_tabs[tab_title] = {
                "domain": None,
                "is_productive": is_productive,
                "first_seen": time.time()
            }
            
            self.logger.debug(f"New tab with unknown domain: {tab_title}, Productive: {is_productive}")
    
    def _extract_domain_from_title(self, title: str) -> Optional[str]:
        """Extract domain from window title."""
        # Try to find URL directly in title first
        match = self.url_pattern.search(title)
        if match:
            url = match.group(0)
            return extract_domain_from_url(url)
        
        # Handle Edge's complex titles
        if ' - ' in title:
            # Format: "Page Title - Domain - Browser"
            parts = title.split(' - ')
            if len(parts) >= 2:
                domain_part = parts[-2]
                if '.' in domain_part and not domain_part.startswith('http'):
                    domain = normalize_domain(domain_part)
                    if domain:
                        return domain
                
                # Check for known services in any part
                for part in parts:
                    part_lower = part.lower()
                    if 'gmail' in part_lower:
                        return "mail.google.com"
                    elif 'calendar' in part_lower and 'google' in part_lower:
                        return "calendar.google.com"
                    elif 'docs' in part_lower and 'google' in part_lower:
                        return "docs.google.com"
                    elif 'meet' in part_lower and 'google' in part_lower:
                        return "meet.google.com"
                    elif 'zoom' in part_lower:
                        return "zoom.us"
                    elif 'teams' in part_lower:
                        return "teams.microsoft.com"
        
        # Check for email addresses
        if '@gmail.com' in title:
            return "mail.google.com"
        elif '@outlook.com' in title or '@office.com' in title:
            return "outlook.office.com"
            
        return None
    
    def _is_productive_domain(self, domain: str) -> bool:
        """Determine if a domain is productive."""
        # Check whitelist
        if domain in self.domain_whitelist:
            return True
            
        # Check known productivity domains
        if domain in self.known_productivity_domains:
            return True
            
        # Check parent domains
        parts = domain.split('.')
        for i in range(1, len(parts)):
            parent = '.'.join(parts[i:])
            if parent in self.domain_whitelist or parent in self.known_productivity_domains:
                return True
        
        # Check domain category
        category = classify_domain(domain)
        if category:
            if category in self.productive_categories:
                return True
            if category in self.distracting_categories:
                return False
        
        # Default to not productive if we can't determine
        return False
    
    def is_current_tab_productive(self, window_title: str) -> bool:
        """Check if the current tab is productive."""
        # If browser extension is available and connected, use it first
        if self.use_extension and self.extension_integration:
            if self.extension_integration.is_extension_connected():
                active_tab = self.extension_integration.get_active_tab()
                if active_tab:
                    url = active_tab.get("url")
                    if url:
                        domain = extract_domain_from_url(url)
                        if domain:
                            self.logger.debug(f"Using extension data for active tab: {domain}")
                            return self._is_productive_domain(domain)
        
        # Fall back to window title parsing if extension not available or no data
        # Update tabs first
        self.update_tabs(window_title)
        
        # Check if we have info about this tab
        if window_title in self.browser_tabs:
            return self.browser_tabs[window_title].get('is_productive', False)
        
        # Try to extract domain from title
        domain = self._extract_domain_from_title(window_title)
        if domain:
            return self._is_productive_domain(domain)
        
        # Check for productivity keywords in title
        lower_title = window_title.lower()
        return any(keyword in lower_title for keyword in self.productivity_keywords)
        
    def get_active_tab_info(self) -> dict:
        """Get detailed information about the currently active browser tab.
        
        Returns:
            dict: Information about the active tab including URL, title, domain, and productivity status
        """
        # Try to get active tab from browser extension first
        if self.use_extension and self.extension_integration:
            if self.extension_integration.is_extension_connected():
                active_tab = self.extension_integration.get_active_tab()
                if active_tab:
                    url = active_tab.get("url", "Unknown")
                    title = active_tab.get("title", "Unknown")
                    domain = extract_domain_from_url(url) if url and url != "Unknown" else "Unknown"
                    is_productive = self._is_productive_domain(domain) if domain and domain != "Unknown" else False
                    
                    self.logger.debug(f"Active tab from extension: {title} ({domain})")
                    
                    return {
                        "url": url,
                        "title": title,
                        "domain": domain,
                        "is_productive": is_productive,
                        "source": "extension"
                    }
        
        # Fall back to window title parsing if extension not available
        # This is less accurate as we can only see the currently focused window
        from core.cross_platform.cross_platform import get_active_window_info
        
        active_window = get_active_window_info()
        app_name = active_window.get("app_name", "").lower()
        window_title = active_window.get("window_title", "")
        
        browsers = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'iexplore.exe', 'safari.exe', 'opera.exe', 'brave.exe']
        
        if any(browser in app_name for browser in browsers) and window_title:
            # Update tabs with this window title
            self.update_tabs(window_title)
            
            # Try to extract domain from title
            domain = self._extract_domain_from_title(window_title)
            is_productive = self._is_productive_domain(domain) if domain else False
            
            # If we couldn't extract a domain, check for productivity keywords
            if not domain:
                lower_title = window_title.lower()
                is_productive = any(keyword in lower_title for keyword in self.productivity_keywords)
            
            self.logger.debug(f"Active tab from window title: {window_title}")
            
            return {
                "url": None,  # We can't reliably extract URLs from window titles
                "title": window_title,
                "domain": domain or "Unknown",
                "is_productive": is_productive,
                "source": "window_title"
            }
        
        # No browser window is active
        return {
            "url": None,
            "title": None,
            "domain": None,
            "is_productive": False,
            "source": None
        }
    
    def get_tab_info(self) -> Dict:
        """Get information about all tracked tabs."""
        return self.browser_tabs
