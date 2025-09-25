"""
Domain Whitelist: Centralized allowlist for always-allowed domains.
Uses the configuration from domain_config.py and domain utilities.
"""
from typing import Set, Optional, Union, List

from .domain_config import domain_config
from .domain_utils import (
    normalize_domain,
    is_valid_domain,
    extract_domain_from_url,
    is_subdomain,
    get_domain_parts
)

# Load whitelisted domains from configuration
_WHITELISTED_DOMAINS: Set[str] = set()

# Initialize whitelisted domains with normalized values
for domain in domain_config["whitelist"]:
    normalized = normalize_domain(domain)
    if normalized:
        _WHITELISTED_DOMAINS.add(normalized)

def domain_whitelist(domain: Optional[Union[str, List[str]]]) -> bool:
    """
    Check if a domain or any domain in a list is whitelisted.
    
    This function is specifically for web domains and will return False for email addresses.
    
    Args:
        domain: The domain(s) to check (can be a string or list of strings,
               and can include full URLs). Email addresses will be rejected.
        
    Returns:
        bool: True if any domain is whitelisted, False otherwise or if input is an email
    """
    def _check_single_domain(d: Optional[str]) -> bool:
        # Reject email addresses immediately - they are not valid domain inputs
        if not d or not isinstance(d, str) or '@' in d:
            return False
        return _is_domain_whitelisted(d)
    
    if not domain:
        return False
    
    # Handle list of domains
    if isinstance(domain, list):
        return any(_check_single_domain(d) for d in domain if d)
    
    return _check_single_domain(domain)

def _is_domain_whitelisted(domain: str) -> bool:
    """
    Internal function to check if a single domain is whitelisted.
    
    Args:
        domain: The domain to check (can be a URL, email, or plain domain)
        
    Returns:
        bool: True if the domain is whitelisted, False otherwise
    """
    # Handle None or empty input
    if not domain or not isinstance(domain, str):
        return False
        
    # Handle email addresses - extract domain part
    if '@' in domain:
        # Only extract the domain part if it's a valid email format
        email_parts = domain.split('@')
        if len(email_parts) != 2 or not email_parts[1]:
            return False
        domain = email_parts[1]
    
    # If it looks like a URL, extract the domain
    if '://' in domain or '/' in domain or '?' in domain or '#' in domain or ':' in domain:
        domain = extract_domain_from_url(domain)
        if not domain:  # If extraction failed
            return False
    
    # Normalize the domain
    domain = normalize_domain(domain)
    if not domain:
        return False
    
    # Check exact match first (fast path)
    if domain in _WHITELISTED_DOMAINS:
        return True
    
    # Check parent domains (subdomain handling)
    domain_parts = get_domain_parts(domain)
    if not domain_parts or len(domain_parts) < 2:  # Not a valid domain
        return False
        
    # Check all possible parent domains
    for i in range(1, len(domain_parts)):
        parent_domain = '.'.join(domain_parts[i:])
        if parent_domain in _WHITELISTED_DOMAINS:
            return True
    
    return False

def get_whitelisted_domains() -> Set[str]:
    """
    Get a set of all whitelisted domains.
    
    Returns:
        Set[str]: A copy of the whitelisted domains set
    """
    return _WHITELISTED_DOMAINS.copy()

def add_to_whitelist(domains: Union[str, List[str]]) -> None:
    """
    Add one or more domains to the whitelist.
    
    Args:
        domains: Domain or list of domains to add
    """
    if not domains:
        return
        
    if isinstance(domains, str):
        domains = [domains]
    
    for domain in domains:
        if not domain:
            continue
            
        normalized = normalize_domain(domain)
        if normalized and normalized not in _WHITELISTED_DOMAINS:
            _WHITELISTED_DOMAINS.add(normalized)

def remove_from_whitelist(domains: Union[str, List[str]]) -> None:
    """
    Remove one or more domains from the whitelist.
    
    Args:
        domains: Domain or list of domains to remove
    """
    if not domains:
        return
        
    if isinstance(domains, str):
        domains = [domains]
    
    for domain in domains:
        if not domain:
            continue
            
        normalized = normalize_domain(domain)
        if normalized and normalized in _WHITELISTED_DOMAINS:
            _WHITELISTED_DOMAINS.remove(normalized)
