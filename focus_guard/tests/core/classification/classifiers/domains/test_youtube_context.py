"""
Test YouTube-specific cache key generation and context handling.
"""

import asyncio
import tempfile
from focus_guard.core.classification.enhanced_pipeline import EnhancedClassificationPipeline
from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.classification.base import ClassifierRegistry


async def main():
    print("Testing YouTube-Specific Cache Key Generation")
    print("=" * 45)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup
        registry = ClassifierRegistry()
        
        class MockClassifier:
            def __init__(self):
                self.name = "mock_classifier"
                
            def classify(self, domain):
                return Category.ENTERTAINMENT
        
        registry.register(MockClassifier())
        
        pipeline = EnhancedClassificationPipeline(
            registry=registry,
            cache_dir=temp_dir,
            config={'cache_enabled': True}
        )
        
        pipeline.add_classifier("mock_classifier")
        
        try:
            # Test 1: Basic YouTube domain without context
            print("\n1. Basic YouTube Domain (No Context)")
            print("-" * 40)
            
            youtube_domain = Domain("youtube.com")
            key1 = pipeline._generate_cache_key(youtube_domain, None)
            print(f"  Key: {key1}")
            assert key1 == "domain:youtube.com"
            print("  + Basic domain key generation passed")
            
            # Test 2: YouTube with video ID context
            print("\n2. YouTube Video Context")
            print("-" * 27)
            
            video_contexts = [
                {'video_id': 'dQw4w9WgXcQ'},
                {'video_id': 'abc123def456'},
                {'video_id': 'XYZ789'},
            ]
            
            for i, context in enumerate(video_contexts):
                key = pipeline._generate_cache_key(youtube_domain, context)
                expected = f"youtube_video:{context['video_id']}"
                print(f"  Context {i+1}: {context['video_id']}")
                print(f"    Key: {key}")
                print(f"    Expected: {expected}")
                assert key == expected
                print(f"    + Video context {i+1} passed")
            
            # Test 3: YouTube with channel ID context
            print("\n3. YouTube Channel ID Context")
            print("-" * 32)
            
            channel_contexts = [
                {'channel_id': 'UC123456789'},
                {'channel_id': 'UCabcdefghij'},
                {'channel_id': 'UC_TestChannel'},
            ]
            
            for i, context in enumerate(channel_contexts):
                key = pipeline._generate_cache_key(youtube_domain, context)
                expected = f"youtube_channel:{context['channel_id']}"
                print(f"  Context {i+1}: {context['channel_id']}")
                print(f"    Key: {key}")
                print(f"    Expected: {expected}")
                assert key == expected
                print(f"    + Channel ID context {i+1} passed")
            
            # Test 4: YouTube with channel title context
            print("\n4. YouTube Channel Title Context")
            print("-" * 35)
            
            channel_title_contexts = [
                {'channel_title': 'Tech Reviews'},
                {'channel_title': 'Gaming Channel'},
                {'channel_title': 'Educational Content'},
            ]
            
            for i, context in enumerate(channel_title_contexts):
                key = pipeline._generate_cache_key(youtube_domain, context)
                print(f"  Context {i+1}: {context['channel_title']}")
                print(f"    Key: {key}")
                assert key.startswith("youtube_channel_title:")
                print(f"    + Channel title context {i+1} passed")
            
            # Test 5: YouTube with URL context
            print("\n5. YouTube URL Context")
            print("-" * 23)
            
            url_contexts = [
                {'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'},
                {'url': 'https://www.youtube.com/channel/UC123456789'},
                {'url': 'https://www.youtube.com/user/testuser'},
            ]
            
            for i, context in enumerate(url_contexts):
                key = pipeline._generate_cache_key(youtube_domain, context)
                print(f"  Context {i+1}: {context['url']}")
                print(f"    Key: {key}")
                assert key.startswith("url_context:")
                print(f"    + URL context {i+1} passed")
            
            # Test 6: YouTube.be short URLs
            print("\n6. YouTube.be Short URLs")
            print("-" * 27)
            
            youtu_be_domain = Domain("youtu.be")
            
            short_url_contexts = [
                {'video_id': 'dQw4w9WgXcQ'},
                {'url': 'https://youtu.be/dQw4w9WgXcQ'},
            ]
            
            for i, context in enumerate(short_url_contexts):
                key = pipeline._generate_cache_key(youtu_be_domain, context)
                print(f"  Context {i+1}: {context}")
                print(f"    Key: {key}")
                if 'video_id' in context:
                    assert key == f"youtube_video:{context['video_id']}"
                else:
                    assert key.startswith("url_context:")
                print(f"    + Short URL context {i+1} passed")
            
            # Test 7: Classification with different contexts
            print("\n7. Classification with Context Caching")
            print("-" * 40)
            
            # Classify same video with different contexts
            video_id = "test_video_123"
            contexts = [
                {'video_id': video_id, 'title': 'Test Video 1'},
                {'video_id': video_id, 'title': 'Test Video 2'},  # Same video, different title
                {'video_id': video_id, 'channel_id': 'UC123'},    # Same video, with channel
            ]
            
            results = []
            for i, context in enumerate(contexts):
                result = await pipeline.classify(youtube_domain, context=context)
                results.append(result)
                print(f"  Classification {i+1}: {result.category.name}")
                assert result is not None
                assert result.category == Category.ENTERTAINMENT
            
            # All should be the same since they have the same video_id
            for i in range(1, len(results)):
                assert results[i] == results[0]
            print("  + Same video ID produces consistent results")
            
            # Test 8: Performance with context caching
            print("\n8. Performance with Context Caching")
            print("-" * 37)
            
            import time
            
            # First classification (cache miss)
            start_time = time.time()
            result1 = await pipeline.classify(
                youtube_domain, 
                context={'video_id': 'performance_test'}
            )
            first_time = time.time() - start_time
            
            # Second classification (cache hit)
            start_time = time.time()
            result2 = await pipeline.classify(
                youtube_domain, 
                context={'video_id': 'performance_test'}
            )
            second_time = time.time() - start_time
            
            print(f"  First call (cache miss): {first_time*1000:.1f}ms")
            print(f"  Second call (cache hit): {second_time*1000:.1f}ms")
            print(f"  Speedup: {first_time/max(second_time, 0.001):.1f}x")
            
            assert result1 == result2
            assert second_time < first_time  # Cache hit should be faster
            print("  + Context caching improves performance")
            
            # Test 9: Mixed context types
            print("\n9. Mixed Context Types")
            print("-" * 24)
            
            mixed_contexts = [
                {'video_id': 'abc123', 'channel_id': 'UC456'},  # Video ID takes precedence
                {'channel_id': 'UC789', 'channel_title': 'Test'},  # Channel ID takes precedence
                {'url': 'https://youtube.com/watch?v=xyz', 'title': 'Video'},  # URL context
            ]
            
            for i, context in enumerate(mixed_contexts):
                key = pipeline._generate_cache_key(youtube_domain, context)
                print(f"  Mixed context {i+1}: {context}")
                print(f"    Key: {key}")
                
                if 'video_id' in context:
                    assert key.startswith("youtube_video:")
                elif 'channel_id' in context:
                    assert key.startswith("youtube_channel:")
                else:
                    assert key.startswith("url_context:")
                
                print(f"    + Mixed context {i+1} passed")
            
            # Test 10: Cache statistics
            print("\n10. Cache Statistics")
            print("-" * 20)
            
            stats = pipeline.get_performance_stats()
            print(f"  Total requests: {stats['total_requests']}")
            print(f"  Cache hits: {stats['cache_hits']}")
            print(f"  Cache misses: {stats['cache_misses']}")
            print(f"  Hit rate: {stats['cache_hit_rate']:.1%}")
            
            assert stats['total_requests'] > 0
            assert stats['cache_hits'] > 0
            print("  + Cache statistics tracked correctly")
            
            print("\n" + "=" * 45)
            print("YOUTUBE CONTEXT TEST RESULTS")
            print("=" * 45)
            print("+ Basic domain key generation works")
            print("+ Video ID context creates specific keys")
            print("+ Channel ID context creates specific keys")
            print("+ Channel title context creates hashed keys")
            print("+ URL context creates hashed keys")
            print("+ YouTube.be short URLs handled correctly")
            print("+ Context caching improves performance")
            print("+ Mixed context types prioritized correctly")
            print("+ Cache statistics tracked accurately")
            print("\nALL YOUTUBE CONTEXT TESTS PASSED!")
            
        finally:
            await pipeline.cache.close()


if __name__ == "__main__":
    asyncio.run(main())
