"""
Minimal Domain Test
An extremely minimal script that doesn't import any potentially problematic modules
"""

# Domain categories for testing
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

def main():
    """Main function for minimal domain testing"""
    print("Minimal Domain Classification Test")
    print("--------------------------------")
    
    # Test domains
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
    
    print("\nTesting domain classification:")
    for domain in test_domains:
        category = classify_domain(domain)
        print(f"Domain: {domain}")
        print(f"Category: {category}")
        print(f"Result: {domain} -> {category}\n")
    
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
                
            category = classify_domain(domain)
            print(f"Domain: {domain}")
            print(f"Category: {category}")
            print("")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
    
    print("Test complete")

if __name__ == "__main__":
    main()
