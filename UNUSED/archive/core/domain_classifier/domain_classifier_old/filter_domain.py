"""
Domain Filtering Pipeline: Combines excluder, classifier, and whitelist.
"""
from .domain_excluder import domain_excluder
from .domain_classifier import classify_domain
from .domain_whitelist import domain_whitelist
from core.logger.logger import get_logger

logger = get_logger("domain_classifier")

def filter_domain(domain: str) -> str:
    """
    Returns the filtering decision for a domain:
    - 'excluded': blocked by excluder (e.g., gambling, porn, etc.)
    - 'whitelisted': explicitly allowed
    - category: classified category (e.g., 'social', 'news', etc.)
    - 'unknown': not matched by any rule
    """
    if domain_excluder(domain):
        return "excluded"
    if domain_whitelist(domain):
        return "whitelisted"
    category = classify_domain(domain)
    return category or "unknown"

if __name__ == "__main__":
    test_domains = [
        "facebook.com", "mail.office.com", "github.com", "cnn.com", "amazon.com",
        "pornhub.com", "youtube.com", "khanacademy.org", "randomsite.xyz",
        "artofproblemsolving.com", "bet365.com", "fakenewswebsite.com"
    ]
    for d in test_domains:
        logger.info(f"{d:30s} -> {filter_domain(d)}")
