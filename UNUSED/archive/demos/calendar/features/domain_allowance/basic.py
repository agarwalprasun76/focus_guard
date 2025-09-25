"""
Basic Domain Allowance

Implements calendar-based domain allowance with minimal memory usage.
This is a lightweight implementation focused on domain classification and allowance.

Features:
- Domain classification into categories
- Context-based domain allowance rules
- Memory-efficient implementation
- Whitelist support for critical domains
"""
import sys
import os
import time
import datetime
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

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
        return False, f"Unknown domain category"
    
    # For other categories not explicitly allowed or blocked
    return True, f"Category '{category}' is not restricted in context '{context}'"

def simulate_calendar_context():
    """Simulate calendar context based on current time"""
    current_hour = datetime.datetime.now().hour
    
    # Simulate different contexts based on time of day
    if 9 <= current_hour < 12:
        return "focus", "Morning focus time"
    elif 12 <= current_hour < 13:
        return "break", "Lunch break"
    elif 13 <= current_hour < 17:
        return "meeting", "Afternoon meetings"
    elif 17 <= current_hour < 19:
        return "break", "Evening break"
    else:
        return "none", "No scheduled activity"

def test_domain_in_context(domain, context):
    """Test if a domain is allowed in a specific context"""
    category = classify_domain(domain)
    is_allowed, reason = is_domain_allowed(domain, context)
    
    print(f"\nDomain: {domain}")
    print(f"Category: {category}")
    print(f"Context: {context}")
    print(f"Allowed: {'YES' if is_allowed else 'NO'}")
    print(f"Reason: {reason}")
    
    return is_allowed

def main():
    """Main function for memory-efficient calendar domain testing"""
    parser = argparse.ArgumentParser(description='Memory-Efficient Calendar Domain Test')
    parser.add_argument('--context', type=str, choices=['focus', 'meeting', 'break', 'none'],
                        help='Calendar context to use (default: auto-detect based on time)')
    parser.add_argument('--domain', type=str, help='Specific domain to test')
    args = parser.parse_args()
    
    # Get calendar context (from args or auto-detect)
    if args.context:
        context = args.context
        context_source = "command-line argument"
    else:
        context, context_source = simulate_calendar_context()
    
    print("Memory-Efficient Calendar Domain Test")
    print("-------------------------------------")
    print(f"Current context: {context} (from {context_source})")
    
    # Test a specific domain if provided
    if args.domain:
        domain = args.domain.lower()
        if '.' not in domain:
            domain += '.com'
        test_domain_in_context(domain, context)
        return
    
    # Test predefined domains
    test_domains = [
        "youtube.com",
        "github.com", 
        "stackoverflow.com",
        "facebook.com",
        "twitter.com",
        "linkedin.com",
        "netflix.com",
        "amazon.com",
        "google.com",
        "microsoft.com"
    ]
    
    print("\nTesting domains in current context:")
    for domain in test_domains:
        test_domain_in_context(domain, context)
    
    # Interactive mode
    print("\nEnter domains to test (or 'quit' to exit):")
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
                
            test_domain_in_context(domain, context)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
    
    print("\nTest complete")

if __name__ == "__main__":
    main()
