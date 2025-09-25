"""
Domain Excluder: Loads StevenBlack hosts file and checks if a domain should be excluded.
Uses a cached version of the hosts file to avoid downloading it every time.
"""
import os
import requests
import pickle
import time
from pathlib import Path
from typing import Set, Any, Optional

from .domain_utils import extract_domain_from_url
from core.logger.logger import get_logger

logger = get_logger("domain_classifier")

# StevenBlack hosts file with gambling, porn, social, fakenews
STEVENBLACK_HOSTS_URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/fakenews-gambling-porn-social/hosts"

# Cache settings
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cache")
HOSTS_CACHE_FILE = os.path.join(CACHE_DIR, "hosts_domains_cache.pkl")
CACHE_TTL_DAYS = 7  # Update cache if older than this many days

_excluded_domains: Set[str] = set()

def download_and_parse_hosts(url: str = STEVENBLACK_HOSTS_URL) -> Set[str]:
    """
    Downloads and parses the hosts file, returns a set of excluded domains.
    """
    logger.info(f"Downloading hosts file from {url}...")
    response = requests.get(url)
    domains = set()
    for line in response.text.splitlines():
        line = line.strip()
        if line.startswith("0.0.0.0") or line.startswith("127.0.0.1"):
            parts = line.split()
            if len(parts) >= 2:
                domain = parts[1].lower()
                if domain != "localhost":
                    domains.add(domain)
    
    # Save to cache
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(HOSTS_CACHE_FILE, 'wb') as f:
        pickle.dump({
            'timestamp': time.time(),
            'domains': domains
        }, f)
    
    logger.info(f"Downloaded and cached {len(domains)} excluded domains")
    return domains

def load_excluded_domains_from_cache() -> Set[str]:
    """
    Load excluded domains from cache if available and not expired.
    Returns None if cache is invalid or expired.
    """
    if not os.path.exists(HOSTS_CACHE_FILE):
        return None
    
    try:
        with open(HOSTS_CACHE_FILE, 'rb') as f:
            cache_data = pickle.load(f)
        
        # Check if cache is expired
        cache_age_days = (time.time() - cache_data['timestamp']) / (24 * 60 * 60)
        if cache_age_days > CACHE_TTL_DAYS:
            logger.info(f"Cache is {cache_age_days:.1f} days old (> {CACHE_TTL_DAYS} days), will refresh")
            return None
        
        domains = cache_data['domains']
        logger.info(f"Loaded {len(domains)} excluded domains from cache")
        return domains
    except Exception as e:
        logger.error(f"Error loading cache: {e}")
        return None

def load_excluded_domains():
    """Load excluded domains from cache or download if needed"""
    global _excluded_domains
    
    # Try to load from cache first
    domains = load_excluded_domains_from_cache()
    
    if domains is None:
        try:
            # Cache invalid or expired, download fresh data
            domains = download_and_parse_hosts()
        except Exception as e:
            logger.warning(f"Could not download excluded domains: {e}")
            # If download fails but we have a cache (even if expired), use it as fallback
            try:
                with open(HOSTS_CACHE_FILE, 'rb') as f:
                    domains = pickle.load(f)['domains']
                logger.info(f"Using expired cache with {len(domains)} domains as fallback")
            except Exception:
                # No cache available, use a minimal set of excluded domains
                domains = set([
                    "pornhub.com", "xvideos.com", "xnxx.com",
                    "bet365.com", "gambling.com", "casino.com",
                    "fakenews.com", "breitbart.com"
                ])
                logger.info(f"Using minimal set of {len(domains)} excluded domains")
    
    _excluded_domains = domains

# Load on import with caching
load_excluded_domains()

def domain_excluder(domain: Any) -> bool:
    """
    Check if a domain should be excluded (blocked).
    
    This function is specifically for web domains and will return False for email addresses.
    
    Args:
        domain: The domain to check (can be a string or URL). Email addresses will be rejected.
        
    Returns:
        bool: True if the domain should be excluded, False otherwise or if input is an email
    """
    # Reject invalid inputs and email addresses immediately
    if not domain or not isinstance(domain, str) or '@' in str(domain):
        return False
        
    try:
        # Normalize the domain
        domain = domain.strip().lower()
        
        # Extract domain if it's a URL or has path/query parameters
        if '://' in domain or '/' in domain or '?' in domain or '#' in domain or ':' in domain:
            domain = extract_domain_from_url(domain)
            if not domain:  # If extraction failed
                return False
        
        # Normalize the domain (in case it wasn't a URL but had special chars)
        domain = domain.lower().strip('.')
        if not domain:
            return False
            
        # Check exact match first (fast path)
        if domain in _excluded_domains:
            return True
            
        # Check parent domains
        domain_parts = domain.split('.')
        for i in range(1, len(domain_parts)):
            parent_domain = '.'.join(domain_parts[i:])
            if parent_domain in _excluded_domains:
                return True
                
    except (AttributeError, IndexError, ValueError):
        return False
        
    return False
