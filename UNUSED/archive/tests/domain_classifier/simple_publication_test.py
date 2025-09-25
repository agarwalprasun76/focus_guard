"""
Simple Test Script for Publication Classifier

This script demonstrates a simplified version of the publication classifier integration
that will work even without all dependencies installed.
"""

import os
import sys
import logging
from urllib.parse import urlparse

# Add the parent directory to the path so we can import from core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import from link_classifier
from core.domain_classifier.classifiers.link_classifier import link_classifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Sample publication URLs to test
TEST_URLS = [
    # Academic papers
    "https://arxiv.org/pdf/2203.02155.pdf",
    "https://www.science.org/doi/10.1126/science.abq7781",
    # Educational content
    "https://web.stanford.edu/class/cs224n/readings/cs224n-2019-notes01-wordvecs1.pdf",
    # Likely distractions
    "https://www.gutenberg.org/files/1342/1342-h/1342-h.htm",  # Pride and Prejudice
    "https://www.goodreads.com/book/show/3.Harry_Potter_and_the_Sorcerer_s_Stone"
]

def is_potential_publication(url):
    """
    Simplified version of the _is_potential_publication method from LinkClassifier
    to demonstrate how publication detection works.
    """
    publication_domains = [
        'arxiv.org', 'researchgate.net', 'academia.edu', 'ssrn.com',
        'sciencedirect.com', 'springer.com', 'ieee.org', 'acm.org',
        'jstor.org', 'wiley.com', 'tandfonline.com', 'nature.com',
        'science.org', 'apa.org', 'pubmed.ncbi.nlm.nih.gov'
    ]
    
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '')
    path = parsed.path.lower()
    
    # Check for known academic domains
    if any(academic_domain in domain for academic_domain in publication_domains):
        return True
        
    # Check for PDF files
    if path.endswith('.pdf'):
        return True
        
    # Check for DOI patterns
    if '/doi/' in path or 'doi.org' in domain:
        return True
        
    # Check for common academic URL patterns
    academic_patterns = [
        '/article/', '/abstract/', '/full/', '/content/',
        '/publication/', '/document/', '/paper/', '/journal/',
        '/proceedings/', '/conference/', '/preprint/', '/pdf/'
    ]
    
    for pattern in academic_patterns:
        if pattern in path:
            return True
            
    return False

def test_url(url):
    """Test a single URL using both methods"""
    print(f"\nTesting URL: {url}")
    
    # First check if it's a potential publication
    is_pub = is_potential_publication(url)
    print(f"Detected as potential publication: {is_pub}")
    
    # Then run through the link classifier
    domain = link_classifier.extract_domain(url)
    result = link_classifier.classify_link(url, domain)
    
    print(f"Classification: {result['classification']}")
    print(f"Confidence: {result['confidence']:.4f}")
    print(f"Reason: {result['reason']}")
    
    if 'metadata' in result and result['metadata'] and result['metadata'].get('publication_label'):
        print(f"Publication Label: {result['metadata']['publication_label']}")
    
    print("-" * 60)
    
def main():
    print("\nPUBLICATION CLASSIFIER SIMPLE TEST\n")
    print("This test demonstrates how the publication classifier works")
    print("even without all dependencies installed.")
    print("-" * 60)
    
    for url in TEST_URLS:
        test_url(url)
    
    print("\nTest complete!")
    print("\nHOW TO USE THE PUBLICATION CLASSIFIER IN YOUR CODE:\n")
    print("""
    # Method 1: Direct usage with Link Classifier
    url = "https://arxiv.org/pdf/2203.02155.pdf"
    domain = link_classifier.extract_domain(url)
    result = link_classifier.classify_link(url, domain)
    
    if result['classification'] == 'useful':
        print(f"The URL is a useful publication")
    elif result['classification'] == 'distraction':
        print(f"The URL is a distracting publication")
    else:
        print(f"The URL is neutral or couldn't be classified")
    
    # Method 2: For more direct access to publication details
    if PUBLICATION_CLASSIFIER_AVAILABLE:  # Check if import was successful
        import asyncio
        
        async def check_publication(url):
            result = await publication_classifier.classify_url(url)
            print(f"Publication category: {result.label}")
            print(f"Decision: {result.decision}")
        
        # Run the async function
        asyncio.run(check_publication(url))
    """)

if __name__ == "__main__":
    main()
