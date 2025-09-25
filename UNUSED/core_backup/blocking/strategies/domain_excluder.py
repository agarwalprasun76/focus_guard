"""
Domain Excluder Strategy.

This module provides a blocking strategy that excludes domains based on
StevenBlack hosts file, which includes gambling, porn, social, and fakenews domains.
"""

import os
import time
import pickle
import logging
import requests
from pathlib import Path
from typing import Set, Optional, Dict, Any

from core_v2.blocking.base import BlockingStrategy, BlockingDecision
from core_v2.domain.models import Domain, Category
from core_v2.utils.domain_utils import is_valid_domain
from core_v2.config.loader import ConfigurationLoader


# StevenBlack hosts file with gambling, porn, social, fakenews
STEVENBLACK_HOSTS_URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/fakenews-gambling-porn-social/hosts"

# Cache settings
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "cache")
HOSTS_CACHE_FILE = os.path.join(CACHE_DIR, "hosts_domains_cache.pkl")
CACHE_TTL_DAYS = 7  # Update cache if older than this many days


class DomainExcluderStrategy(BlockingStrategy):
    """
    Blocking strategy that excludes domains based on StevenBlack hosts file.
    
    This strategy blocks domains that are known to be associated with
    gambling, porn, social media, and fake news.
    """
    
    def __init__(self):
        """Initialize the domain excluder strategy."""
        self._excluded_domains: Set[str] = set()
        self._whitelist_domains: Set[str] = set()
        self._logger = logging.getLogger("core_v2.blocking.strategies.domain_excluder")
        self._config_loader = ConfigurationLoader()
        self._load_excluded_domains()
        self._load_whitelist_domains()
        self._logger.info("Domain excluder strategy initialized")
    
    @property
    def name(self) -> str:
        """
        Get the name of the blocking strategy.
        
        Returns:
            The strategy name.
        """
        return "domain_excluder"
    
    @property
    def priority(self) -> int:
        """
        Get the priority of the blocking strategy.
        
        Domain excluder has high priority (100) to ensure excluded domains
        are blocked before other strategies are considered.
        
        Returns:
            The strategy priority.
        """
        return 100
    
    def should_block(self, domain: Domain) -> BlockingDecision:
        """
        Determine if a domain should be blocked.
        
        Args:
            domain: The domain to check.
            
        Returns:
            A BlockingDecision indicating whether the domain should be blocked.
        """
        # Reject invalid inputs and email addresses immediately
        if not domain or '@' in domain.value:
            return BlockingDecision(should_block=False, reason=None)
            
        try:
            # Normalize the domain
            domain_value = domain.value.strip().lower()
            
            # Check if domain is in whitelist or categorized as PRODUCTIVITY
            if self._is_whitelisted(domain_value) or domain.category == Category.PRODUCTIVITY:
                self._logger.debug(f"Domain {domain_value} is whitelisted or categorized as PRODUCTIVITY, not blocking")
                return BlockingDecision(should_block=False, reason=None)
            
            # Check exact match first (fast path)
            if domain_value in self._excluded_domains:
                return BlockingDecision(
                    should_block=True,
                    reason=f"Domain {domain_value} is in the exclusion list"
                )
                
            # Check parent domains
            domain_parts = domain_value.split('.')
            for i in range(1, len(domain_parts)):
                parent_domain = '.'.join(domain_parts[i:])
                if parent_domain in self._excluded_domains:
                    return BlockingDecision(
                        should_block=True,
                        reason=f"Parent domain {parent_domain} is in the exclusion list"
                    )
                    
        except (AttributeError, IndexError, ValueError) as e:
            self._logger.error(f"Error checking domain {domain.value}: {str(e)}")
            return BlockingDecision(should_block=False, reason=None)
            
        return BlockingDecision(should_block=False, reason=None)
    
    def should_block_with_context(self, domain: Domain, context: Dict[str, Any]) -> BlockingDecision:
        """
        Determine if a domain should be blocked using additional context.
        
        For this strategy, context is not used as the blocking decision
        is based solely on the domain.
        
        Args:
            domain: The domain to check.
            context: Additional context (not used).
            
        Returns:
            A BlockingDecision indicating whether the domain should be blocked.
        """
        # This strategy doesn't use context
        return self.should_block(domain)
    
    def _download_and_parse_hosts(self, url: str = STEVENBLACK_HOSTS_URL) -> Set[str]:
        """
        Download and parse the hosts file.
        
        Args:
            url: The URL of the hosts file.
            
        Returns:
            A set of excluded domains.
        """
        self._logger.info(f"Downloading hosts file from {url}...")
        response = requests.get(url)
        domains = set()
        for line in response.text.splitlines():
            line = line.strip()
            if line.startswith("0.0.0.0") or line.startswith("127.0.0.1"):
                parts = line.split()
                if len(parts) >= 2:
                    domain = parts[1].lower()
                    if domain != "localhost" and is_valid_domain(domain):
                        domains.add(domain)
        
        # Save to cache
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(HOSTS_CACHE_FILE, 'wb') as f:
            pickle.dump({
                'timestamp': time.time(),
                'domains': domains
            }, f)
        
        self._logger.info(f"Downloaded and cached {len(domains)} excluded domains")
        return domains
    
    def _load_excluded_domains_from_cache(self) -> Optional[Set[str]]:
        """
        Load excluded domains from cache if available and not expired.
        
        Returns:
            A set of excluded domains, or None if cache is invalid or expired.
        """
        if not os.path.exists(HOSTS_CACHE_FILE):
            return None
        
        try:
            with open(HOSTS_CACHE_FILE, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Check if cache is expired
            cache_age_days = (time.time() - cache_data['timestamp']) / (24 * 60 * 60)
            if cache_age_days > CACHE_TTL_DAYS:
                self._logger.info(f"Cache is {cache_age_days:.1f} days old (> {CACHE_TTL_DAYS} days), will refresh")
                return None
            
            domains = cache_data['domains']
            self._logger.info(f"Loaded {len(domains)} excluded domains from cache")
            return domains
        except Exception as e:
            self._logger.error(f"Error loading cache: {e}")
            return None
    
    def _load_excluded_domains(self) -> None:
        """Load excluded domains from cache or download if needed."""
        # Try to load from cache first
        domains = self._load_excluded_domains_from_cache()
        
        if domains is None:
            try:
                # Cache invalid or expired, download fresh data
                domains = self._download_and_parse_hosts()
            except Exception as e:
                self._logger.warning(f"Could not download excluded domains: {e}")
                # If download fails but we have a cache (even if expired), use it as fallback
                try:
                    with open(HOSTS_CACHE_FILE, 'rb') as f:
                        domains = pickle.load(f)['domains']
                    self._logger.info(f"Using expired cache with {len(domains)} domains as fallback")
                except Exception:
                    # No cache available, use a minimal set of excluded domains
                    domains = set([
                        "pornhub.com", "xvideos.com", "xnxx.com",
                        "bet365.com", "gambling.com", "casino.com",
                        "fakenews.com", "breitbart.com"
                    ])
                    self._logger.info(f"Using minimal set of {len(domains)} excluded domains")
        
        self._excluded_domains = domains
    
    def _is_whitelisted(self, domain_value: str) -> bool:
        """
        Check if a domain is in the whitelist.
        
        Args:
            domain_value: The domain to check.
            
        Returns:
            True if the domain is whitelisted, False otherwise.
        """
        # Check exact match first
        if domain_value in self._whitelist_domains:
            return True
            
        # Check parent domains
        domain_parts = domain_value.split('.')
        for i in range(1, len(domain_parts)):
            parent_domain = '.'.join(domain_parts[i:])
            if parent_domain in self._whitelist_domains:
                return True
                
        return False
        
    def _load_whitelist_domains(self) -> None:
        """Load whitelist domains from configuration."""
        self._whitelist_domains.clear()
        
        # Get whitelist domains from configuration
        whitelist = self._config_loader.whitelist
        if whitelist:
            for domain in whitelist.domains:
                self._whitelist_domains.add(domain.lower())
                
        self._logger.info(f"Loaded {len(self._whitelist_domains)} whitelist domains")
    
    def reload(self) -> None:
        """Reload the excluded domains list and whitelist."""
        self._logger.info("Reloading excluded domains and whitelist")
        self._load_excluded_domains()
        self._load_whitelist_domains()
