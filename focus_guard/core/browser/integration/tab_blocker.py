"""
Tab blocker integration module.

This module provides the concrete implementation of the tab blocking functionality,
integrating with browser extensions to block and close tabs.
"""

import logging
import time
from typing import Dict, Optional, List, Any
import json

from focus_guard.core.browser.interfaces import TabBlockerInterface
from focus_guard.core.browser.models.tab import Tab

logger = logging.getLogger(__name__)


class BrowserTabBlocker(TabBlockerInterface):
    """Browser tab blocker implementation that integrates with browser extensions."""
    
    def __init__(self, extension_server_url: str = "http://localhost:8000"):
        """Initialize the browser tab blocker.
        
        Args:
            extension_server_url: URL of the extension server
        """
        self._extension_server_url = extension_server_url
        self._blocked_domains: Dict[str, Optional[float]] = {}  # domain -> expiry time
    
    def close_tab(self, tab: Tab, reason: str = None) -> bool:
        """Close a browser tab.
        
        Args:
            tab: Tab to close
            reason: Reason for closing the tab
            
        Returns:
            bool: True if the tab was closed successfully
        """
        if not tab:
            return False
            
        logger.info(f"Closing tab: {tab.url} (reason: {reason})")
        
        try:
            # In a real implementation, this would communicate with browser extensions
            # to close the tab
            import requests
            
            # Prepare the close tab message
            close_data = {
                "action": "close_tab",
                "data": {
                    "tabId": tab.id,
                    "windowId": tab.window_id,
                    "url": tab.url,
                    "domain": tab.domain,
                    "reason": reason
                }
            }
            
            # Send the close tab request to the extension server
            response = requests.post(
                f"{self._extension_server_url}/close_tab",
                json=close_data
            )
            
            if response.status_code == 200:
                logger.info(f"Tab closed successfully: {tab.url}")
                return True
            else:
                logger.warning(f"Failed to close tab: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error closing tab: {e}")
            return False
    
    def block_domain(self, domain: str, duration_seconds: int = None) -> bool:
        """Block a domain from being accessed.
        
        Args:
            domain: Domain to block
            duration_seconds: Duration of the block in seconds, or None for permanent
            
        Returns:
            bool: True if the domain was blocked successfully
        """
        if not domain:
            return False
            
        logger.info(f"Blocking domain: {domain} (duration: {duration_seconds}s)")
        
        # Set expiry time if duration is specified
        expiry_time = None
        if duration_seconds:
            expiry_time = time.time() + duration_seconds
            
        # Add to blocked domains
        domain_lower = domain.lower()
        self._blocked_domains[domain_lower] = expiry_time
        
        try:
            # In a real implementation, this would communicate with browser extensions
            # to block the domain
            import requests
            
            # Prepare the block domain message
            block_data = {
                "action": "block_domain",
                "data": {
                    "domain": domain,
                    "duration": duration_seconds,
                    "expiry": expiry_time
                }
            }
            
            # Send the block domain request to the extension server
            response = requests.post(
                f"{self._extension_server_url}/block_domain",
                json=block_data
            )
            
            if response.status_code == 200:
                logger.info(f"Domain blocked successfully: {domain}")
                return True
            else:
                logger.warning(f"Failed to block domain: {response.status_code}")
                # Remove from blocked domains if request failed
                del self._blocked_domains[domain_lower]
                return False
                
        except Exception as e:
            logger.error(f"Error blocking domain: {e}")
            # Remove from blocked domains if request failed
            del self._blocked_domains[domain_lower]
            return False
    
    def is_domain_blocked(self, domain: str) -> bool:
        """Check if a domain is blocked.
        
        Args:
            domain: Domain to check
            
        Returns:
            bool: True if the domain is blocked
        """
        if not domain:
            return False
            
        domain_lower = domain.lower()
        if domain_lower not in self._blocked_domains:
            return False
            
        # Check if block has expired
        expiry_time = self._blocked_domains[domain_lower]
        if expiry_time and time.time() > expiry_time:
            # Block has expired
            del self._blocked_domains[domain_lower]
            return False
            
        return True
    
    def get_blocked_domains(self) -> Dict[str, Optional[float]]:
        """Get all blocked domains and their expiry times.
        
        Returns:
            Dict[str, Optional[float]]: Dictionary mapping domain to expiry time
        """
        # Clean up expired blocks
        current_time = time.time()
        expired_domains = []
        
        for domain, expiry_time in self._blocked_domains.items():
            if expiry_time and current_time > expiry_time:
                expired_domains.append(domain)
                
        for domain in expired_domains:
            del self._blocked_domains[domain]
            
        return self._blocked_domains.copy()
    
    def close_tabs_by_domain(self, domain: str, reason: str = None) -> int:
        """Close all tabs for a specific domain.
        
        Args:
            domain: Domain to close tabs for
            reason: Reason for closing the tabs
            
        Returns:
            int: Number of tabs closed
        """
        if not domain:
            return 0
            
        domain_lower = domain.lower()
        logger.info(f"Closing all tabs for domain: {domain}")
        
        try:
            # In a real implementation, this would communicate with browser extensions
            # to close tabs for the domain
            import requests
            
            # Prepare the close tabs by domain message
            close_data = {
                "action": "close_tabs_by_domain",
                "data": {
                    "domain": domain,
                    "reason": reason
                }
            }
            
            # Send the close tabs by domain request to the extension server
            response = requests.post(
                f"{self._extension_server_url}/close_tabs_by_domain",
                json=close_data
            )
            
            if response.status_code == 200:
                result = response.json()
                closed_count = result.get("closed_count", 0)
                logger.info(f"Closed {closed_count} tabs for domain: {domain}")
                return closed_count
            else:
                logger.warning(f"Failed to close tabs for domain: {response.status_code}")
                return 0
                
        except Exception as e:
            logger.error(f"Error closing tabs for domain: {e}")
            return 0
