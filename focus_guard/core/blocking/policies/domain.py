"""
Domain-based blocking policies.

This module implements blocking policies that are based on domain names.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union, Pattern
import re

from .base import BlockingPolicy, BlockingPolicyConfig, BlockingPolicyType
from focus_guard.core.domain.models import Domain, Category


@dataclass
class DomainBlockingConfig(BlockingPolicyConfig):
    """Configuration for domain-based blocking policies."""
    blocked_domains: Set[str] = field(default_factory=set)
    blocked_categories: Set[Category] = field(default_factory=set)
    allowlist: Set[str] = field(default_factory=set)
    regex_patterns: List[str] = field(default_factory=list)
    _compiled_patterns: List[Pattern] = field(init=False, default_factory=list)
    
    def __post_init__(self):
        """Compile regex patterns after initialization."""
        self._compiled_patterns = [re.compile(pattern, re.IGNORECASE) 
                                 for pattern in self.regex_patterns]


class DomainBlockingPolicy(BlockingPolicy):
    """
    A blocking policy that enforces domain-based restrictions.
    
    This policy blocks access to specific domains, domain patterns, or categories of domains.
    """
    
    def __init__(self, config: DomainBlockingConfig):
        """Initialize the domain blocking policy."""
        if not isinstance(config, DomainBlockingConfig):
            raise ValueError("config must be an instance of DomainBlockingConfig")
        super().__init__(config)
        self._config = config
    
    def _is_domain_blocked(self, domain: Union[Domain, str]) -> bool:
        """Check if a domain is explicitly blocked."""
        domain_str = str(domain).lower()
        
        # Check allowlist first (highest priority)
        if domain_str in self._config.allowlist:
            return False
            
        # Check exact domain matches
        if domain_str in self._config.blocked_domains:
            return True
            
        # Check domain patterns
        for pattern in self._config._compiled_patterns:
            if pattern.search(domain_str):
                return True
                
        # Check domain categories if domain is a Domain object
        if isinstance(domain, Domain) and domain.category in self._config.blocked_categories:
            return True
            
        return False
    
    def should_block(self, resource: Union[Domain, str], context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the domain should be blocked."""
        if not self._enabled:
            return False
            
        return self._is_domain_blocked(resource)
    
    def get_block_reason(self, resource: Union[Domain, str], context: Optional[Dict[str, Any]] = None) -> str:
        """Get the reason for blocking the domain."""
        if not self._enabled or not self._is_domain_blocked(resource):
            return ""
            
        domain_str = str(resource).lower()
        
        # Check exact matches first
        if domain_str in self._config.blocked_domains:
            return f"Domain '{domain_str}' is in the blocked domains list."
            
        # Check patterns
        for pattern in self._config.regex_patterns:
            if re.search(pattern, domain_str, re.IGNORECASE):
                return f"Domain '{domain_str}' matches blocked pattern '{pattern}'."
                
        # Check categories
        if isinstance(resource, Domain) and resource.category in self._config.blocked_categories:
            return f"Domain '{domain_str}' is in blocked category '{resource.category.value}'."
            
        return ""
    
    def add_blocked_domain(self, domain: str) -> None:
        """Add a domain to the blocked domains list."""
        self._config.blocked_domains.add(domain.lower())
    
    def remove_blocked_domain(self, domain: str) -> None:
        """Remove a domain from the blocked domains list."""
        self._config.blocked_domains.discard(domain.lower())
    
    def add_blocked_category(self, category: Category) -> None:
        """Add a category to the blocked categories list."""
        self._config.blocked_categories.add(category)
    
    def remove_blocked_category(self, category: Category) -> None:
        """Remove a category from the blocked categories list."""
        self._config.blocked_categories.discard(category)
    
    def add_allowlist_domain(self, domain: str) -> None:
        """Add a domain to the allowlist."""
        self._config.allowlist.add(domain.lower())
    
    def remove_allowlist_domain(self, domain: str) -> None:
        """Remove a domain from the allowlist."""
        self._config.allowlist.discard(domain.lower())
    
    def add_regex_pattern(self, pattern: str) -> None:
        """Add a regex pattern for domain blocking."""
        self._config.regex_patterns.append(pattern)
        self._config._compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
    
    @classmethod
    def create(
        cls,
        name: str,
        blocked_domains: Optional[Set[str]] = None,
        blocked_categories: Optional[Set[Category]] = None,
        allowlist: Optional[Set[str]] = None,
        regex_patterns: Optional[List[str]] = None,
        enabled: bool = True,
        description: str = "",
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'DomainBlockingPolicy':
        """Create a new domain blocking policy."""
        config = DomainBlockingConfig(
            policy_type=BlockingPolicyType.DOMAIN,
            name=name,
            description=description,
            enabled=enabled,
            priority=priority,
            metadata=metadata or {},
            blocked_domains=set(blocked_domains or []),
            blocked_categories=set(blocked_categories or []),
            allowlist=set(allowlist or []),
            regex_patterns=list(regex_patterns or [])
        )
        return cls(config)
