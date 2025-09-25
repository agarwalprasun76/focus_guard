"""
Domain Utilities

This module provides utility functions for domain handling, loading, and management.
"""

import re
from typing import Dict, List, Set, Optional, Pattern, Tuple, Any, Union

# Domain validation regex
DOMAIN_PATTERN: Pattern = re.compile(
    r'^((?=[a-z0-9-]{1,63}\.)([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,63}|localhost)$',
    re.IGNORECASE
)

# For IDN (Internationalized Domain Names) support
IDN_PATTERN: Pattern = re.compile(
    r'^((xn--[a-z0-9-]+\.)+[a-z]{2,}|[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,})$'
)

def normalize_domain(domain: Any) -> Optional[str]:
    """
    Normalize a domain name by converting to lowercase and removing whitespace.
    
    Args:
        domain: The domain to normalize (str, None, or any type that can be converted to string)
        
    Returns:
        Optional[str]: Normalized domain or None if input is invalid
    """
    if domain is None:
        return None
        
    try:
        domain = str(domain).strip()
        if not domain:  # Empty string after stripping
            return None
            
        domain = domain.lower()
        
        # Handle URLs
        if '://' in domain:
            domain = domain.split('://', 1)[1]
        if '/' in domain:
            domain = domain.split('/', 1)[0]
        if '?' in domain:
            domain = domain.split('?', 1)[0]
        if '#' in domain:
            domain = domain.split('#', 1)[0]
        if '@' in domain:  # Handle email addresses
            domain = domain.split('@', 1)[1]
            
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':', 1)[0]
            
        # Final cleanup
        domain = domain.strip('.').strip()
        
        return domain if is_valid_domain(domain) or is_valid_idn_domain(domain) else None
    except (AttributeError, IndexError, TypeError):
        return None

def is_valid_domain(domain: Any) -> bool:
    """
    Check if a domain is valid.
    
    Args:
        domain: The domain to validate (str, None, or any type that can be converted to string)
        
    Returns:
        bool: True if the domain is valid, False otherwise
    """
    try:
        if domain is None:
            return False
            
        domain = str(domain).strip()
        return bool(DOMAIN_PATTERN.match(domain)) or is_valid_idn_domain(domain)
    except (AttributeError, TypeError):
        return False

def is_valid_idn_domain(domain: Any) -> bool:
    """
    Check if a domain is a valid IDN (Internationalized Domain Name).
    
    Args:
        domain: The domain to validate (str, None, or any type that can be converted to string)
        
    Returns:
        bool: True if the domain is a valid IDN, False otherwise
    """
    try:
        if not domain:
            return False
            
        domain = str(domain).strip().lower()
        return bool(IDN_PATTERN.match(domain))
    except (AttributeError, TypeError):
        return False

def extract_domain_from_url(url: Any) -> Optional[str]:
    """
    Extract the domain from a URL or path string.
    
    Args:
        url: The URL or path to extract the domain from (str, None, or any type that can be converted to string)
        
    Returns:
        Optional[str]: The extracted domain or None if invalid or not a valid domain
    """
    try:
        if not url:
            return None
            
        url = str(url).strip()
        if not url:
            return None
            
        # Handle protocol-relative URLs (e.g., //example.com/path)
        if url.startswith('//'):
            url = url[2:]
        # Remove protocol if present
        elif '://' in url:
            url = url.split('://', 1)[1]
        
        # Extract the domain part (everything before the first /, ?, or #)
        domain_part = url.split('/')[0].split('?')[0].split('#')[0]
        
        # Remove port if present
        if ':' in domain_part:
            domain_part = domain_part.split(':', 1)[0]
            
        # Normalize and validate
        domain_part = domain_part.strip().lower().strip('.')
        
        # Only return if it's a valid domain
        if is_valid_domain(domain_part) or is_valid_idn_domain(domain_part):
            return domain_part
            
        # If we have a path but no protocol, the first part might be a domain
        if '/' in url and not url.startswith(('http://', 'https://')) and '.' in url.split('/')[0]:
            potential_domain = url.split('/')[0].split('?')[0].split('#')[0].split(':')[0]
            potential_domain = potential_domain.strip().lower().strip('.')
            if is_valid_domain(potential_domain) or is_valid_idn_domain(potential_domain):
                return potential_domain
                
        return None
    except (AttributeError, IndexError, TypeError):
        return None

def is_subdomain(domain: Any, parent_domain: Any) -> bool:
    """
    Check if a domain is a subdomain of another domain.
    
    Args:
        domain: The domain to check (str, None, or any type that can be converted to string)
        parent_domain: The potential parent domain (str, None, or any type that can be converted to string)
        
    Returns:
        bool: True if domain is a subdomain of parent_domain
    """
    domain = normalize_domain(domain)
    parent_domain = normalize_domain(parent_domain)
    
    if not domain or not parent_domain:
        return False
        
    # If they're exactly the same, it's not a subdomain
    if domain == parent_domain:
        return False
        
    # Check if domain ends with .parent_domain
    return domain.endswith('.' + parent_domain)
    
    if not domain or not parent_domain:
        return False
        
    # Exact match

def get_domain_parts(domain: Any) -> List[str]:
    """
    Split a domain into its parts.
    
    Args:
        domain: The domain to split (str, None, or any type that can be converted to string)
        
    Returns:
        List[str]: List of domain parts from TLD to subdomain, or empty list if invalid
    """
    try:
        domain = normalize_domain(domain)
        if not domain:
            return []
            
        parts = [p for p in domain.split('.') if p]  # Remove any empty parts
        return parts if len(parts) > 1 else []  # Must have at least 2 parts to be a valid domain
    except (AttributeError, TypeError):
        return []
