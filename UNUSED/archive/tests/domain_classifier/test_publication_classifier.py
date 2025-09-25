"""
Test Script for Publication Classifier

This script demonstrates how to use the publication classifier to categorize URLs
and provides examples with various types of publications.
"""

import os
import sys
import asyncio
import logging
from pprint import pprint

# Add the parent directory to the path so we can import from core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the publication classifier and link classifier (updated paths)
from core.domain_classifier.classifiers.publication_classifier import publication_classifier
from core.domain_classifier.classifiers.link_classifier import link_classifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test URLs - a mix of different types of publications and non-publications
TEST_URLS = {
    "Scientific Papers": [
        "https://arxiv.org/pdf/2203.02155.pdf",  # AI research paper
        "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7745045/",  # Medical research
        "https://www.science.org/doi/10.1126/science.abq7781",  # Science journal
    ],
    "Educational Content": [
        "https://web.stanford.edu/class/cs224n/readings/cs224n-2019-notes01-wordvecs1.pdf",  # Course notes
        "https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-fall-2010/resources/mit6_042jf10_chap01/",  # MIT OCW
    ],
    "Technical Documentation": [
        "https://docs.python.org/3/tutorial/index.html",  # Python docs
        "https://reactjs.org/docs/getting-started.html",  # React docs
    ],
    "Books": [
        "https://www.gutenberg.org/files/1342/1342-h/1342-h.htm",  # Pride and Prejudice
        "https://www.gutenberg.org/files/84/84-h/84-h.htm",  # Frankenstein
    ],
    "News Articles": [
        "https://www.nytimes.com/section/science",  # Science news
        "https://www.wired.com/category/science/",  # Tech/science news
    ],
    "Entertainment": [
        "https://www.goodreads.com/book/show/3.Harry_Potter_and_the_Sorcerer_s_Stone",  # Harry Potter
        "https://www.imdb.com/title/tt0241527/",  # Harry Potter movie
    ]
}

async def test_single_url(url):
    """Test a single URL with the publication classifier"""
    logger.info(f"Testing URL: {url}")
    
    # Use the publication classifier directly
    result = await publication_classifier.classify_url(url)
    
    # Print the detailed results
    print("\n--- Publication Classifier Direct Result ---")
    print(f"URL: {url}")
    print(f"Content Type: {result.content_type}")
    print(f"Label: {result.label}")
    print(f"Score: {result.score:.4f}")
    print(f"Decision: {result.decision}")
    print(f"Reason: {result.reason}")
    
    # Also demonstrate how to use it through the link_classifier
    domain = link_classifier.extract_domain(url)
    focus_guard_result = link_classifier.classify_link(url, domain)
    
    # Print the focus_guard classification
    print("\n--- Focus Guard Integration Result ---")
    print(f"Classification: {focus_guard_result['classification']}")
    print(f"Confidence: {focus_guard_result['confidence']:.4f}")
    print(f"Reason: {focus_guard_result['reason']}")
    if 'metadata' in focus_guard_result and focus_guard_result['metadata']:
        print("\nMetadata:")
        # Print first few items of metadata to keep output manageable
        for key, value in list(focus_guard_result['metadata'].items())[:3]:
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
    
    print("\n" + "-"*50)
    return result

async def test_category(category, urls):
    """Test a category of URLs"""
    print(f"\n\n===== Testing {category} =====")
    for url in urls:
        await test_single_url(url)

async def main():
    """Main test function"""
    print("PUBLICATION CLASSIFIER TEST\n")
    
    # Check if a specific URL was provided as a command-line argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
        await test_single_url(url)
    else:
        # Test each category
        for category, urls in TEST_URLS.items():
            await test_category(category, urls)
    
    print("\nTest completed!")

def example_usage():
    """Example of how to use the publication classifier in your code"""
    # This is just a code example, not executed
    print("\nEXAMPLE USAGE IN CODE:")
    print("""
    # Direct async usage
    async def classify_publication(url):
        result = await publication_classifier.classify_url(url)
        if result.decision == "allow":
            print(f"{url} is a useful publication about {result.label}")
        elif result.decision == "block":
            print(f"{url} is a distracting publication about {result.label}")
        else:
            print(f"{url} is neutral or couldn't be classified")
    
    # Usage through the link_classifier
    def check_url(url):
        domain = link_classifier.extract_domain(url)
        result = link_classifier.classify_link(url, domain)
        
        if result['classification'] == 'useful':
            print(f"{url} is classified as useful")
        elif result['classification'] == 'distraction':
            print(f"{url} is classified as a distraction")
        else:
            print(f"{url} is neutral")
    """)

if __name__ == "__main__":
    # Show example code usage
    example_usage()
    
    # Run the async tests
    asyncio.run(main())
