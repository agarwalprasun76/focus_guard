"""
Domain classification and management for web domains and applications.

This package provides comprehensive functionality for:
- Classifying domains into categories (work, social, etc.)
- Managing whitelisted domains
- Filtering and validating domains
- Extracting domains from URLs
- Domain normalization and validation

Example usage:
    >>> from core.domain_classifier import classify_domain, domain_whitelist
    >>> classify_domain("github.com")  # Returns 'work'
    'work'
    >>> domain_whitelist("google.com")  # Returns True
    True
"""

from typing import Dict, List, Set, Optional, Union

# Import core functionality
from .domain_classifier import classify_domain, get_all_domains, get_all_categories
from .domain_whitelist import (
    domain_whitelist,
    get_whitelisted_domains,
    add_to_whitelist,
    remove_from_whitelist
)
from .domain_excluder import domain_excluder as is_domain_excluded
from .filter_domain import filter_domain
from .domain_config import domain_config, DomainConfig
from .domain_utils import (
    normalize_domain,
    is_valid_domain,
    extract_domain_from_url,
    is_subdomain,
    get_domain_parts
)

__all__ = [
    # Core functions
    'classify_domain',
    'domain_whitelist',
    'is_domain_excluded',
    'filter_domain',
    
    # Domain utilities
    'normalize_domain',
    'is_valid_domain',
    'extract_domain_from_url',
    'is_subdomain',
    'get_domain_parts',
    
    # Whitelist management
    'get_whitelisted_domains',
    'add_to_whitelist',
    'remove_from_whitelist',
    
    # Domain information
    'get_all_domains',
    'get_all_categories',
    
    # Configuration
    'domain_config',
    'DomainConfig',
]

# Initialize the domain cache on import
from .domain_classifier import classify_domain as _init_cache
_init_cache("example.com")  # Trigger cache initialization
