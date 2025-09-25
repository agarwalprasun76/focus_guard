"""
Utility functions for the blocking system.

This module provides helper functions and utilities for working with the blocking system.
"""

import re
import logging
from typing import Dict, List, Optional, Pattern, Set, Tuple, Union
from urllib.parse import urlparse

from focus_guard.core.domain.models import Domain, Category

# Compile common regex patterns once for better performance
DOMAIN_PATTERN = re.compile(
    r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
)
IP_PATTERN = re.compile(
    r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)

logger = logging.getLogger("core.blocking.utils")

def is_valid_domain(domain: str) -> bool:
    """
    Check if a string is a valid domain name.
    
    Args:
        domain: The domain string to validate.
        
    Returns:
        bool: True if the domain is valid, False otherwise.
    """
    if not domain or len(domain) > 253:
        return False
    
    # Check for IP address first
    if IP_PATTERN.match(domain):
        return True
    
    # Check domain pattern
    return bool(DOMAIN_PATTERN.match(domain))

def normalize_domain(domain: str) -> str:
    """
    Normalize a domain name by converting to lowercase and removing www. prefix.
    
    Args:
        domain: The domain to normalize.
        
    Returns:
        str: The normalized domain.
    """
    if not domain:
        return ""
    
    domain = domain.lower().strip()
    
    # Remove protocol if present
    if '://' in domain:
        domain = domain.split('://', 1)[1]
    
    # Remove path and query parameters
    domain = domain.split('/', 1)[0]
    
    # Remove port if present
    domain = domain.split(':', 1)[0]
    
    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    
    return domain

def extract_domain_from_url(url: str) -> Optional[str]:
    """
    Extract and normalize the domain from a URL.
    
    Args:
        url: The URL to extract the domain from.
        
    Returns:
        Optional[str]: The normalized domain, or None if invalid.
    """
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            # Handle URLs without protocol (e.g., 'example.com/path')
            parsed = urlparse(f'//{url}', scheme='http')
        
        domain = parsed.netloc
        if not domain:
            return None
            
        # Remove port if present
        domain = domain.split(':', 1)[0]
        
        return normalize_domain(domain)
    except Exception as e:
        logger.debug(f"Error extracting domain from URL '{url}': {e}")
        return None

def create_domain_set(domains: List[str]) -> Set[str]:
    """
    Create a normalized set of domains from a list.
    
    Args:
        domains: List of domain strings.
        
    Returns:
        Set[str]: Set of normalized domains.
    """
    return {
        normalize_domain(domain)
        for domain in domains
        if domain and is_valid_domain(domain)
    }

def domain_matches(domain: str, pattern: Union[str, Pattern]) -> bool:
    """
    Check if a domain matches a pattern.
    
    Args:
        domain: The domain to check.
        pattern: The pattern to match against (can be a string or compiled regex).
        
    Returns:
        bool: True if the domain matches the pattern, False otherwise.
    """
    if not domain:
        return False
    
    domain = normalize_domain(domain)
    
    if isinstance(pattern, str):
        # Simple string matching
        pattern = pattern.lower()
        if pattern.startswith('*.'):
            # Wildcard subdomain matching
            return domain == pattern[2:] or domain.endswith('.' + pattern[2:])
        else:
            return domain == pattern
    else:
        # Regex matching
        return bool(pattern.search(domain))

def categorize_domain(domain: str, category_map: Dict[Category, List[str]]) -> Optional[Category]:
    """
    Categorize a domain based on a mapping of categories to domain patterns.
    
    Args:
        domain: The domain to categorize.
        category_map: Dictionary mapping categories to lists of domain patterns.
        
    Returns:
        Optional[Category]: The matching category, or None if no match found.
    """
    if not domain:
        return None
    
    domain = normalize_domain(domain)
    
    for category, patterns in category_map.items():
        for pattern in patterns:
            if domain_matches(domain, pattern):
                return category
    
    return None

def merge_domain_lists(*domain_lists: List[str]) -> List[str]:
    """
    Merge multiple domain lists, removing duplicates and normalizing domains.
    
    Args:
        *domain_lists: Variable number of domain lists to merge.
        
    Returns:
        List[str]: Merged and deduplicated list of normalized domains.
    """
    merged = set()
    
    for domain_list in domain_lists:
        if not domain_list:
            continue
            
        for domain in domain_list:
            normalized = normalize_domain(domain)
            if normalized and is_valid_domain(normalized):
                merged.add(normalized)
    
    return sorted(merged)

def parse_domain_list(text: str) -> List[str]:
    """
    Parse a text block containing domains (one per line) into a list.
    
    Args:
        text: The text containing domains, one per line.
        
    Returns:
        List[str]: List of valid, normalized domains.
    """
    domains = []
    
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # Handle comments at the end of lines
        domain = line.split('#', 1)[0].strip()
        if not domain:
            continue
            
        normalized = normalize_domain(domain)
        if normalized and is_valid_domain(normalized):
            domains.append(normalized)
    
    return domains

def is_subdomain(domain: str, parent_domain: str) -> bool:
    """
    Check if a domain is a subdomain of another domain.
    
    Args:
        domain: The domain to check.
        parent_domain: The potential parent domain.
        
    Returns:
        bool: True if domain is a subdomain of parent_domain, False otherwise.
    """
    if not domain or not parent_domain:
        return False
    
    domain = normalize_domain(domain)
    parent_domain = normalize_domain(parent_domain)
    
    if domain == parent_domain:
        return False
    
    return domain.endswith('.' + parent_domain)

def get_root_domain(domain: str) -> str:
    """
    Get the root domain (eTLD + 1) from a domain.
    
    Args:
        domain: The domain to process.
        
    Returns:
        str: The root domain, or the original domain if it's already a root domain.
    """
    domain = normalize_domain(domain)
    if not domain:
        return ""
    
    parts = domain.split('.')
    
    # Handle IP addresses
    if IP_PATTERN.match(domain):
        return domain
    
    # Handle known TLDs (this is a simplified version)
    # In a real implementation, you might want to use a proper TLD list
    if len(parts) > 2:
        # For now, just take the last two parts
        return '.'.join(parts[-2:])
    
    return domain
