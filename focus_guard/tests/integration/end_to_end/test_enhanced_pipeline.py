"""
Test for EnhancedClassificationPipeline functionality.
"""

import asyncio
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock

from focus_guard.core.classification.enhanced_pipeline import EnhancedClassificationPipeline
from focus_guard.core.cache.multi_level_cache import MultiLevelCache
from focus_guard.core.utils.background_tasks import BackgroundClassificationService
from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.classification.base import ClassifierRegistry


async def main():
    print("Testing EnhancedClassificationPipeline...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create cache
        cache = MultiLevelCache(
            cache_dir=temp_dir,
            memory_ttl=60,
            disk_ttl=3600
        )
        
        # Mock classifier registry
        registry = ClassifierRegistry()
        
        # Mock classifier class
        class MockClassifier:
            def __init__(self):
                self.name = "mock_classifier"
                
            def classify(self, domain):
                # Return just the Category, not a full Classification
                return Category.PRODUCTIVITY
        
        # Register the mock classifier
        registry.register(MockClassifier())
        
        # Mock classifier function for background service
        async def mock_classifier_func(domain_input):
            if isinstance(domain_input, str):
                domain_obj = Domain(domain_input)
            else:
                domain_obj = domain_input
            
            return Classification(
                domain=domain_obj,
                category=Category.PRODUCTIVITY,
                confidence=0.8,
                metadata={"source": "background_classifier"}
            )
        
        # Create background service
        background_service = BackgroundClassificationService(
            cache=cache,
            classifier_func=mock_classifier_func
        )
        
        # Create enhanced pipeline
        pipeline = EnhancedClassificationPipeline(
            registry=registry,
            cache_dir=temp_dir,
            config={
                'cache_enabled': True,
                'background_classification': True,
                'performance_monitoring': True
            }
        )
        
        # Add the mock classifier to the pipeline
        pipeline.add_classifier("mock_classifier")
        
        try:
            # Test 1: Basic classification with cache miss
            print("+ Testing basic classification...")
            domain = Domain("example.com")
            
            result = await pipeline.classify(domain)
            assert result is not None
            print(f"  Result: {result}")
            print(f"  Domain: {result.domain.value}")
            print(f"  Category: {result.category}")
            print(f"  Expected: {Category.PRODUCTIVITY}")
            assert result.domain.value == "example.com"
            assert result.category == Category.PRODUCTIVITY
            print("+ Basic classification test passed")
            
            # Test 2: Cache hit (should be faster)
            print("+ Testing cache hit...")
            start_time = time.time()
            result2 = await pipeline.classify(domain)
            cache_time = time.time() - start_time
            
            assert result2 is not None
            assert result2.domain.value == "example.com"
            assert cache_time < 0.1  # Should be very fast from cache
            print(f"+ Cache hit test passed (took {cache_time:.4f}s)")
            
            # Test 3: YouTube context handling
            print("+ Testing YouTube context...")
            youtube_domain = Domain("youtube.com")
            context = {
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'video_id': 'dQw4w9WgXcQ',
                'title': 'Test Video'
            }
            
            result3 = await pipeline.classify(youtube_domain, context=context)
            assert result3 is not None
            print("+ YouTube context test passed")
            
            # Test 4: Performance metrics
            print("+ Testing performance metrics...")
            metrics = pipeline.get_performance_stats()
            assert 'cache_hit_rate' in metrics
            assert 'avg_response_time' in metrics
            assert 'total_requests' in metrics
            assert metrics['total_requests'] >= 3
            print("+ Performance metrics test passed")
            
            # Test 5: Cache key generation
            print("+ Testing cache key generation...")
            
            # Regular domain
            key1 = pipeline._generate_cache_key(Domain("example.com"), None)
            assert key1 == "domain:example.com"
            
            # YouTube with video context
            key2 = pipeline._generate_cache_key(
                Domain("youtube.com"), 
                {'video_id': 'abc123'}
            )
            assert key2 == "youtube_video:abc123"
            
            # YouTube with channel context
            key3 = pipeline._generate_cache_key(
                Domain("youtube.com"), 
                {'channel_id': 'UC123'}
            )
            assert key3 == "youtube_channel:UC123"
            
            print("+ Cache key generation test passed")
            
            # Test 6: Configuration handling
            print("+ Testing configuration...")
            
            # Disable cache
            pipeline.config['cache_enabled'] = False
            result4 = await pipeline.classify(Domain("test.com"))
            assert result4 is not None
            
            # Re-enable cache
            pipeline.config['cache_enabled'] = True
            print("+ Configuration test passed")
            
            print("All EnhancedClassificationPipeline tests passed!")
            
        finally:
            await background_service.stop()
            await cache.close()


if __name__ == "__main__":
    asyncio.run(main())
