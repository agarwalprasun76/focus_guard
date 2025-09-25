"""
Lightweight Calendar Domain Test
A minimal script to test calendar domain allowance without memory issues
"""
import sys
import os
import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from core.calendar.calendar_integration import GoogleCalendarClient
from core.domain_classifier.filter_domain import filter_domain

def safe_print(msg):
    """Print safely, handling encoding issues."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode())

def test_domain_classification(domain):
    """Test domain classification without calendar context"""
    category = filter_domain(domain)
    safe_print(f"Domain: {domain}")
    safe_print(f"Category: {category}")
    return category

def main():
    """Main function for lightweight domain testing"""
    safe_print("Lightweight Calendar Domain Test")
    safe_print("--------------------------------")
    
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
    
    safe_print("\nTesting domain classification:")
    for domain in test_domains:
        category = test_domain_classification(domain)
        safe_print(f"Result: {domain} -> {category}\n")
    
    # Interactive mode
    safe_print("\nEnter domains to test (or 'quit' to exit):")
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
            safe_print("")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            safe_print(f"Error: {str(e)}")
    
    safe_print("Test complete")

if __name__ == "__main__":
    main()
