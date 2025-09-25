"""
Test Domain Contexts
A utility script to test different domains in different calendar contexts
"""
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

# Domain categories for classification
DOMAIN_CATEGORIES = {
    "work": ["office.com", "slack.com", "zoom.us", "github.com", "atlassian.com", "microsoft.com"],
    "social": ["facebook.com", "twitter.com", "instagram.com", "tiktok.com", "snapchat.com", "reddit.com", "linkedin.com"],
    "news": ["cnn.com", "bbc.com", "nytimes.com", "theguardian.com", "reuters.com", "foxnews.com"],
    "shopping": ["amazon.com", "ebay.com", "aliexpress.com", "walmart.com", "etsy.com"],
    "entertainment": ["youtube.com", "netflix.com", "hulu.com", "spotify.com", "twitch.tv"],
    "education": ["khanacademy.org", "coursera.org", "edx.org", "udemy.com", "wikipedia.org"],
}

# Whitelist of always-allowed domains
WHITELIST = ["google.com", "docs.google.com", "drive.google.com", "calendar.google.com"]

# Calendar context rules (which domain categories are allowed in which contexts)
CONTEXT_RULES = {
    "focus": {
        "allowed": ["work", "education"],
        "blocked": ["social", "entertainment", "shopping"]
    },
    "meeting": {
        "allowed": ["work", "education"],
        "blocked": ["social", "entertainment", "shopping"]
    },
    "break": {
        "allowed": ["work", "education", "news", "entertainment"],
        "blocked": []
    },
    "none": {
        "allowed": ["work", "education", "news"],
        "blocked": ["social"]
    }
}

def classify_domain(domain):
    """Classify a domain without external API calls"""
    if not domain:
        return "unknown"
        
    domain = domain.lower().strip()
    
    # Check whitelist
    if domain in WHITELIST:
        return "whitelisted"
        
    # Check categories
    for category, domains in DOMAIN_CATEGORIES.items():
        for known in domains:
            if domain == known or domain.endswith('.' + known):
                return category
                
    return "unknown"

def is_domain_allowed(domain, context="none"):
    """Check if a domain is allowed in the given calendar context"""
    if not domain:
        return True, "No domain to check"
        
    category = classify_domain(domain)
    
    # Whitelisted domains are always allowed
    if category == "whitelisted":
        return True, f"Domain is whitelisted"
    
    # Get context rules
    rules = CONTEXT_RULES.get(context, CONTEXT_RULES["none"])
    
    # Check if category is explicitly allowed
    if category in rules["allowed"]:
        return True, f"Category '{category}' is allowed in context '{context}'"
    
    # Check if category is explicitly blocked
    if category in rules["blocked"]:
        return False, f"Category '{category}' is blocked in context '{context}'"
    
    # Default behavior for unknown categories
    if category == "unknown":
        return True, f"Unknown domain category"
    
    # For other categories not explicitly allowed or blocked
    return True, f"Category '{category}' is not restricted in context '{context}'"

def test_domain_in_all_contexts(domain):
    """Test a domain in all available contexts"""
    print(f"\nDomain: {domain}")
    category = classify_domain(domain)
    print(f"Category: {category}")
    print("\nContext allowances:")
    
    for context in CONTEXT_RULES.keys():
        is_allowed, reason = is_domain_allowed(domain, context)
        status = "✅ ALLOWED" if is_allowed else "❌ BLOCKED"
        print(f"  {context}: {status} - {reason}")

def main():
    """Main function for testing domains in different contexts"""
    print("Domain Context Testing Utility")
    print("=============================")
    print("This utility tests domains against different calendar contexts.")
    
    # Test some common domains
    test_domains = [
        "youtube.com",
        "github.com", 
        "facebook.com",
        "netflix.com",
        "google.com",
        "microsoft.com"
    ]
    
    for domain in test_domains:
        test_domain_in_all_contexts(domain)
    
    # Interactive mode
    print("\n\nEnter domains to test (or 'quit' to exit):")
    while True:
        try:
            domain = input("> ").strip().lower()
            if domain == 'quit':
                break
                
            if not domain:
                continue
                
            # Add domain suffix if not provided
            if '.' not in domain:
                domain += '.com'
                
            test_domain_in_all_contexts(domain)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
    
    print("\nTest complete")

if __name__ == "__main__":
    main()
