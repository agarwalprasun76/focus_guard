#!/usr/bin/env python3
"""
Test script to verify YouTube metadata extraction is working.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the focus_guard package to the path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_youtube_metadata_extraction():
    """Test YouTube metadata extraction with the specific URLs from the issue."""
    
    print("=" * 60)
    print("YOUTUBE METADATA EXTRACTION TEST")
    print("=" * 60)
    
    # Test URLs from the original issue
    test_urls = [
        "https://www.youtube.com/watch?v=m_C4uC-kWA4",
        "https://www.youtube.com/shorts/At3syx84D34"
    ]
    
    try:
        # Test 1: Direct metadata fetcher
        print("\n1. Testing MetadataFetcher directly:")
        print("-" * 40)
        
        from focus_guard.core.utils.metadata_fetcher import metadata_fetcher
        from focus_guard.core.utils.youtube_utils import extract_youtube_id
        
        for url in test_urls:
            print(f"\nTesting URL: {url}")
            
            # Extract video ID
            video_id = extract_youtube_id(url)
            print(f"  Video ID: {video_id}")
            
            if video_id:
                # Fetch metadata
                metadata = metadata_fetcher.fetch_metadata_for_youtube(video_id)
                
                if metadata and 'error' not in metadata:
                    print(f"  [SUCCESS] - Metadata extracted:")
                    print(f"    Title: {metadata.get('title', 'N/A')}")
                    print(f"    Channel: {metadata.get('channel_title', 'N/A')}")
                    print(f"    Duration: {metadata.get('duration', 'N/A')} seconds")
                    print(f"    View Count: {metadata.get('view_count', 'N/A')}")
                    print(f"    Tags: {len(metadata.get('tags', []))} tags")
                    if metadata.get('description'):
                        desc_preview = metadata['description'][:100] + "..." if len(metadata['description']) > 100 else metadata['description']
                        print(f"    Description: {desc_preview}")
                else:
                    print(f"  [FAILED] - Error: {metadata.get('error', 'Unknown error')}")
            else:
                print(f"  [FAILED] - Could not extract video ID")
        
        # Test 2: API integration
        print("\n\n2. Testing ClassifierBlockerAPI integration:")
        print("-" * 40)
        
        from focus_guard.core.api.api import ClassifierBlockerAPI
        from focus_guard.core.domain.domain_utils_new import extract_domain_from_url
        
        api = ClassifierBlockerAPI()
        
        for url in test_urls:
            print(f"\nTesting URL: {url}")
            
            domain = extract_domain_from_url(url)
            print(f"  Domain: {domain}")
            
            # Test classification with URL context
            category = await api.classify_domain(domain, url)
            
            if category:
                print(f"  [SUCCESS] Classification: {category.name}")
            else:
                print(f"  [WARNING] No classification returned")
        
        # Test 3: Full blocking pipeline
        print("\n\n3. Testing full blocking pipeline:")
        print("-" * 40)
        
        for url in test_urls:
            print(f"\nTesting URL: {url}")
            
            # Use combined method to avoid duplicate calls
            blocking_result = await api.check_blocking_with_details(url)
            
            status = "BLOCKED" if blocking_result.should_block else "ALLOWED"
            print(f"  Decision: {status}")
            print(f"  Reason: {blocking_result.reason or 'No blocking rules matched'}")
            if blocking_result.category:
                print(f"  Category: {blocking_result.category.name}")
            if blocking_result.classifier_name:
                print(f"  Classified by: {blocking_result.classifier_name}")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_youtube_metadata_extraction())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
