"""
Domain utility functions.

This module provides utility functions for domain handling, URL parsing,
and other common operations used throughout the system.
"""

import re
import urllib.parse
from typing import Optional, Tuple, List

from core_v2.domain.models import Domain, URL, DomainValidationError


def extract_domain_from_url(url: str) -> Optional[str]:
    """
    Extract the domain from a URL.
    
    Args:
        url: The URL to extract the domain from.
        
    Returns:
        The domain, or None if it couldn't be extracted.
        For URLs with 'www.' prefix, returns the domain without the prefix.
    """
    if url is None:
        return None
        
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        
        # Remove username/password if present
        if '@' in domain:
            domain = domain.split('@', 1)[1]
            
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':', 1)[0]
        
        # Convert to lowercase
        domain = domain.lower() if domain else None
        
        # Remove 'www.' prefix if present
        if domain and domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except Exception:
        return None


def normalize_domain(domain: str) -> str:
    """
    Normalize a domain string.
    
    Normalization includes:
    - Converting to lowercase
    - Removing trailing dots
    - Removing leading/trailing whitespace
    
    Args:
        domain: The domain to normalize.
        
    Returns:
        The normalized domain.
    """
    if not domain:
        return ""
    
    # Remove whitespace and convert to lowercase
    domain = domain.strip().lower()
    
    # Remove trailing dots
    domain = domain.rstrip('.')
    
    return domain


def is_valid_domain(domain: str) -> bool:
    """
    Check if a domain is valid.
    
    Args:
        domain: The domain to check.
        
    Returns:
        True if the domain is valid, False otherwise.
    """
    if not domain:
        return False
    
    # Basic validation
    if ' ' in domain or len(domain) > 255:
        return False
    
    # Check for at least one dot (for TLD)
    if '.' not in domain:
        return False
    
    # More comprehensive validation using regex
    # This pattern checks for valid domain name format
    pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    return bool(re.match(pattern, domain))


def get_domain_parts(domain: str) -> List[str]:
    """
    Split a domain into its component parts.
    
    Args:
        domain: The domain to split.
        
    Returns:
        A list of domain parts, e.g., ["www", "example", "com"]
    """
    return normalize_domain(domain).split('.')


def get_parent_domains(domain: str) -> List[str]:
    """
    Get all parent domains for a given domain.
    
    For example, for "www.example.com", returns ["example.com", "com"].
    
    Args:
        domain: The domain to get parent domains for.
        
    Returns:
        A list of parent domains, from most specific to least specific.
    """
    if domain is None:
        return []
        
    # Normalize and split the domain
    parts = get_domain_parts(domain)
    
    # Filter out empty parts (which can happen with consecutive dots)
    parts = [part for part in parts if part]
    
    if len(parts) <= 1:
        return []
    
    parent_domains = []
    for i in range(1, len(parts)):
        parent_domain = '.'.join(parts[i:])
        parent_domains.append(parent_domain)
    
    return parent_domains


def is_subdomain(domain: str, parent_domain: str) -> bool:
    """
    Check if a domain is a subdomain of another domain.
    
    Args:
        domain: The potential subdomain.
        parent_domain: The potential parent domain.
        
    Returns:
        True if domain is a subdomain of parent_domain.
    """
    domain = normalize_domain(domain)
    parent_domain = normalize_domain(parent_domain)
    
    if domain == parent_domain:
        return False
    
    return domain.endswith('.' + parent_domain)


def get_registered_domain(domain: str) -> str:
    """
    Get the registered domain (without subdomains).
    
    This is a simplistic implementation. For a more accurate approach,
    a library like tldextract would be used.
    
    Args:
        domain: The domain to get the registered domain for.
        
    Returns:
        The registered domain (e.g., "example.com" for "www.example.com").
    """
    if domain is None:
        return ""
        
    parts = get_domain_parts(domain)
    
    # This is a simplified approach; a more robust implementation would use tldextract
    if len(parts) <= 2:
        return domain
    
    # Special case for known multi-part TLDs
    if len(parts) >= 3 and '.'.join(parts[-2:]) in ["co.uk", "com.au", "org.uk"]:
        return '.'.join(parts[-3:])
    
    return '.'.join(parts[-2:])


def create_domain_from_url(url: str) -> Optional[Domain]:
    """
    Create a Domain object from a URL.
    
    Args:
        url: The URL to extract the domain from.
        
    Returns:
        A Domain object, or None if the domain couldn't be extracted or is invalid.
    """
    domain_str = extract_domain_from_url(url)
    if not domain_str:
        return None
    
    try:
        return Domain(domain_str)
    except DomainValidationError:
        return None


def create_url_from_string(url_str: str) -> Optional[URL]:
    """
    Create a URL object from a string.
    
    Args:
        url_str: The URL string.
        
    Returns:
        A URL object, or None if the URL is invalid.
    """
    try:
        return URL(url_str)
    except ValueError:
        return None


def is_ip_address(domain: str) -> bool:
    """
    Check if a domain is an IP address.
    
    Args:
        domain: The domain to check.
        
    Returns:
        True if the domain is an IP address, False otherwise.
    """
    if domain is None or not isinstance(domain, str):
        return False
        
    # IPv4 pattern
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    
    # IPv6 pattern (simplified)
    ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    
    # Basic check for pattern match
    if not (re.match(ipv4_pattern, domain) or re.match(ipv6_pattern, domain)):
        return False
    
    # For IPv4, validate that each octet is in range 0-255
    if re.match(ipv4_pattern, domain):
        octets = domain.split('.')
        for octet in octets:
            try:
                value = int(octet)
                if value < 0 or value > 255:
                    return False
            except ValueError:
                return False
    
    return True


def is_localhost(domain: str) -> bool:
    """
    Check if a domain is localhost.
    
    Args:
        domain: The domain to check.
        
    Returns:
        True if the domain is localhost, False otherwise.
    """
    localhost_patterns = [
        r'^localhost$',
        r'^127\.0\.0\.1$',
        r'^::1$'
    ]
    
    return any(bool(re.match(pattern, domain)) for pattern in localhost_patterns)
