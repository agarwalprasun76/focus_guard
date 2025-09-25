#!/usr/bin/env python3
"""
Test script to verify that ClassifierBlockerAPI returns which classifier was used in classification results.

This script tests the new classify_domain_detailed method to ensure it properly reports
which classifier was used for classification, along with confidence and metadata.
"""

import asyncio
import sys
import os

# Add the focus_guard package to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from focus_guard.core.api.api import ClassifierBlockerAPI


async def test_classifier_name_reporting():
    """Test that classifier names are properly reported in classification results."""
    
    print("Testing Classifier Name Reporting")
    print("=" * 50)
    
    # Initialize the API
    api = ClassifierBlockerAPI()
    
    # Test URLs with different expected classifiers
    test_cases = [
        {
            'url': 'https://www.youtube.com/watch?v=H2bRYtE5l18',
            'domain': 'youtube.com',
            'description': 'YouTube video URL'
        },
        {
            'url': 'https://www.youtube.com/shorts/At3syx84D34',
            'domain': 'youtube.com', 
            'description': 'YouTube Shorts URL'
        },
               {
            'url': 'https://www.youtube.com/watch?v=302eJ3TzJQU&t=41s',
            'domain': 'youtube.com', 
            'description': 'Introduction to Geometry'
        },
               {
            'url': 'https://www.youtube.com/watch?v=MflpyJwhMhQ',
            'domain': 'youtube.com', 
            'description': 'What is algebraic geometry'
        },
        {
            'url': 'https://www.facebook.com',
            'domain': 'facebook.com',
            'description': 'Facebook domain (no URL context)'
        },
        {
            'url': 'https://www.reddit.com/r/programming',
            'domain': 'reddit.com',
            'description': 'Reddit URL'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['description']}")
        print(f"URL: {test_case['url']}")
        print(f"Domain: {test_case['domain']}")
        print("-" * 40)
        
        try:
            # Test the detailed classification method
            result = await api.classify_domain_detailed(test_case['domain'], test_case['url'])
            
            print(f"Classification Result:")
            print(f"  Category: {result.category.name if result.category else 'None'}")
            print(f"  Classifier Used: {result.classifier_name or 'None'}")
            print(f"  Confidence: {result.confidence or 'N/A'}")
            
            if result.metadata:
                print(f"  Metadata Keys: {list(result.metadata.keys())}")
                
                # Show classifier hierarchy for YouTube
                if 'composite_classifier' in result.metadata:
                    print(f"  Composite Classifier: {result.metadata['composite_classifier']}")
                if 'classifier' in result.metadata:
                    print(f"  Specific Classifier: {result.metadata['classifier']}")
                
                # Show some key metadata for YouTube
                if 'title' in result.metadata:
                    title = result.metadata['title']
                    # Handle Unicode encoding for Windows console
                    try:
                        print(f"  Video Title: {title}")
                    except UnicodeEncodeError:
                        print(f"  Video Title: {title.encode('ascii', 'replace').decode('ascii')}")
                
                if 'channel_title' in result.metadata:
                    channel = result.metadata['channel_title']
                    try:
                        print(f"  Channel: {channel}")
                    except UnicodeEncodeError:
                        print(f"  Channel: {channel.encode('ascii', 'replace').decode('ascii')}")
                        
                # Show classification method for YouTube
                if 'method' in result.metadata:
                    print(f"  Classification Method: {result.metadata['method']}")
            else:
                print(f"  Metadata: None")
            
            # Test backward compatibility with original method
            print(f"\nBackward Compatibility Test:")
            category_only = await api.classify_domain(test_case['domain'], test_case['url'])
            print(f"  Original method result: {category_only.name if category_only else 'None'}")
            
            # Verify consistency
            if result.category == category_only:
                print(f"  [OK] Results are consistent")
            else:
                print(f"  [ERROR] Results differ: {result.category} vs {category_only}")
                
        except Exception as e:
            print(f"[ERROR] Error during classification: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n" + "=" * 50)
    print("Classifier Name Reporting Test Complete")


if __name__ == "__main__":
    asyncio.run(test_classifier_name_reporting())
