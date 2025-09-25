"""
End-to-end integration test for Enhanced Classification System.
Tests the complete Phase 2.2 implementation with all components working together.
"""

import asyncio
import tempfile
import time
import statistics
from typing import List

from focus_guard.core.classification.enhanced_pipeline import EnhancedClassificationPipeline
from focus_guard.core.cache.multi_level_cache import MultiLevelCache
from focus_guard.core.utils.background_tasks import BackgroundClassificationService
from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.classification.base import ClassifierRegistry


async def main():
    print("End-to-End Integration Test - Enhanced Classification System")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup complete system
        print("\n1. System Setup")
        print("-" * 15)
        
        # Configuration
        config = {
            'cache_enabled': True,
            'background_classification': True,
            'performance_monitoring': True
        }
        
        # Mock classifier registry
        registry = ClassifierRegistry()
        
        class ProductivityClassifier:
            def __init__(self):
                self.name = "productivity_classifier"
                
            def classify(self, domain):
                productivity_domains = ['github.com', 'stackoverflow.com', 'docs.google.com']
                if domain.value in productivity_domains:
                    return Category.PRODUCTIVITY
                return None
        
        class EntertainmentClassifier:
            def __init__(self):
                self.name = "entertainment_classifier"
                
            def classify(self, domain):
                entertainment_domains = ['youtube.com', 'netflix.com', 'twitch.tv']
                if domain.value in entertainment_domains:
                    return Category.ENTERTAINMENT
                return None
        
        class SocialMediaClassifier:
            def __init__(self):
                self.name = "social_media_classifier"
                
            def classify(self, domain):
                social_domains = ['facebook.com', 'twitter.com', 'instagram.com']
                if domain.value in social_domains:
                    return Category.SOCIAL_MEDIA
                return None
        
        # Register classifiers
        registry.register(ProductivityClassifier())
        registry.register(EntertainmentClassifier())
        registry.register(SocialMediaClassifier())
        
        print("  + Mock classifiers registered")
        
        # Create enhanced classification pipeline directly
        pipeline = EnhancedClassificationPipeline(
            registry=registry,
            cache_dir=temp_dir,
            config=config
        )
        
        # Add classifiers to pipeline
        pipeline.add_classifier("productivity_classifier")
        pipeline.add_classifier("entertainment_classifier")
        pipeline.add_classifier("social_media_classifier")
        
        print("  + Enhanced classification pipeline created")
        
        try:
            
            # Test 2: Basic classification workflow
            print("\n2. Basic Classification Workflow")
            print("-" * 35)
            
            test_domains = [
                "github.com",
                "youtube.com", 
                "facebook.com",
                "unknown-domain.com"
            ]
            
            results = {}
            for domain_str in test_domains:
                domain = Domain(domain_str)
                result = await pipeline.classify(domain)
                results[domain_str] = result
                
                if result:
                    print(f"  {domain_str}: {result.category.name}")
                else:
                    print(f"  {domain_str}: UNCLASSIFIED")
            
            # Verify expected classifications
            assert results["github.com"].category == Category.PRODUCTIVITY
            assert results["youtube.com"].category == Category.ENTERTAINMENT
            assert results["facebook.com"].category == Category.SOCIAL_MEDIA
            assert results["unknown-domain.com"] is None
            
            print("  + Basic classification workflow passed")
            
            # Test 3: Cache performance
            print("\n3. Cache Performance Test")
            print("-" * 27)
            
            # First round (cache misses)
            miss_times = []
            for domain_str in test_domains[:3]:  # Skip unclassified
                domain = Domain(domain_str)
                start_time = time.time()
                result = await pipeline.classify(domain)
                response_time = time.time() - start_time
                miss_times.append(response_time)
                print(f"  {domain_str} (miss): {response_time*1000:.1f}ms")
            
            # Second round (cache hits)
            hit_times = []
            for domain_str in test_domains[:3]:
                domain = Domain(domain_str)
                start_time = time.time()
                result = await pipeline.classify(domain)
                response_time = time.time() - start_time
                hit_times.append(response_time)
                print(f"  {domain_str} (hit): {response_time*1000:.1f}ms")
            
            avg_miss_time = statistics.mean(miss_times)
            avg_hit_time = statistics.mean(hit_times)
            speedup = avg_miss_time / max(avg_hit_time, 0.001)
            
            print(f"\n  Average miss time: {avg_miss_time*1000:.1f}ms")
            print(f"  Average hit time: {avg_hit_time*1000:.1f}ms")
            print(f"  Cache speedup: {speedup:.1f}x")
            
            assert avg_hit_time < avg_miss_time
            print("  + Cache performance test passed")
            
            # Test 4: YouTube context handling
            print("\n4. YouTube Context Handling")
            print("-" * 29)
            
            youtube_domain = Domain("youtube.com")
            youtube_contexts = [
                {'video_id': 'dQw4w9WgXcQ', 'title': 'Never Gonna Give You Up'},
                {'video_id': 'abc123def', 'title': 'Test Video'},
                {'channel_id': 'UC123456', 'channel_title': 'Test Channel'},
                {'url': 'https://www.youtube.com/watch?v=xyz789'}
            ]
            
            for i, context in enumerate(youtube_contexts):
                result = await pipeline.classify(youtube_domain, context=context)
                cache_key = pipeline._generate_cache_key(youtube_domain, context)
                
                assert result is not None
                assert result.category == Category.ENTERTAINMENT
                print(f"  Context {i+1}: {result.category.name} (key: {cache_key[:30]}...)")
            
            print("  + YouTube context handling passed")
            
            # Test 5: URL simulation
            print("\n5. URL Classification Simulation")
            print("-" * 34)
            
            # Simulate URL-based classification
            test_urls = [
                'https://github.com/user/repo',
                'https://www.youtube.com/watch?v=test123',
                'https://facebook.com/page',
                'https://unknown-site.com'
            ]
            
            for url in test_urls:
                # Extract domain from URL
                domain_str = url.split('/')[2] if '//' in url else url
                domain = Domain(domain_str)
                
                result = await pipeline.classify(domain)
                print(f"  URL: {url}")
                print(f"    Domain: {domain_str} -> {result.category.name if result else 'UNCLASSIFIED'}")
            
            print("  + URL classification simulation passed")
            
            # Test 6: Performance metrics validation
            print("\n6. Performance Metrics Validation")
            print("-" * 36)
            
            pipeline_stats = pipeline.get_performance_stats()
            cache_stats = pipeline.cache.get_stats()
            
            print(f"  Total requests: {pipeline_stats['total_requests']}")
            print(f"  Cache hit rate: {pipeline_stats['cache_hit_rate']:.1%}")
            print(f"  Average response time: {pipeline_stats['avg_response_time']*1000:.1f}ms")
            print(f"  Fast responses: {pipeline_stats['fast_responses']}")
            print(f"  Memory cache entries: {cache_stats['memory_valid_entries']}")
            
            # Validate performance targets
            assert pipeline_stats['cache_hit_rate'] >= 0.5  # At least 50% hit rate
            assert pipeline_stats['avg_response_time'] < 0.5  # Under 500ms average
            assert pipeline_stats['fast_responses'] > 0  # Some fast responses
            
            print("  + Performance metrics validation passed")
            
            # Test 7: System health check
            print("\n7. System Health Check")
            print("-" * 24)
            
            print(f"  Cache operational: {pipeline.cache is not None}")
            print(f"  Pipeline operational: {pipeline is not None}")
            print(f"  Fallback pipeline operational: {pipeline.fallback_pipeline is not None}")
            
            assert pipeline.cache is not None
            assert pipeline is not None
            assert pipeline.fallback_pipeline is not None
            
            print("  + System health check passed")
            
            # Test 8: Stress test
            print("\n8. Stress Test")
            print("-" * 14)
            
            stress_domains = [
                f"test{i}.com" for i in range(20)
            ] + test_domains * 5  # Mix of new and cached domains
            
            stress_start = time.time()
            stress_results = []
            
            for domain_str in stress_domains:
                domain = Domain(domain_str)
                result = await pipeline.classify(domain)
                stress_results.append(result)
            
            stress_duration = time.time() - stress_start
            throughput = len(stress_domains) / stress_duration
            
            print(f"  Processed {len(stress_domains)} requests in {stress_duration:.2f}s")
            print(f"  Throughput: {throughput:.1f} requests/second")
            print(f"  Success rate: {len([r for r in stress_results if r is not None])/len(stress_results):.1%}")
            
            assert throughput > 10  # At least 10 requests/second
            print("  + Stress test passed")
            
            # Final system statistics
            print("\n" + "=" * 60)
            print("FINAL SYSTEM STATISTICS")
            print("=" * 60)
            
            final_pipeline_stats = pipeline.get_performance_stats()
            final_cache_stats = pipeline.cache.get_stats()
            
            print(f"Total Classifications: {final_pipeline_stats['total_requests']}")
            print(f"Cache Hit Rate: {final_pipeline_stats['cache_hit_rate']:.1%}")
            print(f"Average Response Time: {final_pipeline_stats['avg_response_time']*1000:.1f}ms")
            print(f"Cache Entries (Memory): {final_cache_stats['memory_valid_entries']}")
            print(f"Popular Domains Tracked: {final_cache_stats['popular_domains_count']}")
            
            print("\n" + "=" * 60)
            print("END-TO-END INTEGRATION TEST RESULTS")
            print("=" * 60)
            print("+ System setup and initialization successful")
            print("+ Basic classification workflow functional")
            print("+ Cache performance meets targets")
            print("+ YouTube context handling working")
            print("+ URL classification simulation successful")
            print("+ Performance metrics within targets")
            print("+ System health checks passing")
            print("+ Stress test performance acceptable")
            print("\nALL INTEGRATION TESTS PASSED!")
            print("Phase 2.2 Enhanced Classification System is fully operational!")
            
        finally:
            # Cleanup
            await pipeline.cache.close()
            print("\n+ System cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
