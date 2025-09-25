"""
Performance validation test for Enhanced Classification Pipeline.
Validates cache hit rates and response times meet Phase 2.2 targets.
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
    print("Performance Validation Test for Enhanced Classification Pipeline")
    print("=" * 65)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create components
        registry = ClassifierRegistry()
        
        # Mock classifier with realistic delay
        class MockClassifier:
            def __init__(self):
                self.name = "mock_classifier"
                
            def classify(self, domain):
                # Simulate realistic classification time (50-200ms)
                time.sleep(0.1)  # 100ms delay
                return Category.PRODUCTIVITY
        
        registry.register(MockClassifier())
        
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
        
        pipeline.add_classifier("mock_classifier")
        
        try:
            # Test 1: Cold start performance (cache misses)
            print("\n1. Cold Start Performance Test")
            print("-" * 35)
            
            test_domains = [
                "example.com", "test.com", "github.com", "stackoverflow.com", 
                "youtube.com", "google.com", "facebook.com", "twitter.com"
            ]
            
            cold_times = []
            for domain_str in test_domains:
                domain = Domain(domain_str)
                start_time = time.time()
                result = await pipeline.classify(domain)
                response_time = time.time() - start_time
                cold_times.append(response_time)
                
                assert result is not None
                print(f"  {domain_str}: {response_time*1000:.1f}ms")
            
            avg_cold_time = statistics.mean(cold_times)
            print(f"\nCold start average: {avg_cold_time*1000:.1f}ms")
            
            # Test 2: Warm cache performance (cache hits)
            print("\n2. Warm Cache Performance Test")
            print("-" * 35)
            
            warm_times = []
            for domain_str in test_domains:
                domain = Domain(domain_str)
                start_time = time.time()
                result = await pipeline.classify(domain)
                response_time = time.time() - start_time
                warm_times.append(response_time)
                
                assert result is not None
                print(f"  {domain_str}: {response_time*1000:.1f}ms")
            
            avg_warm_time = statistics.mean(warm_times)
            print(f"\nWarm cache average: {avg_warm_time*1000:.1f}ms")
            
            # Test 3: Cache hit rate validation
            print("\n3. Cache Hit Rate Analysis")
            print("-" * 30)
            
            stats = pipeline.get_performance_stats()
            cache_hit_rate = stats['cache_hit_rate']
            total_requests = stats['total_requests']
            cache_hits = stats['cache_hits']
            cache_misses = stats['cache_misses']
            
            print(f"  Total requests: {total_requests}")
            print(f"  Cache hits: {cache_hits}")
            print(f"  Cache misses: {cache_misses}")
            print(f"  Cache hit rate: {cache_hit_rate:.1%}")
            
            # Test 4: Load test with mixed domains
            print("\n4. Load Test (Mixed Cache Hits/Misses)")
            print("-" * 42)
            
            load_test_domains = test_domains * 3  # Repeat for cache hits
            load_test_domains.extend([f"new{i}.com" for i in range(5)])  # Add new domains
            
            load_times = []
            load_start = time.time()
            
            for domain_str in load_test_domains:
                domain = Domain(domain_str)
                start_time = time.time()
                result = await pipeline.classify(domain)
                response_time = time.time() - start_time
                load_times.append(response_time)
                
                assert result is not None
            
            load_duration = time.time() - load_start
            avg_load_time = statistics.mean(load_times)
            throughput = len(load_test_domains) / load_duration
            
            print(f"  Processed {len(load_test_domains)} requests in {load_duration:.2f}s")
            print(f"  Average response time: {avg_load_time*1000:.1f}ms")
            print(f"  Throughput: {throughput:.1f} requests/second")
            
            # Test 5: YouTube context performance
            print("\n5. YouTube Context Performance")
            print("-" * 35)
            
            youtube_contexts = [
                {'video_id': 'dQw4w9WgXcQ'},
                {'video_id': 'abc123def'},
                {'channel_id': 'UC123456'},
                {'channel_id': 'UCabcdef'},
            ]
            
            youtube_times = []
            for i, context in enumerate(youtube_contexts):
                domain = Domain("youtube.com")
                start_time = time.time()
                result = await pipeline.classify(domain, context=context)
                response_time = time.time() - start_time
                youtube_times.append(response_time)
                
                assert result is not None
                print(f"  Context {i+1}: {response_time*1000:.1f}ms")
            
            # Repeat for cache hits
            print("  Cache hits:")
            for i, context in enumerate(youtube_contexts):
                domain = Domain("youtube.com")
                start_time = time.time()
                result = await pipeline.classify(domain, context=context)
                response_time = time.time() - start_time
                
                assert result is not None
                print(f"  Context {i+1}: {response_time*1000:.1f}ms")
            
            # Final performance analysis
            print("\n" + "=" * 65)
            print("PERFORMANCE VALIDATION RESULTS")
            print("=" * 65)
            
            final_stats = pipeline.get_performance_stats()
            final_hit_rate = final_stats['cache_hit_rate']
            final_avg_time = final_stats['avg_response_time']
            
            print(f"Overall Cache Hit Rate: {final_hit_rate:.1%}")
            print(f"Overall Average Response Time: {final_avg_time*1000:.1f}ms")
            print(f"Fast Responses (<500ms): {final_stats['fast_responses']}")
            print(f"Slow Responses (>=500ms): {final_stats['slow_responses']}")
            
            # Validate targets
            print("\nTARGET VALIDATION:")
            print("-" * 20)
            
            # Target 1: Cache hit rate > 80% after warmup
            hit_rate_target = 0.8
            hit_rate_pass = final_hit_rate >= hit_rate_target
            print(f"Cache Hit Rate >= {hit_rate_target:.0%}: {'PASS' if hit_rate_pass else 'FAIL'} ({final_hit_rate:.1%})")
            
            # Target 2: Cached responses < 50ms
            cached_time_target = 0.05
            cached_time_pass = avg_warm_time < cached_time_target
            print(f"Cached Response Time < {cached_time_target*1000:.0f}ms: {'PASS' if cached_time_pass else 'FAIL'} ({avg_warm_time*1000:.1f}ms)")
            
            # Target 3: Overall average < 500ms
            overall_time_target = 0.5
            overall_time_pass = final_avg_time < overall_time_target
            print(f"Overall Average Time < {overall_time_target*1000:.0f}ms: {'PASS' if overall_time_pass else 'FAIL'} ({final_avg_time*1000:.1f}ms)")
            
            # Target 4: Throughput > 10 requests/second
            throughput_target = 10
            throughput_pass = throughput >= throughput_target
            print(f"Throughput >= {throughput_target} req/s: {'PASS' if throughput_pass else 'FAIL'} ({throughput:.1f} req/s)")
            
            # Overall result
            all_targets_pass = all([hit_rate_pass, cached_time_pass, overall_time_pass, throughput_pass])
            
            print(f"\nOVERALL RESULT: {'PASS' if all_targets_pass else 'FAIL'}")
            
            if all_targets_pass:
                print("All performance targets met! Phase 2.2 optimization successful.")
            else:
                print("Some performance targets not met. Review optimization strategy.")
                
        finally:
            await pipeline.cache.close()


if __name__ == "__main__":
    asyncio.run(main())
