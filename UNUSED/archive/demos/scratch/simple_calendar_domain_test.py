"""
Simple Calendar Domain Test
A simplified script to test calendar domain allowance with minimal overhead
"""
import sys
import os
import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from core.domain_classifier.filter_domain import filter_domain

def test_domain_classification(domain):
    """Test domain classification without calendar context"""
    category = filter_domain(domain)
    print(f"Domain: {domain}")
    print(f"Category: {category}")
    return category

def main():
    """Main function for simple domain testing"""
    print("Simple Calendar Domain Test")
    print("--------------------------------")
    
    # Test domains without calendar context
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
        category = test_domain_classification(domain)
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
                
            test_domain_classification(domain)
            print("")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {str(e)}")
    
    print("Test complete")

if __name__ == "__main__":
    main()
