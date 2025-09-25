"""
Enhanced Domain Blocker for Phase 3: Advanced Browser Tab Control

This module provides enhanced domain blocking capabilities that integrate with
Phase 2 blocking policies and support URL pattern matching, multi-browser support,
and advanced blocking strategies.
"""

import logging
import time
import re
import fnmatch
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

from focus_guard.core.activity.blocking.models import BlockingPolicy, BlockingAction
from focus_guard.core.browser.integration.tab_blocker import BrowserTabBlocker
from focus_guard.core.browser.models.tab import Tab

logger = logging.getLogger(__name__)


class URLPattern:
    """Advanced URL pattern matching with support for wildcards, regex, and query parameters."""
    
    def __init__(self, pattern: str, pattern_type: str = "wildcard"):
        """
        Initialize URL pattern.
        
        Args:
            pattern: The pattern string
            pattern_type: Type of pattern ("wildcard", "regex", "exact", "domain", "path")
        """
        self.pattern = pattern
        self.pattern_type = pattern_type
        self._compiled_regex = None
        
        if pattern_type == "regex":
            try:
                self._compiled_regex = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")
                self.pattern_type = "exact"  # Fallback to exact match
    
    def matches(self, url: str) -> bool:
        """Check if URL matches this pattern."""
        if not url:
            return False
        
        url_lower = url.lower()
        pattern_lower = self.pattern.lower()
        
        if self.pattern_type == "exact":
            return url_lower == pattern_lower
        
        elif self.pattern_type == "wildcard":
            return fnmatch.fnmatch(url_lower, pattern_lower)
        
        elif self.pattern_type == "regex" and self._compiled_regex:
            return bool(self._compiled_regex.search(url))
        
        elif self.pattern_type == "domain":
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return domain == pattern_lower or domain.endswith('.' + pattern_lower)
        
        elif self.pattern_type == "path":
            parsed = urlparse(url)
            return fnmatch.fnmatch(parsed.path.lower(), pattern_lower)
        
        else:
            # Default to substring match
            return pattern_lower in url_lower


class BlockingRule:
    """Advanced blocking rule with multiple patterns and conditions."""
    
    def __init__(self, name: str, action: BlockingAction, patterns: List[URLPattern],
                 time_restrictions: List[Tuple[int, int]] = None, 
                 exception_patterns: List[URLPattern] = None,
                 grace_period: int = 0, warning_message: str = None):
        """
        Initialize blocking rule.
        
        Args:
            name: Rule name
            action: Blocking action to take
            patterns: List of URL patterns to match
            time_restrictions: List of (start_hour, end_hour) tuples for time-based blocking
            exception_patterns: Patterns that override blocking (whitelist)
            grace_period: Grace period before blocking takes effect
            warning_message: Custom warning message
        """
        self.name = name
        self.action = action
        self.patterns = patterns or []
        self.time_restrictions = time_restrictions or []
        self.exception_patterns = exception_patterns or []
        self.grace_period = grace_period
        self.warning_message = warning_message
        self.created_at = datetime.now()
        
        # Statistics
        self.matches_count = 0
        self.blocks_count = 0
        self.warnings_count = 0
    
    def matches_url(self, url: str) -> bool:
        """Check if URL matches this rule."""
        # Check exception patterns first (whitelist)
        for exception_pattern in self.exception_patterns:
            if exception_pattern.matches(url):
                return False
        
        # Check main patterns
        for pattern in self.patterns:
            if pattern.matches(url):
                self.matches_count += 1
                return True
        
        return False
    
    def is_active_now(self) -> bool:
        """Check if rule is active based on time restrictions."""
        if not self.time_restrictions:
            return True
        
        current_hour = datetime.now().hour
        
        for start_hour, end_hour in self.time_restrictions:
            if start_hour <= end_hour:
                # Same day restriction (e.g., 9 AM to 5 PM)
                if start_hour <= current_hour <= end_hour:
                    return True
            else:
                # Overnight restriction (e.g., 10 PM to 6 AM)
                if current_hour >= start_hour or current_hour <= end_hour:
                    return True
        
        return False
    
    def should_block(self, url: str) -> bool:
        """Check if URL should be blocked by this rule."""
        if not self.is_active_now():
            return False
        
        if self.matches_url(url):
            if self.action == BlockingAction.BLOCK:
                self.blocks_count += 1
                return True
            elif self.action == BlockingAction.WARN:
                self.warnings_count += 1
        
        return False


class EnhancedDomainBlocker(BrowserTabBlocker):
    """
    Enhanced domain blocker with advanced URL pattern matching and policy integration.
    
    Extends the basic BrowserTabBlocker with:
    - Advanced URL pattern matching (wildcards, regex, domain-specific)
    - Integration with Phase 2 blocking policies
    - Time-based blocking rules
    - Exception handling (whitelists)
    - Multi-browser support
    - Detailed blocking statistics
    """
    
    def __init__(self, extension_server_url: str = "http://localhost:8000"):
        """Initialize the enhanced domain blocker."""
        super().__init__(extension_server_url)
        
        # Advanced blocking rules
        self._blocking_rules: Dict[str, BlockingRule] = {}
        self._policy_rules: Dict[str, List[BlockingRule]] = {}  # Policy name -> rules
        
        # Browser-specific blocking
        self._browser_blocks: Dict[str, Set[str]] = {}  # browser -> blocked domains
        
        # Blocking statistics
        self._stats = {
            'total_blocks': 0,
            'total_warnings': 0,
            'blocks_by_rule': {},
            'blocks_by_browser': {},
            'blocks_by_domain': {},
            'recent_blocks': [],  # Last 100 blocks
            'start_time': datetime.now()
        }
        
        # Pattern matching cache
        self._pattern_cache: Dict[str, Dict[str, bool]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_cleanup = time.time()
    
    def add_blocking_rule(self, rule: BlockingRule):
        """Add a new blocking rule."""
        self._blocking_rules[rule.name] = rule
        logger.info(f"Added blocking rule: {rule.name}")
    
    def remove_blocking_rule(self, rule_name: str) -> bool:
        """Remove a blocking rule."""
        if rule_name in self._blocking_rules:
            del self._blocking_rules[rule_name]
            logger.info(f"Removed blocking rule: {rule_name}")
            return True
        return False
    
    def create_rule_from_policy(self, policy: BlockingPolicy) -> BlockingRule:
        """Create a blocking rule from a Phase 2 blocking policy."""
        patterns = []
        
        # Convert domain patterns to URL patterns
        for domain_pattern in policy.domain_patterns:
            patterns.append(URLPattern(domain_pattern, "domain"))
        
        # Convert app patterns to domain patterns (for browser apps)
        browser_domains = {
            "chrome": ["chrome://", "chrome-extension://"],
            "firefox": ["about:", "moz-extension://"],
            "edge": ["edge://", "extension://"],
            "safari": ["safari://", "safari-extension://"]
        }
        
        for app_pattern in policy.app_patterns:
            if app_pattern.lower() in browser_domains:
                for domain in browser_domains[app_pattern.lower()]:
                    patterns.append(URLPattern(f"{domain}*", "wildcard"))
        
        # Create time restrictions if policy has them
        time_restrictions = []
        if hasattr(policy, 'time_restrictions') and policy.time_restrictions:
            for restriction in policy.time_restrictions:
                if hasattr(restriction, 'start_hour') and hasattr(restriction, 'end_hour'):
                    time_restrictions.append((restriction.start_hour, restriction.end_hour))
        
        rule = BlockingRule(
            name=f"policy_{policy.name}",
            action=policy.action,
            patterns=patterns,
            time_restrictions=time_restrictions,
            grace_period=policy.grace_period_seconds,
            warning_message=policy.warning_message
        )
        
        return rule
    
    def sync_with_policies(self, policies: List[BlockingPolicy]):
        """Synchronize blocking rules with Phase 2 policies."""
        # Remove old policy rules
        old_policy_rules = [name for name in self._blocking_rules.keys() if name.startswith("policy_")]
        for rule_name in old_policy_rules:
            self.remove_blocking_rule(rule_name)
        
        # Add new policy rules
        for policy in policies:
            rule = self.create_rule_from_policy(policy)
            self.add_blocking_rule(rule)
            
            # Track policy -> rules mapping
            if policy.name not in self._policy_rules:
                self._policy_rules[policy.name] = []
            self._policy_rules[policy.name].append(rule)
        
        logger.info(f"Synchronized {len(policies)} policies into blocking rules")
    
    def should_block_url(self, url: str, browser: str = None) -> Tuple[bool, Optional[BlockingRule]]:
        """
        Check if URL should be blocked.
        
        Returns:
            Tuple of (should_block, matching_rule)
        """
        if not url:
            return False, None
        
        # Check cache first
        cache_key = f"block:{url}"
        if cache_key in self._pattern_cache:
            cached_result = self._pattern_cache[cache_key]
            if cached_result.get('timestamp', 0) + self._cache_ttl > time.time():
                rule_name = cached_result.get('rule_name')
                rule = self._blocking_rules.get(rule_name) if rule_name else None
                return cached_result.get('should_block', False), rule
        
        # Evaluate all rules
        for rule in self._blocking_rules.values():
            if rule.should_block(url):
                # Cache result
                self._pattern_cache[cache_key] = {
                    'should_block': True,
                    'rule_name': rule.name,
                    'timestamp': time.time()
                }
                return True, rule
        
        # Cache negative result
        self._pattern_cache[cache_key] = {
            'should_block': False,
            'rule_name': None,
            'timestamp': time.time()
        }
        
        return False, None
    
    def should_warn_url(self, url: str, browser: str = None) -> Tuple[bool, Optional[BlockingRule]]:
        """
        Check if URL should trigger a warning.
        
        Returns:
            Tuple of (should_warn, matching_rule)
        """
        if not url:
            return False, None
        
        for rule in self._blocking_rules.values():
            if rule.is_active_now() and rule.matches_url(url) and rule.action == BlockingAction.WARN:
                return True, rule
        
        return False, None
    
    def block_tab_advanced(self, tab: Tab, rule: BlockingRule = None, reason: str = None) -> bool:
        """Block a tab using advanced blocking logic."""
        if not tab:
            return False
        
        # Determine blocking reason
        if not reason and rule:
            reason = rule.warning_message or f"Blocked by rule: {rule.name}"
        elif not reason:
            reason = "Tab blocked by domain blocker"
        
        # Record blocking statistics
        self._record_block(tab, rule, reason)
        
        # Apply grace period if specified
        if rule and rule.grace_period > 0:
            logger.info(f"Grace period of {rule.grace_period}s before blocking {tab.url}")
            # In a real implementation, you might want to schedule the block
            # For now, we'll block immediately but log the grace period
        
        # Close the tab
        success = self.close_tab(tab, reason)
        
        if success:
            # Track browser-specific blocks
            if tab.browser_id:
                if tab.browser_id not in self._browser_blocks:
                    self._browser_blocks[tab.browser_id] = set()
                if tab.domain:
                    self._browser_blocks[tab.browser_id].add(tab.domain)
        
        return success
    
    def close_tabs_by_pattern(self, pattern: URLPattern, reason: str = None) -> int:
        """Close all tabs matching a URL pattern."""
        # This would require getting all active tabs from browser integration
        # For now, return 0 as placeholder
        logger.info(f"Would close tabs matching pattern: {pattern.pattern}")
        return 0
    
    def add_exception_pattern(self, rule_name: str, pattern: URLPattern):
        """Add an exception pattern to a blocking rule."""
        if rule_name in self._blocking_rules:
            self._blocking_rules[rule_name].exception_patterns.append(pattern)
            logger.info(f"Added exception pattern to rule {rule_name}: {pattern.pattern}")
    
    def get_blocking_rules(self) -> Dict[str, BlockingRule]:
        """Get all blocking rules."""
        return self._blocking_rules.copy()
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics for all blocking rules."""
        rule_stats = {}
        for name, rule in self._blocking_rules.items():
            rule_stats[name] = {
                'matches_count': rule.matches_count,
                'blocks_count': rule.blocks_count,
                'warnings_count': rule.warnings_count,
                'created_at': rule.created_at.isoformat(),
                'patterns_count': len(rule.patterns),
                'exception_patterns_count': len(rule.exception_patterns),
                'is_active_now': rule.is_active_now()
            }
        return rule_stats
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive blocking statistics."""
        return {
            **self._stats,
            'rules_count': len(self._blocking_rules),
            'active_rules_count': sum(1 for rule in self._blocking_rules.values() if rule.is_active_now()),
            'browser_blocks': {browser: list(domains) for browser, domains in self._browser_blocks.items()},
            'rule_statistics': self.get_rule_statistics(),
            'cache_size': len(self._pattern_cache),
            'uptime_seconds': (datetime.now() - self._stats['start_time']).total_seconds()
        }
    
    def _record_block(self, tab: Tab, rule: BlockingRule = None, reason: str = None):
        """Record blocking statistics."""
        self._stats['total_blocks'] += 1
        
        # Record by rule
        if rule:
            if rule.name not in self._stats['blocks_by_rule']:
                self._stats['blocks_by_rule'][rule.name] = 0
            self._stats['blocks_by_rule'][rule.name] += 1
        
        # Record by browser
        if tab.browser_id:
            if tab.browser_id not in self._stats['blocks_by_browser']:
                self._stats['blocks_by_browser'][tab.browser_id] = 0
            self._stats['blocks_by_browser'][tab.browser_id] += 1
        
        # Record by domain
        if tab.domain:
            if tab.domain not in self._stats['blocks_by_domain']:
                self._stats['blocks_by_domain'][tab.domain] = 0
            self._stats['blocks_by_domain'][tab.domain] += 1
        
        # Record recent block
        block_record = {
            'timestamp': datetime.now().isoformat(),
            'url': tab.url,
            'domain': tab.domain,
            'browser': tab.browser_id,
            'rule': rule.name if rule else None,
            'reason': reason
        }
        
        self._stats['recent_blocks'].append(block_record)
        
        # Keep only last 100 blocks
        if len(self._stats['recent_blocks']) > 100:
            self._stats['recent_blocks'] = self._stats['recent_blocks'][-100:]
    
    def cleanup_cache(self):
        """Clean up pattern matching cache."""
        current_time = time.time()
        if current_time - self._last_cache_cleanup > self._cache_ttl:
            expired_keys = []
            for key, cached_data in self._pattern_cache.items():
                if cached_data.get('timestamp', 0) + self._cache_ttl < current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._pattern_cache[key]
            
            self._last_cache_cleanup = current_time
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


# Utility functions for creating common blocking patterns
def create_social_media_patterns() -> List[URLPattern]:
    """Create patterns for common social media sites."""
    return [
        URLPattern("*.facebook.com", "domain"),
        URLPattern("*.twitter.com", "domain"),
        URLPattern("*.instagram.com", "domain"),
        URLPattern("*.tiktok.com", "domain"),
        URLPattern("*.snapchat.com", "domain"),
        URLPattern("*.linkedin.com", "domain"),
        URLPattern("*.reddit.com", "domain"),
        URLPattern("*.pinterest.com", "domain")
    ]


def create_entertainment_patterns() -> List[URLPattern]:
    """Create patterns for entertainment sites."""
    return [
        URLPattern("*.youtube.com", "domain"),
        URLPattern("*.netflix.com", "domain"),
        URLPattern("*.twitch.tv", "domain"),
        URLPattern("*.hulu.com", "domain"),
        URLPattern("*.disney.com", "domain"),
        URLPattern("*.amazon.com/prime*", "wildcard"),
        URLPattern("*.spotify.com", "domain")
    ]


def create_gaming_patterns() -> List[URLPattern]:
    """Create patterns for gaming sites and platforms."""
    return [
        URLPattern("*.steam.com", "domain"),
        URLPattern("*.epicgames.com", "domain"),
        URLPattern("*.origin.com", "domain"),
        URLPattern("*.battle.net", "domain"),
        URLPattern("*.roblox.com", "domain"),
        URLPattern("*.minecraft.net", "domain"),
        URLPattern("*.twitch.tv", "domain")
    ]


def create_work_productivity_exceptions() -> List[URLPattern]:
    """Create exception patterns for work productivity tools."""
    return [
        URLPattern("*.github.com", "domain"),
        URLPattern("*.stackoverflow.com", "domain"),
        URLPattern("*.google.com/search*", "wildcard"),
        URLPattern("*.microsoft.com", "domain"),
        URLPattern("*.office.com", "domain"),
        URLPattern("*.slack.com", "domain"),
        URLPattern("*.zoom.us", "domain")
    ]
