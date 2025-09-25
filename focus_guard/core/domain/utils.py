"""
Domain utility functions.

This module provides utility functions for working with domains,
such as extracting domains from URLs, validating domains, and normalizing domain formats.
"""

import re
from typing import Optional, Any
from urllib.parse import urlparse

# Domain validation regex
DOMAIN_PATTERN = re.compile(
    r'^((localhost)|((?=[a-z0-9-]{1,63}\.)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+([a-z]{2,63})))$',
    re.IGNORECASE
)

# For IDN (Internationalized Domain Names) support
IDN_PATTERN = re.compile(
    r'^((xn--[a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}|([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,})$'
)


def is_valid_domain(domain: Any) -> bool:
    """
    Check if a domain is valid.
    
    Args:
        domain: The domain to validate
        
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
        domain: The domain to validate
        
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


def normalize_domain(domain: Any) -> Optional[str]:
    """
    Normalize a domain name by converting to lowercase and removing whitespace.
    
    Args:
        domain: The domain to normalize
        
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


def normalize_url(url: Any) -> Optional[str]:
    """
    Normalize a URL string.
    
    This function ensures that the URL has a scheme (http:// or https://),
    and performs basic normalization.
    
    Args:
        url: The URL to normalize (can be string or any object with __str__).
        
    Returns:
        The normalized URL string, or None if the URL is malformed.
    """
    # Handle None or invalid inputs
    if url is None:
        return None
        
    try:
        # Convert to string and strip whitespace
        url_str = str(url).strip()
        
        # Handle empty strings
        if not url_str:
            return None
        
        # Define patterns for malformed URLs
        malformed_patterns = [
            # Empty schemes
            lambda u: u in ('http://', 'https://', '://', ':/'),
            # Triple slashes
            lambda u: '///' in u,
            # Invalid scheme
            lambda u: u.startswith('://'),
        ]
        
        # Check for empty username in authentication (e.g., http://@example.com)
        # But only if it's not already a well-formed URL with a scheme
        if '@' in url_str and '://' in url_str and not url_str.startswith(('http://', 'https://')):
            # Extract the part after the scheme
            scheme_part, rest = url_str.split('://', 1)
            if rest.startswith('@'):
                return None
        
        # Check if URL matches any malformed pattern
        if any(pattern(url_str) for pattern in malformed_patterns):
            return None
            
        # Add scheme if missing
        if not url_str.startswith(('http://', 'https://')): 
            # Handle protocol-relative URLs (starting with //)
            if url_str.startswith('//') and not url_str.startswith('///'):
                return 'https:' + url_str
            # Add https:// prefix for all other cases
            return 'https://' + url_str
            
        return url_str
    except (AttributeError, TypeError):
        return None


def extract_domain_from_url(url: Any) -> Optional[str]:
    """
    Extract the domain from a URL.
    
    This function handles various URL formats, including those with or without
    protocols, protocol-relative URLs, and paths. It also removes 'www.' prefixes,
    ports, and authentication information.
    
    Args:
        url: The URL to extract the domain from.
        
    Returns:
        The normalized domain extracted from the URL, or None if the URL is invalid.
    """
    if url is None:
        return None
        
    try:
        url_str = str(url).strip()
        if not url_str:
            return None
            
        # Handle protocol-relative URLs (e.g., //example.com/path)
        if url_str.startswith('//'):
            url_str = url_str[2:]
        # Add protocol if missing to help urlparse
        elif not url_str.startswith(('http://', 'https://')):
            # Check if it's a simple domain or path
            if '/' in url_str and not url_str.startswith('/'):
                # Might be a domain with path
                potential_domain = url_str.split('/')[0]
                if '.' in potential_domain:
                    url_str = 'http://' + url_str
            else:
                # Simple domain or hostname
                url_str = 'http://' + url_str
        
        # Use urlparse for robust parsing
        parsed = urlparse(url_str)
        domain = parsed.netloc
        
        # Handle empty netloc (might be a path only)
        if not domain and parsed.path:
            # Try to extract domain from path
            potential_domain = parsed.path.split('/')[0]
            if '.' in potential_domain:
                domain = potential_domain
        
        # Check for empty username in authentication (e.g., http://@example.com)
        if '@' in domain:
            auth_part, domain_part = domain.split('@', 1)
            if not auth_part:  # Empty username before @
                return None
            domain = domain_part
            
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':', 1)[0]
        
        # Convert to lowercase
        domain = domain.lower() if domain else None
        
        # Remove 'www.' prefix if present
        if domain and domain.startswith('www.'):
            domain = domain[4:]
        
        # Final validation
        if domain and (is_valid_domain(domain) or is_valid_idn_domain(domain)):
            return domain
            
        return None
    except Exception:
        return None