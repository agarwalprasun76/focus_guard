"""
Demo Script for Hierarchical Classification System

This script demonstrates the hierarchical classification system by testing
various URLs and showing which classifier handled each one.
"""

import logging
from urllib.parse import urlparse

# Import the initialized classifier from main.py
from core.domain_classifier.main import initialized_classifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Sample URLs to test (covering different classifiers)
TEST_URLS = [
    # Entertainment content
    "https://www.imdb.com/title/tt0111161/",  # Movie (Shawshank Redemption)
    "https://www.netflix.com/title/80192098",  # Series (Money Heist)
    
    # Publications
    "https://arxiv.org/abs/2106.04554",  # Academic paper
    "https://www.sciencedirect.com/science/article/pii/S0004370221000862",  # Journal article
    
    # Google Drive
    "https://docs.google.com/document/d/1abc123def456/edit",  # Google Doc
    "https://drive.google.com/file/d/1abc123def456/view",  # Google Drive file
    
    # YouTube
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # YouTube video
    "https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw",  # YouTube channel
    
    # General URLs (will use keyword classifier)
    "https://www.github.com/tensorflow/tensorflow",  # Code repository (useful)
    "https://stackoverflow.com/questions/tagged/python",  # Programming Q&A (useful)
    "https://www.facebook.com/profile",  # Social media (distraction)
    "https://www.cnn.com/news",  # News (could be neutral)
]

def test_url(url):
    """Test a single URL using the hierarchical classifier."""
    print(f"\n--- Testing URL: {url} ---")
    
    # Extract domain from URL
    domain = urlparse(url).netloc
    
    # Classify the URL
    result = initialized_classifier.classify_link(url, domain)
    
    # Print the result
    print(f"Classification: {result['classification']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Reason: {result['reason']}")
    
    # Print which classifier was used
    classifier_used = result.get("metadata", {}).get("classifier", "Unknown")
    print(f"Classifier Used: {classifier_used}")
    
    # If there were multiple classification attempts, show them
    attempts = result.get("metadata", {}).get("classification_attempts", [])
    if attempts:
        print("\nClassification Attempts:")
        for i, attempt in enumerate(attempts):
            classifier = attempt.get("classifier", "Unknown")
            confidence = attempt.get("confidence", "N/A")
            classification = attempt.get("classification", "N/A")
            error = attempt.get("error", None)
            
            if error:
                print(f"  {i+1}. {classifier} - Error: {error}")
            else:
                print(f"  {i+1}. {classifier} - {classification} (confidence: {confidence:.2f})")
    
    return result

def main():
    """Test all URLs in the list."""
    print("=== Hierarchical Classification System Demo ===")
    
    results = {}
    for url in TEST_URLS:
        result = test_url(url)
        results[url] = result
    
    # Print summary
    print("\n=== Classification Summary ===")
    print(f"Total URLs tested: {len(TEST_URLS)}")
    
    classifications = {}
    classifiers_used = {}
    
    for url, result in results.items():
        classification = result["classification"]
        classifier = result.get("metadata", {}).get("classifier", "Unknown")
        
        if classification not in classifications:
            classifications[classification] = 0
        classifications[classification] += 1
        
        if classifier not in classifiers_used:
            classifiers_used[classifier] = 0
        classifiers_used[classifier] += 1
    
    print("\nClassification Distribution:")
    for classification, count in classifications.items():
        print(f"  {classification}: {count} URLs ({count/len(TEST_URLS)*100:.1f}%)")
    
    print("\nClassifiers Used:")
    for classifier, count in classifiers_used.items():
        print(f"  {classifier}: {count} URLs ({count/len(TEST_URLS)*100:.1f}%)")

if __name__ == "__main__":
    main()
