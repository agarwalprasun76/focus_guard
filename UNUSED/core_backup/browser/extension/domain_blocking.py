"""
Domain blocking integration for browser extension.

This module provides functionality for integrating domain blocking with the tab server.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse

from core_v2.models import Category
from core_v2.config.interfaces import ConfigurationManager
from core_v2.browser.extension.interfaces import TabServerInterface
from core_v2.browser.extension.tab_server import get_tab_server
from core_v2.browser.extension.integration import get_extension_integration

logger = logging.getLogger(__name__)


class DomainBlockingIntegration:
    """Integration class for domain blocking with browser extension."""
    
    def __init__(self, 
                 config_manager: Optional[ConfigurationManager] = None,
                 tab_server: Optional[TabServerInterface] = None):
        """Initialize the domain blocking integration.
        
        Args:
            config_manager: Configuration manager for domain settings
            tab_server: Tab server instance
        """
        self._config_manager = config_manager
        self._tab_server = tab_server or get_tab_server()
        self._blocked_categories: Set[Category] = set()
        self._blocked_domains: Set[str] = set()
        self._last_update_time = 0
        self._update_interval = 60  # seconds
        
        # Initialize blocked categories and domains
        self._update_blocking_rules()
    
    def _update_blocking_rules(self) -> None:
        """Update the blocking rules from configuration."""
        if not self._config_manager:
            logger.warning("No configuration manager provided, using default blocking rules")
            return
            
        try:
            # Get blocked categories from configuration
            blocked_categories = self._config_manager.get("focus.blocked_categories", [])
            self._blocked_categories = set()
            
            # Convert string categories to Category enum values using the mapping
            from core_v2.models import CATEGORY_TO_ENUM_MAPPING
            for category_str in blocked_categories:
                if category_str in CATEGORY_TO_ENUM_MAPPING:
                    self._blocked_categories.add(CATEGORY_TO_ENUM_MAPPING[category_str])
            
            # Get explicitly blocked domains
            self._blocked_domains = set(self._config_manager.get("focus.blocked_domains", []))
            
            # Update the last update time
            self._last_update_time = time.time()
            
            logger.info(f"Updated blocking rules: {len(self._blocked_categories)} categories, "
                        f"{len(self._blocked_domains)} domains")
        except Exception as e:
            logger.error(f"Error updating blocking rules: {e}")
    
    def should_block_url(self, url: str) -> bool:
        """Check if a URL should be blocked.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if the URL should be blocked, False otherwise
        """
        # Update blocking rules if needed
        if time.time() - self._last_update_time > self._update_interval:
            self._update_blocking_rules()
        
        try:
            # Parse the URL to get the domain
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Remove www. prefix if present
            if domain.startswith("www."):
                domain = domain[4:]
            
            # Check if domain is explicitly blocked
            if domain in self._blocked_domains:
                logger.debug(f"Domain {domain} is explicitly blocked")
                return True
            
            # Check if domain is in a blocked category
            if self._blocked_categories:
                domain_category = self._get_domain_category(domain)
                if domain_category in self._blocked_categories:
                    logger.debug(f"Domain {domain} is in blocked category {domain_category}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking if URL should be blocked: {e}")
            return False
    
    def _get_domain_category(self, domain: str) -> Optional[Category]:
        """Get the category for a domain.
        
        Args:
            domain: Domain to check
            
        Returns:
            Category: Category of the domain, or None if not categorized
        """
        if not self._config_manager:
            return None
            
        try:
            # Get domain classifications from configuration
            domain_categories = self._config_manager.get("domain_classifications", {})
            
            # Check if domain is directly classified
            if domain in domain_categories:
                category_str = domain_categories[domain]
                from core_v2.models import CATEGORY_TO_ENUM_MAPPING
                return CATEGORY_TO_ENUM_MAPPING.get(category_str)
            
            # Check for parent domains (e.g., example.com for sub.example.com)
            parts = domain.split('.')
            for i in range(1, len(parts) - 1):
                parent_domain = '.'.join(parts[i:])
                if parent_domain in domain_categories:
                    category_str = domain_categories[parent_domain]
                    from core_v2.models import CATEGORY_TO_ENUM_MAPPING
                    return CATEGORY_TO_ENUM_MAPPING.get(category_str)
            
            return None
        except Exception as e:
            logger.error(f"Error getting domain category: {e}")
            return None
    
    def close_blocked_tabs(self) -> int:
        """Close all tabs that should be blocked.
        
        Returns:
            int: Number of tabs closed
        """
        if not self._tab_server:
            logger.warning("No tab server available, cannot close blocked tabs")
            return 0
        
        try:
            # Get all tabs
            tabs = self._tab_server.get_tabs()
            closed_count = 0
            
            # Check each tab
            for tab in tabs:
                url = tab.get('url')
                if url and self.should_block_url(url):
                    # Get tab details for closing
                    tab_id = tab.get('id')
                    window_id = tab.get('windowId')
                    browser_name = tab.get('browser')
                    
                    if tab_id:
                        # Use the extension integration to close the tab
                        integration = get_extension_integration()
                        if integration.close_tab(tab_id, window_id, browser_name):
                            logger.info(f"Closed blocked tab: {tab.get('title')} ({url})")
                            closed_count += 1
                        else:
                            logger.warning(f"Failed to close blocked tab: {url}")
            
            return closed_count
        except Exception as e:
            logger.error(f"Error closing blocked tabs: {e}")
            return 0
    
    def get_blocking_rules(self) -> Dict[str, Any]:
        """Get the current blocking rules.
        
        Returns:
            Dict[str, Any]: Dictionary containing blocking rules
        """
        return {
            "blocked_categories": list(self._blocked_categories),
            "blocked_domains": list(self._blocked_domains),
            "last_update": self._last_update_time
        }


# Singleton instance
_domain_blocking_instance = None

def get_domain_blocking_integration(**kwargs) -> DomainBlockingIntegration:
    """Get the singleton domain blocking integration instance.
    
    Args:
        **kwargs: Arguments to pass to the DomainBlockingIntegration constructor
        
    Returns:
        DomainBlockingIntegration: The singleton instance
    """
    global _domain_blocking_instance
    if _domain_blocking_instance is None:
        _domain_blocking_instance = DomainBlockingIntegration(**kwargs)
    return _domain_blocking_instance

def should_block_url(url: str) -> bool:
    """Check if a URL should be blocked.
    
    Args:
        url: URL to check
        
    Returns:
        bool: True if the URL should be blocked, False otherwise
    """
    integration = get_domain_blocking_integration()
    return integration.should_block_url(url)

def close_blocked_tabs() -> int:
    """Close all tabs that should be blocked.
    
    Returns:
        int: Number of tabs closed
    """
    integration = get_domain_blocking_integration()
    return integration.close_blocked_tabs()
