"""
Domain Blocker: Central logic for deciding if a domain should be blocked, allowed, or flagged.

This module provides functionality to determine if a domain should be blocked based on various
policies including whitelisting, category-based blocking, and approved-only mode.

Features:
- Domain whitelisting/blacklisting
- Category-based blocking
- Approved-only mode
- Domain exclusion rules
"""
from typing import List, Optional, Set, Union

from core.domain_classifier import (
    domain_excluder,
    domain_whitelist,
    classify_domain,
    is_valid_domain,
    normalize_domain,
    extract_domain as extract_domain_from_url
)

def block_reason(domain: Optional[Union[str, List[str]]], 
                approved_only: bool = False, 
                block_categories: Optional[Union[List[str], Set[str]]] = None) -> Optional[str]:
    """
    Determine if a domain should be blocked and return the reason.

    Args:
        domain: The domain(s) to check. Can be a string or list of strings.
        approved_only: If True, only whitelisted domains are allowed.
        block_categories: List of categories to block (e.g., ['social', 'news'])

    Returns:
        Optional[str]: The reason for blocking, or None if the domain should be allowed.
                     Possible reasons: 'excluded', 'not_whitelisted', or the category name.
    """
    if not domain:
        return None

    # Handle list of domains
    if isinstance(domain, list):
        for d in domain:
            reason = _get_block_reason_for_single_domain(d, approved_only, block_categories)
            if reason:
                return reason
        return None
    
    return _get_block_reason_for_single_domain(domain, approved_only, block_categories)

def _get_block_reason_for_single_domain(domain: str, 
                                     approved_only: bool,
                                     block_categories: Optional[Union[List[str], Set[str]]] = None) -> Optional[str]:
    """Internal function to check a single domain."""
    # Normalize the domain
    normalized = normalize_domain(domain)
    if not normalized:
        return "invalid_domain"
    
    # Check exclusion list
    if domain_excluder(normalized):
        return "excluded"
        
    # Check whitelist
    if domain_whitelist(normalized):
        return None
        
    # Get category
    category = classify_domain(normalized)
    
    # Approved-only mode
    if approved_only:
        return "not_whitelisted"
        
    # Category-based blocking
    if block_categories and category in block_categories:
        return category
        
    return None

def should_block(domain: Optional[Union[str, List[str]]], **kwargs) -> bool:
    """
    Check if a domain should be blocked based on the current policy.
    
    Args:
        domain: The domain(s) to check. Can be a string or list of strings.
        **kwargs: Additional arguments passed to block_reason()
        
    Returns:
        bool: True if the domain should be blocked, False otherwise.
    """
    return block_reason(domain, **kwargs) is not None



def run_tests():
    """Run test cases for the domain blocker."""
    test_domains = [
        "facebook.com", "mail.office.com", "github.com", "cnn.com", "amazon.com",
        "pornhub.com", "youtube.com", "khanacademy.org", "randomsite.xyz",
        "artofproblemsolving.com", "bet365.com", "fakenewswebsite.com"
    ]
    
    print("\n=== Domain Blocker Tests ===\n")
    
    # Test 1: Default policy (block excluded only)
    print("1. Default policy (block excluded only):")
    for d in test_domains:
        reason = block_reason(d)
        print(f"{d:30s} -> {'BLOCK' if reason else 'ALLOW'}: {reason or 'Allowed'}")
    
    # Test 2: Approved-only policy
    print("\n2. Approved-only policy (only whitelisted domains allowed):")
    for d in test_domains:
        reason = block_reason(d, approved_only=True)
        print(f"{d:30s} -> {'BLOCK' if reason else 'ALLOW'}: {reason or 'Whitelisted'}")
    
    # Test 3: Category-based blocking
    print("\n3. Block social and news categories:")
    for d in test_domains:
        reason = block_reason(d, block_categories=['social','news'])
        print(f"{d:30s} -> {'BLOCK' if reason else 'ALLOW'}: {reason or 'Allowed'}")
    
    # Test 4: URL handling
    print("\n4. URL handling tests:")
    test_urls = [
        "https://www.github.com/path?query=1",
        "http://sub.domain.com:8080/path",
        "invalid domain"
    ]
    for url in test_urls:
        reason = block_reason(url)
        print(f"{url:40s} -> {'BLOCK' if reason else 'ALLOW'}: {reason or 'Allowed'}")

if __name__ == "__main__":
    run_tests()
