#!/usr/bin/env python3
"""
Test script to debug YouTube classification for geometry video.
"""

import asyncio
import logging
from focus_guard.core.api.api import api
from focus_guard.core.domain.models import Domain

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_youtube_classification():
    """Test YouTube classification for the geometry video."""
    
    # Test URL from user
    test_url = "https://www.youtube.com/watch?v=302eJ3TzJQU"
    domain_str = "youtube.com"
    
    # Test metadata (simulating what browser would provide)
    metadata = {
        'url': test_url,
        'title': 'Geometry Video Title',  # We don't have the actual title
        'timestamp': '2025-08-28T19:42:00',
        'domain': domain_str
    }
    
    print(f"\n=== Testing YouTube Classification ===")
    print(f"URL: {test_url}")
    print(f"Domain: {domain_str}")
    print(f"Metadata: {metadata}")
    print("=" * 50)
    
    # Test classification with context
    try:
        category = await api.classify_domain_with_context(domain_str, metadata)
        print(f"\nClassification Result: {category}")
        
        # Test blocking decision
        should_block = await api.should_block_tab(test_url, metadata)
        print(f"Should Block: {should_block}")
        
    except Exception as e:
        print(f"Error during classification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_youtube_classification())
