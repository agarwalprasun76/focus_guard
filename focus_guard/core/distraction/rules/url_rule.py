"""
URL-based distraction rule implementation.

This module provides a rule for detecting distractions based on URLs
in browser windows, leveraging domain classification to determine
if a URL is distracting.
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from focus_guard.core.distraction.interfaces import DistractionRule
from focus_guard.core.distraction.models import DistractionState, DistractionAlert, AlertLevel
from focus_guard.core.distraction.rules.base import BaseDistractionRule
from focus_guard.core.classification.base import ContextAwareClassifier
from focus_guard.core.domain.models import Domain, Category


class URLRule(BaseDistractionRule):
    """
    Rule for detecting distractions based on URLs in browser windows.
    
    This rule checks if the active window contains a URL that is classified
    as a distraction based on its domain category.
    """
    
    def __init__(
        self,
        domain_classifier: ContextAwareClassifier,
        distracting_categories: Optional[List[str]] = None,
        domain_whitelist: Optional[Set[str]] = None,
        rule_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the URL rule.
        
        Args:
            domain_classifier: The domain classifier to use.
            distracting_categories: List of categories considered distracting.
            domain_whitelist: Set of domains to whitelist (never considered distracting).
            rule_config: Optional configuration for the rule.
        """
        super().__init__(rule_config)
        self._domain_classifier = domain_classifier
        self._distracting_categories = distracting_categories or [
            "social", "entertainment", "shopping"
        ]
        self._domain_whitelist = domain_whitelist or set()
        
    @property
    def name(self) -> str:
        """Get the name of the rule."""
        return "URL Rule"
    
    @property
    def description(self) -> str:
        """Get the description of the rule."""
        return "Detects distracting URLs in browser windows."
    
    def should_apply(self, state: DistractionState) -> bool:
        """
        Determine if the rule should be applied to the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            True if the rule should be applied, False otherwise.
        """
        active_window = state.active_window
        if not active_window:
            return False
            
        app_name = active_window.get('app_name', '').lower()
        return self._is_browser(app_name)
    
    def check(self, state: DistractionState) -> List[DistractionAlert]:
        """
        Check for distractions based on the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            A list of distraction alerts, or an empty list if no distractions are detected.
        """
        alerts = []
        active_window = state.active_window
        
        if not active_window:
            return alerts
            
        # Extract URL from window title or browser tabs
        url = self._extract_url_from_window(active_window, state.browser_tabs)
        if not url:
            return alerts
            
        # Extract domain from URL
        domain_str = self._extract_domain_from_url(url)
        if not domain_str:
            return alerts
            
        # Check if domain is whitelisted
        if domain_str in self._domain_whitelist:
            return alerts
            
        # Classify domain
        try:
            domain = Domain(domain_str)
            classification = self._domain_classifier.classify(domain)
            
            # Check if domain is in a distracting category
            category = classification.category
            if category:
                # Map enum names to expected category strings
                category_map = {
                    "SOCIAL_MEDIA": "social",
                    "ENTERTAINMENT": "entertainment",
                    "SHOPPING": "shopping",
                    "GAMING": "entertainment",
                    "ADULT": "entertainment"
                }
                category_str = category_map.get(category.name, category.name.lower())
                if category_str in self._distracting_categories:
                    alert = self.create_alert(
                        message=f"Distracting website detected: {domain_str}",
                        level=AlertLevel.WARNING,
                        metadata={
                            "domain": domain_str,
                            "category": category.name,
                            "url": url
                        }
                    )
                    alerts.append(alert)
        except Exception as e:
            # Log error but don't crash
            pass
            
        return alerts
    
    def _is_browser(self, app_name: str) -> bool:
        """
        Check if the application is a browser.
        
        Args:
            app_name: The name of the application.
            
        Returns:
            True if the application is a browser, False otherwise.
        """
        browsers = ["chrome", "firefox", "edge", "opera", "safari", "brave"]
        return any(browser in app_name for browser in browsers)
    
    def _extract_url_from_window(
        self,
        window: Dict[str, Any],
        browser_tabs: Dict[str, Any]
    ) -> Optional[str]:
        """
        Extract URL from window title or browser tabs.
        
        Args:
            window: Information about the window.
            browser_tabs: Information about browser tabs.
            
        Returns:
            The extracted URL, or None if no URL could be extracted.
        """
        # First try to get URL from browser tabs if available
        if browser_tabs:
            active_tab = browser_tabs.get("active_tab")
            if active_tab and "url" in active_tab:
                return active_tab["url"]
        
        # Fall back to window title
        title = window.get("title", "")
        
        # Simple heuristic: look for http:// or https:// in the title
        if "http://" in title or "https://" in title:
            # Extract URL using simple heuristic
            parts = title.split(" ")
            for part in parts:
                if part.startswith("http://") or part.startswith("https://"):
                    return part
        
        return None
    
    def _extract_domain_from_url(self, url: str) -> Optional[str]:
        """
        Extract domain from URL.
        
        Args:
            url: The URL to extract the domain from.
            
        Returns:
            The extracted domain, or None if no domain could be extracted.
        """
        # Import here to avoid circular imports
        from focus_guard.core.domain.utils import extract_domain_from_url
        return extract_domain_from_url(url)
