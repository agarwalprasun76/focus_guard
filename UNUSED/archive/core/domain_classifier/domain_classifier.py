"""
Rule-based domain classifier for categorizing domains into types like work, social, news, etc.
Uses centralized domain configuration from domain_config.py and domain utilities.
"""

from typing import Optional, Dict, List, Set

from .domain_config import domain_config, DomainConfig
from .domain_utils import (
    normalize_domain,
    is_valid_domain,
    is_valid_idn_domain,
    extract_domain_from_url,
    is_subdomain,
    get_domain_parts
)
from core.logger.logger import get_logger

logger = get_logger("domain_classifier")

# Load domain categories from configuration
CATEGORY_KEYWORDS: Dict[str, List[str]] = domain_config["categories"]

# Pre-process domains for faster lookups
_domain_cache: Dict[str, str] = {}

# Build a cache of all domains for faster lookups
for category, domains in CATEGORY_KEYWORDS.items():
    for domain in domains:
        normalized = normalize_domain(domain)
        if normalized:
            _domain_cache[normalized] = category

def classify_domain(domain: str) -> Optional[str]:
    """
    Classify a domain into a category.
    
    This function can handle both plain domains (e.g., 'example.com') and URLs
    (e.g., 'https://example.com/path'). Email addresses will be rejected.
    
    Args:
        domain: The domain or URL to classify
        
    Returns:
        str: The category of the domain, or None if not found or input is invalid
    """
    # Add debug logging
    logger.info(f"Classifying domain: {domain}")
    
    # Reject invalid inputs and email addresses immediately
    if not domain or not isinstance(domain, str) or '@' in str(domain):
        logger.warning(f"Invalid domain format: {domain}")
        return None
    
    # If it looks like a URL or has special characters, extract the domain first
    if '://' in domain or '/' in domain or '?' in domain or '#' in domain or ':' in domain:
        original_domain = domain
        domain = extract_domain_from_url(domain)
        logger.info(f"Extracted domain {domain} from URL {original_domain}")
        if not domain:
            logger.warning(f"Failed to extract domain from URL: {original_domain}")
            return None
    
    # Normalize the domain
    original_domain = domain
    domain = normalize_domain(domain)
    if domain != original_domain:
        logger.info(f"Normalized domain: {original_domain} -> {domain}")
    if not domain:
        logger.warning(f"Failed to normalize domain: {original_domain}")
        return None
        
    # Final validation - ensure it's a valid domain
    if not (is_valid_domain(domain) or is_valid_idn_domain(domain)):
        logger.warning(f"Invalid domain after normalization: {domain}")
        return None
    
    # Check exact match first (fast path)
    if domain in _domain_cache:
        category = _domain_cache[domain]
        logger.info(f"Domain {domain} found in cache with category: {category}")
        return category
    
    # Check subdomains
    domain_parts = get_domain_parts(domain)
    for i in range(1, len(domain_parts)):
        parent_domain = '.'.join(domain_parts[i:])
        if parent_domain in _domain_cache:
            category = _domain_cache[parent_domain]
            logger.info(f"Domain {domain} matched to parent domain {parent_domain} with category: {category}")
            return category
    
    logger.warning(f"Domain {domain} not found in any category")
    return None

def get_all_domains() -> Dict[str, List[str]]:
    """
    Get all domains organized by category.
    
    Returns:
        Dict[str, List[str]]: Dictionary mapping categories to lists of domains
    """
    return CATEGORY_KEYWORDS.copy()

def get_all_categories() -> List[str]:
    """
    Get a list of all available domain categories.
    
    Returns:
        List[str]: List of category names
    """
    return list(CATEGORY_KEYWORDS.keys())

if __name__ == "__main__":
    # Demo/test
    test_domains = [
        "facebook.com", "mail.office.com", "github.com", "cnn.com", "amazon.com",
        "pornhub.com", "youtube.com", "khanacademy.org", "randomsite.xyz"
    ]
    for d in test_domains:
        logger.info(f"{d:20s} -> {classify_domain(d)}")
