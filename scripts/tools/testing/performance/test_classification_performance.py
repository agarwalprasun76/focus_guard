#!/usr/bin/env python3
"""
Test script to measure performance improvements in YouTube classification.

This script tests the performance of the YouTube classifier before and after optimizations.
"""

import asyncio
import sys
import os
import time

# Add the focus_guard package to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from focus_guard.core.api.api import ClassifierBlockerAPI


async def test_performance_improvements():
    """Test performance improvements in YouTube classification."""
    
    print("Testing YouTube Classification Performance")
    print("=" * 50)
    
    # Initialize the API
    api = ClassifierBlockerAPI()
    
    # Test URLs - mix of different types
    test_urls = [
        'https://www.youtube.com/watch?v=H2bRYtE5l18',  # Entertainment
        'https://www.youtube.com/shorts/At3syx84D34',   # Shorts
        'https://www.youtube.com/watch?v=302eJ3TzJQU',  # Educational
        'https://www.youtube.com/watch?v=MflpyJwhMhQ',  # Educational
    ]
    
    print(f"Testing {len(test_urls)} URLs...")
    
    # First run - measure initial performance
    print("\nFirst run (cold cache):")
    start_time = time.time()
    
    for i, url in enumerate(test_urls, 1):
        url_start = time.time()
        
        result = await api.classify_domain_detailed('youtube.com', url)
        
        url_end = time.time()
        url_duration = url_end - url_start
        
        print(f"  URL {i}: {result.classifier_name} -> {result.category.name if result.category else 'None'} ({url_duration:.2f}s)")
    
    first_run_time = time.time() - start_time
    print(f"Total first run time: {first_run_time:.2f}s")
    
    # Second run - should benefit from caching
    print("\nSecond run (warm cache):")
    start_time = time.time()
    
    for i, url in enumerate(test_urls, 1):
        url_start = time.time()
        
        result = await api.classify_domain_detailed('youtube.com', url)
        
        url_end = time.time()
        url_duration = url_end - url_start
        
        print(f"  URL {i}: {result.classifier_name} -> {result.category.name if result.category else 'None'} ({url_duration:.2f}s)")
    
    second_run_time = time.time() - start_time
    print(f"Total second run time: {second_run_time:.2f}s")
    
    # Calculate improvement
    if first_run_time > 0:
        improvement = ((first_run_time - second_run_time) / first_run_time) * 100
        print(f"\nPerformance improvement: {improvement:.1f}%")
        
        if improvement > 50:
            print("[EXCELLENT] Significant performance improvement from caching!")
        elif improvement > 20:
            print("[GOOD] Noticeable performance improvement from caching")
        elif improvement > 0:
            print("[OK] Some performance improvement from caching")
        else:
            print("[INFO] No significant improvement (may indicate cache miss)")
    
    print(f"\n" + "=" * 50)
    print("Performance Test Complete")


if __name__ == "__main__":
    asyncio.run(test_performance_improvements())
