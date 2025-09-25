"""
Classifier Blocker API: Integration layer between domain classifier and blocker modules.

This module provides a clean API for communication between the domain classifier
and the blocker modules, enabling both preemptive and reactive blocking based on
domain classification results.

Features:
- Standardized tab information data structure
- Domain classification interface
- Blocking decision interface
- Context-aware classification support
"""

import logging
import time
from typing import Dict, Any, Tuple, Optional, List, Set, Union
from dataclasses import dataclass

# Import domain classifier components
from core.domain_classifier.domain_classifier import classify_domain, get_all_categories
from core.domain_classifier.domain_utils import extract_domain_from_url
from core.domain_classifier.classifiers.youtube_classifier import youtube_classifier
from core.domain_classifier.domain_excluder import domain_excluder
from core.domain_classifier.domain_whitelist import domain_whitelist

# Import blocker components
from core.blocker.domain_blocker import should_block, block_reason

# Setup logging
logger = logging.getLogger(__name__)

# Standard tab information data structure
class TabInfo:
    """Standardized tab information data structure for classifier-blocker communication."""
    
    def __init__(self, 
                 url: str = "",
                 domain: str = "",
                 title: str = "",
                 tab_id: Optional[int] = None,
                 window_id: Optional[int] = None,
                 active: bool = False,
                 metadata: Optional[Dict[str, Any]] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize tab information.
        
        Args:
            url: The URL of the tab
            domain: The domain of the tab (extracted from URL if not provided)
            title: The title of the tab
            tab_id: The browser tab ID
            window_id: The browser window ID
            active: Whether the tab is active
            metadata: Additional metadata about the tab content
            context: Contextual information for context-aware classification
        """
        self.url = url
        self.domain = domain or extract_domain(url) if url else ""
        self.title = title
        self.tab_id = tab_id
        self.window_id = window_id
        self.active = active
        self.metadata = metadata or {}
        self.context = context or {}
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TabInfo':
        """Create a TabInfo object from a dictionary."""
        return cls(
            url=data.get('url', ''),
            domain=data.get('domain', ''),
            title=data.get('title', ''),
            tab_id=data.get('tabId') or data.get('tab_id'),
            window_id=data.get('windowId') or data.get('window_id'),
            active=data.get('active', False),
            metadata=data.get('metadata', {}),
            context=data.get('context', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TabInfo to a dictionary."""
        return {
            'url': self.url,
            'domain': self.domain,
            'title': self.title,
            'tabId': self.tab_id,
            'windowId': self.window_id,
            'active': self.active,
            'metadata': self.metadata,
            'context': self.context
        }


class ClassifierBlockerAPI:
    """Integration API between domain classifier and blocker modules."""
    
    def __init__(self, 
                 block_categories: Optional[List[str]] = None,
                 approved_only: bool = False,
                 context_aware: bool = False):
        """
        Initialize the classifier-blocker API.
        
        Args:
            block_categories: List of categories to block
            approved_only: If True, only whitelisted domains are allowed
            context_aware: If True, enable context-aware classification
        """
        self.block_categories = set(block_categories) if block_categories else set()
        self.approved_only = approved_only
        self.context_aware = context_aware
        
        # No need to initialize domain classifier as we'll use functions directly
        
        # Cache for blocking decisions to avoid repeated lookups
        self._decision_cache = {}
        self._cache_expiry = {}
        self._cache_ttl = 300  # 5 minutes
        
        logger.info(f"ClassifierBlockerAPI initialized with categories: {self.block_categories}")
        logger.info(f"Context-aware classification: {self.context_aware}")
    
    def should_block_tab(self, tab_info: Union[TabInfo, Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Determine if a tab should be blocked based on its URL, domain, and context.
        
        Args:
            tab_info: TabInfo object or dictionary with tab information
            
        Returns:
            Tuple[bool, str]: (should_block, reason)
                - should_block: True if the tab should be blocked
                - reason: The reason for blocking or allowing
        """
        # Convert dictionary to TabInfo if needed
        if isinstance(tab_info, dict):
            tab_info = TabInfo.from_dict(tab_info)
        
        # Check cache first
        cache_key = f"{tab_info.url}_{tab_info.domain}"
        current_time = time.time()
        
        if cache_key in self._decision_cache and current_time < self._cache_expiry.get(cache_key, 0):
            decision, reason = self._decision_cache[cache_key]
            logger.debug(f"Cache hit for {tab_info.domain}: {decision} ({reason})")
            return decision, reason
        
        # Clean up expired cache entries
        self._cleanup_cache(current_time)
        
        # Normalize domain
        domain = tab_info.domain or extract_domain(tab_info.url)
        
        # Check exclusion and whitelist
        if domain_excluder(domain):
            self._cache_decision(cache_key, False, "excluded")
            return False, "excluded"
        
        if domain_whitelist(domain):
            self._cache_decision(cache_key, False, "whitelisted")
            return False, "whitelisted"
        
        # In approved-only mode, block anything not whitelisted
        if self.approved_only:
            self._cache_decision(cache_key, True, "not_whitelisted")
            return True, "not_whitelisted"
        
        # Perform domain classification
        category = self._classify_with_context(tab_info)
        
        # Add debug logging for Facebook URLs
        if 'facebook' in domain:
            logger.info(f"Facebook domain detected: {domain}, classified as: {category}")
            logger.info(f"Block categories: {self.block_categories}")
            logger.info(f"Should block: {category in self.block_categories}")
        
        # Check if category is in block list
        if category in self.block_categories:
            self._cache_decision(cache_key, True, f"blocked_category:{category}")
            return True, f"blocked_category:{category}"
        
        # Not blocked
        self._cache_decision(cache_key, False, f"allowed_category:{category}")
        return False, f"allowed_category:{category}"
    
    def _classify_with_context(self, tab_info: TabInfo) -> str:
        """
        Classify a domain with context awareness if enabled.
        
        Args:
            tab_info: TabInfo object with tab information
            
        Returns:
            str: The category of the domain
        """
        url = tab_info.url
        domain = tab_info.domain or extract_domain_from_url(url)
        
        # If context-aware classification is disabled or no context is available,
        # use standard domain classification
        if not self.context_aware or not tab_info.context:
            return classify_domain(domain)
        
        # Check if this is a YouTube URL - use specialized YouTube classifier
        if 'youtube.com' in domain or 'youtu.be' in domain:
            # Prepare metadata for YouTube classifier
            metadata = {}
            
            # Combine metadata from tab_info.metadata and tab_info.context
            if tab_info.metadata:
                metadata.update(tab_info.metadata)
            if tab_info.context:
                metadata.update(tab_info.context)
                
            # Use the existing YouTube classifier
            result = youtube_classifier.classify(url, domain, "", metadata)
            
            if result and 'classification' in result:
                # Map YouTube classifier result to domain category
                classification = result['classification']
                if classification == 'useful':
                    logger.info(f"YouTube classified as educational: {url}")
                    return 'education'
                elif classification == 'distraction':
                    logger.info(f"YouTube classified as entertainment: {url}")
                    return 'entertainment'
                elif classification == 'neutral':
                    logger.info(f"YouTube classified as neutral: {url}")
                    return 'neutral'
        
        # Fall back to standard domain classification for non-YouTube URLs
        # or if YouTube classification failed
        category = classify_domain(domain)
        logger.info(f"Standard classification for {url}: {category}")
        return category
    
    def _cache_decision(self, cache_key: str, decision: bool, reason: str) -> None:
        """Cache a blocking decision."""
        current_time = time.time()
        self._decision_cache[cache_key] = (decision, reason)
        self._cache_expiry[cache_key] = current_time + self._cache_ttl
    
    def _cleanup_cache(self, current_time: Optional[float] = None) -> None:
        """Clean up expired cache entries."""
        if current_time is None:
            current_time = time.time()
        
        expired_keys = [k for k, expiry in self._cache_expiry.items() if current_time > expiry]
        for key in expired_keys:
            if key in self._decision_cache:
                del self._decision_cache[key]
            if key in self._cache_expiry:
                del self._cache_expiry[key]
    
    def get_blocking_rules(self) -> List[Dict[str, Any]]:
        """
        Get a list of blocking rules for preemptive blocking.
        
        Returns:
            List[Dict[str, Any]]: List of rule dictionaries
        """
        rules = []
        
        # Get domains in blocked categories
        for category in self.block_categories:
            domains = self.domain_classifier.get_domains_in_category(category)
            for domain in domains:
                rules.append({
                    "domain": domain,
                    "category": category,
                    "reason": f"Domain in blocked category: {category}"
                })
        
        # In approved-only mode, we would need to block everything not whitelisted
        # This is not practical for preemptive blocking, so we only include explicit rules
        
        return rules
    
    def set_block_categories(self, categories: List[str]) -> None:
        """Set the list of categories to block."""
        self.block_categories = set(categories)
        # Clear cache when categories change
        self._decision_cache.clear()
        self._cache_expiry.clear()
    
    def add_block_category(self, category: str) -> None:
        """Add a category to the block list."""
        self.block_categories.add(category)
        # Clear cache when categories change
        self._decision_cache.clear()
        self._cache_expiry.clear()
    
    def remove_block_category(self, category: str) -> None:
        """Remove a category from the block list."""
        if category in self.block_categories:
            self.block_categories.remove(category)
            # Clear cache when categories change
            self._decision_cache.clear()
            self._cache_expiry.clear()
    
    def set_approved_only_mode(self, enabled: bool) -> None:
        """Set whether to use approved-only mode."""
        self.approved_only = enabled
        # Clear cache when mode changes
        self._decision_cache.clear()
        self._cache_expiry.clear()
    
    def set_context_aware_mode(self, enabled: bool) -> None:
        """Set whether to use context-aware classification."""
        self.context_aware = enabled
        # Clear cache when mode changes
        self._decision_cache.clear()
        self._cache_expiry.clear()


# Create a singleton instance
classifier_blocker_api = ClassifierBlockerAPI()

def get_api() -> ClassifierBlockerAPI:
    """Get the singleton instance of the ClassifierBlockerAPI."""
    return classifier_blocker_api

def should_block_tab(tab_info: Union[TabInfo, Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Determine if a tab should be blocked (convenience function using singleton).
    
    Args:
        tab_info: TabInfo object or dictionary with tab information
        
    Returns:
        Tuple[bool, str]: (should_block, reason)
    """
    return get_api().should_block_tab(tab_info)

def get_blocking_rules() -> List[Dict[str, Any]]:
    """
    Get a list of blocking rules (convenience function using singleton).
    
    Returns:
        List[Dict[str, Any]]: List of rule dictionaries
    """
    return get_api().get_blocking_rules()


# Simple test function
def run_tests():
    """Run test cases for the classifier-blocker API."""
    api = ClassifierBlockerAPI(block_categories=['social', 'entertainment'])
    
    # Test cases
    test_tabs = [
        TabInfo(url="https://www.facebook.com", title="Facebook"),
        TabInfo(url="https://www.github.com", title="GitHub"),
        TabInfo(url="https://www.youtube.com/watch?v=12345", title="Funny Cat Videos", 
                context={"video_title": "Funny Cat Videos", "channel_name": "CatLover"}),
        TabInfo(url="https://www.youtube.com/watch?v=67890", title="Learn Python Programming", 
                context={"video_title": "Learn Python Programming Tutorial", "channel_name": "CodeAcademy"})
    ]
    
    print("Testing classifier-blocker API:")
    for tab in test_tabs:
        should_block, reason = api.should_block_tab(tab)
        print(f"URL: {tab.url}")
        print(f"  Block: {should_block}")
        print(f"  Reason: {reason}")
    
    # Test context-aware mode
    print("\nTesting with context-aware mode enabled:")
    api.set_context_aware_mode(True)
    for tab in test_tabs:
        if "youtube.com" in tab.url:
            should_block, reason = api.should_block_tab(tab)
            print(f"URL: {tab.url}")
            print(f"  Title: {tab.title}")
            print(f"  Block: {should_block}")
            print(f"  Reason: {reason}")
    
    # Test blocking rules
    print("\nBlocking rules:")
    rules = api.get_blocking_rules()
    for rule in rules[:5]:  # Show first 5 rules
        print(f"  {rule['domain']} ({rule['category']}): {rule['reason']}")
    print(f"  ... and {len(rules) - 5} more rules")


if __name__ == "__main__":
    run_tests()
