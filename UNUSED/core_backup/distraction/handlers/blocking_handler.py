"""
Blocking alert handler implementation.

This module provides an alert handler that blocks distracting
content when critical alerts are triggered.
"""

from typing import Dict, Any, Optional, Set
import logging
from datetime import datetime, timedelta

from core_v2.distraction.interfaces import AlertHandler
from core_v2.distraction.models import DistractionAlert, AlertLevel
from core_v2.browser.interfaces import BrowserIntegrationInterface


class BlockingHandler(AlertHandler):
    """
    Alert handler that blocks distracting content.
    
    This handler uses the browser integration to block distracting
    content when critical alerts are triggered.
    """
    
    def __init__(
        self,
        browser_integration: BrowserIntegrationInterface,
        min_level: AlertLevel = AlertLevel.CRITICAL,
        block_duration_seconds: int = 300,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the blocking handler.
        
        Args:
            browser_integration: The browser integration to use.
            min_level: Minimum alert level to trigger blocking.
            block_duration_seconds: Duration of blocking in seconds.
            logger: Optional logger for logging.
        """
        self._browser_integration = browser_integration
        self._min_level = min_level
        self._block_duration_seconds = block_duration_seconds
        self._logger = logger or logging.getLogger(__name__)
        self._blocked_domains: Set[str] = set()
        self._block_end_time: Optional[datetime] = None
    
    @property
    def name(self) -> str:
        """Get the name of the handler."""
        return "Blocking Handler"
    
    def can_handle(self, alert: DistractionAlert) -> bool:
        """
        Determine if the handler can handle the alert.
        
        Args:
            alert: The distraction alert to handle.
            
        Returns:
            True if the handler can handle the alert, False otherwise.
        """
        # Check if alert level is high enough
        if alert.level.value < self._min_level.value:
            return False
        
        # Check if the alert has a domain to block
        domain = alert.metadata.get("domain")
        return domain is not None
    
    def handle(self, alert: DistractionAlert) -> None:
        """
        Handle a distraction alert by blocking the distracting content.
        
        Args:
            alert: The distraction alert to handle.
        """
        try:
            # Get domain from alert
            domain = alert.metadata.get("domain")
            if not domain:
                return
            
            # Add domain to blocked domains
            self._blocked_domains.add(domain)
            
            # Set block end time
            self._block_end_time = datetime.now() + timedelta(seconds=self._block_duration_seconds)
            
            # Block domain
            self._block_domain(domain)
            
            self._logger.info(f"Blocked domain {domain} for {self._block_duration_seconds} seconds")
        except Exception as e:
            self._logger.error(f"Error blocking domain: {e}")
    
    def _block_domain(self, domain: str) -> None:
        """
        Block a domain.
        
        Args:
            domain: The domain to block.
        """
        try:
            # Close existing tabs with this domain
            self._close_tabs_with_domain(domain)
            
            # Add domain to browser blocker
            self._browser_integration.block_domain(
                domain,
                duration_seconds=self._block_duration_seconds,
                reason="Distraction detected"
            )
        except Exception as e:
            self._logger.error(f"Error blocking domain {domain}: {e}")
    
    def _close_tabs_with_domain(self, domain: str) -> None:
        """
        Close browser tabs with a specific domain.
        
        Args:
            domain: The domain to close tabs for.
        """
        try:
            # Get all tabs
            tabs = self._browser_integration.get_active_tabs()
            all_tabs = tabs.get("all_tabs", [])
            
            # Find tabs with the domain
            for tab in all_tabs:
                tab_url = tab.get("url", "")
                tab_domain = self._extract_domain_from_url(tab_url)
                
                if tab_domain == domain:
                    tab_id = tab.get("id")
                    if tab_id:
                        self._browser_integration.close_tab(tab_id)
                        self._logger.info(f"Closed tab with domain {domain}: {tab_url}")
        except Exception as e:
            self._logger.error(f"Error closing tabs with domain {domain}: {e}")
    
    def _extract_domain_from_url(self, url: str) -> Optional[str]:
        """
        Extract domain from URL.
        
        Args:
            url: The URL to extract the domain from.
            
        Returns:
            The extracted domain, or None if no domain could be extracted.
        """
        # Import here to avoid circular imports
        from core_v2.domain.utils import extract_domain_from_url
        return extract_domain_from_url(url)
    
    def check_and_unblock(self) -> None:
        """
        Check if any blocked domains should be unblocked.
        
        This method should be called periodically to unblock domains
        after the block duration has expired.
        """
        if not self._block_end_time:
            return
            
        if datetime.now() >= self._block_end_time:
            # Unblock all domains
            for domain in self._blocked_domains:
                try:
                    self._browser_integration.unblock_domain(domain)
                    self._logger.info(f"Unblocked domain {domain}")
                except Exception as e:
                    self._logger.error(f"Error unblocking domain {domain}: {e}")
            
            # Clear blocked domains and reset block end time
            self._blocked_domains.clear()
            self._block_end_time = None
