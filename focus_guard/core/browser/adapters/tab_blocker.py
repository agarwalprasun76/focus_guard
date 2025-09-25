"""
Tab blocking adapter implementation.

This module provides the default implementation of the TabBlockerInterface.
"""

import logging
import time
from typing import Dict, Optional, List

from focus_guard.core.browser.interfaces import TabBlockerInterface
from focus_guard.core.browser.models.tab import Tab

logger = logging.getLogger(__name__)

class DefaultTabBlocker(TabBlockerInterface):
    """Default implementation of the TabBlockerInterface.
    
    This implementation handles blocking domains and closing tabs.
    """
    
    def __init__(self):
        """Initialize the tab blocker."""
        self._blocked_domains = {}  # domain -> expiry timestamp
        self._logger = logger.getChild('DefaultTabBlocker')
    
    def close_tab(self, tab: Tab, reason: str = None) -> bool:
        """Close a browser tab.
        
        Args:
            tab: The tab to close
            reason: Optional reason for closing the tab
            
        Returns:
            bool: True if the tab was closed successfully
        """
        try:
            self._logger.info(f"Closing tab {tab.id} (URL: {tab.url}), reason: {reason or 'not specified'}")
            # In a real implementation, this would use browser-specific APIs to close the tab
            # For now, we'll just log the action
            return True
        except Exception as e:
            self._logger.error(f"Error closing tab {tab.id}: {e}")
            return False
    
    def block_domain(self, domain: str, duration_seconds: int = None) -> bool:
        """Block a domain from being accessed.
        
        Args:
            domain: The domain to block
            duration_seconds: How long to block the domain (None = permanent, 0 or negative = block until next check)
            
        Returns:
            bool: True if the domain was blocked successfully
        """
        try:
            if duration_seconds is not None:
                expiry = time.time() + max(0, duration_seconds)  # Ensure non-negative duration
                log_msg = f"for {duration_seconds}s"
            else:
                expiry = None
                log_msg = "permanently"
                
            self._blocked_domains[domain] = expiry
            self._logger.info(f"Blocked domain: {domain} {log_msg}")
            return True
        except Exception as e:
            self._logger.error(f"Error blocking domain {domain}: {e}")
            return False
    
    def is_domain_blocked(self, domain: str) -> bool:
        """Check if a domain is blocked.
        
        Args:
            domain: The domain to check
            
        Returns:
            bool: True if the domain is blocked
        """
        if domain not in self._blocked_domains:
            return False
            
        expiry = self._blocked_domains[domain]
        if expiry is None:  # Permanent block
            return True
            
        if time.time() > expiry:  # Block has expired
            del self._blocked_domains[domain]
            return False
            
        return True
    
    def get_blocked_domains(self) -> Dict[str, Optional[float]]:
        """Get all blocked domains and their expiry times.
        
        Returns:
            Dict[str, Optional[float]]: Dictionary mapping domains to expiry timestamps
            (None means permanent block)
        """
        # Clean up expired blocks
        current_time = time.time()
        expired = [
            domain for domain, expiry in self._blocked_domains.items()
            if expiry is not None and expiry < current_time
        ]
        
        for domain in expired:
            del self._blocked_domains[domain]
            
        return self._blocked_domains.copy()
