"""
Domain utility functions.

This module provides comprehensive domain handling utilities including:
- Domain validation and normalization
- URL parsing and domain extraction
- Domain hierarchy and relationship utilities
- IP address and localhost detection
"""

import re
import urllib.parse
from typing import Optional, List, Any

from focus_guard.core.domain.models import Domain, URL, DomainValidationError

# Domain validation patterns
DOMAIN_PATTERN = re.compile(
    r'^((?=[a-z0-9-]{1,63}\.)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+(([a-z]{2,63})|localhost))$',
    re.IGNORECASE
)

# For IDN (Internationalized Domain Names) support
IDN_PATTERN = re.compile(
    r'^((xn--[a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}|([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,})$'
)

# IP address patterns
IPV4_PATTERN = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
IPV6_PATTERN = re.compile(r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$')

# Localhost patterns
LOCALHOST_PATTERNS = ['localhost', '127.0.0.1', '::1', '0:0:0:0:0:0:0:1']

def is_valid_domain(domain: Any) -> bool:
    """Check if a domain is valid."""
    try:
        if not domain:
            return False
        domain = str(domain).strip()
        return bool(DOMAIN_PATTERN.match(domain)) or is_valid_idn_domain(domain)
    except (AttributeError, TypeError):
        return False

def is_valid_idn_domain(domain: Any) -> bool:
    """Check if a domain is a valid IDN."""
    try:
        return bool(domain and IDN_PATTERN.match(str(domain).strip()))
    except (AttributeError, TypeError):
        return False

def normalize_domain(domain: Any) -> str:
    """Normalize a domain name."""
    try:
        return str(domain).strip().lower().rstrip('.') if domain else ""
    except (AttributeError, TypeError):
        return ""

def normalize_url(url: Any) -> Optional[str]:
    """Normalize a URL string."""
    try:
        url_str = str(url).strip()
        if not url_str:
            return None
            
        if url_str.startswith('//'):
            url_str = 'http:' + url_str
        if '://' not in url_str:
            url_str = 'http://' + url_str
            
        parsed = urllib.parse.urlparse(url_str)
        return urllib.parse.urlunparse(parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower()
        ))
    except (ValueError, AttributeError, TypeError):
        return None

def extract_domain_from_url(url: Any) -> Optional[str]:
    """Extract and normalize domain from URL."""
    try:
        normalized = normalize_url(url)
        if not normalized:
            return None
            
        parsed = urllib.parse.urlparse(normalized)
        domain = parsed.netloc
        
        if '@' in domain:
            _, domain = domain.split('@', 1)
        if ':' in domain:
            domain = domain.split(':', 1)[0]
            
        domain = normalize_domain(domain)
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain if domain and is_valid_domain(domain) else None
    except (ValueError, AttributeError, TypeError):
        return None

def get_domain_parts(domain: str) -> List[str]:
    """Split domain into parts."""
    return [p for p in normalize_domain(domain).split('.') if p]

def get_parent_domains(domain: str) -> List[str]:
    """Get all parent domains."""
    parts = get_domain_parts(domain)
    return ['.'.join(parts[i:]) for i in range(1, len(parts))] if len(parts) > 1 else []

def is_subdomain(domain: str, parent_domain: str) -> bool:
    """Check if domain is a subdomain of parent_domain."""
    if not all([domain, parent_domain]):
        return False
    domain = normalize_domain(domain)
    parent = normalize_domain(parent_domain)
    return domain != parent and domain.endswith('.' + parent)

def get_registered_domain(domain: str) -> str:
    """Get registered domain (without subdomains)."""
    parts = get_domain_parts(domain)
    if not parts:
        return ""
    return '.'.join(parts[-2:]) if len(parts) > 1 else domain

def is_ip_address(domain: str) -> bool:
    """Check if domain is an IP address."""
    if not domain:
        return False
    return bool(IPV4_PATTERN.match(domain) or IPV6_PATTERN.match(domain))

def is_localhost(domain: str) -> bool:
    """Check if domain is localhost."""
    return normalize_domain(domain) in LOCALHOST_PATTERNS if domain else False

def create_url_from_string(url_str: str) -> Optional[URL]:
    """Create URL object from string."""
    try:
        return URL(url_str) if url_str else None
    except (ValueError, AttributeError, TypeError):
        return None
