"""
Domain Classifier Package

This package provides domain classification and URL classification functionality
for focus_guard.
"""

# Import and re-export the hierarchical classifier as the main link classifier
from .hierarchical_classifier import link_classifier
# Import from domain_classifier directly
from .domain_classifier import classify_domain, get_all_domains, get_all_categories
from .domain_whitelist import domain_whitelist, add_to_whitelist, remove_from_whitelist
from .domain_excluder import domain_excluder
from .filter_domain import filter_domain
from .domain_utils import (
    normalize_domain,
    is_valid_domain,
    extract_domain_from_url as extract_domain,
    get_domain_parts
)

# Export public API
__all__ = [
    'link_classifier',
    'classify_domain',
    'get_all_domains',
    'get_all_categories',
    'domain_whitelist',
    'add_to_whitelist',
    'remove_from_whitelist',
    'domain_excluder',
    'filter_domain',
    'normalize_domain',
    'is_valid_domain',
    'extract_domain',
    'get_domain_parts'
]