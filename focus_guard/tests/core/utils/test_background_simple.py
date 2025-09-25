"""
Simple test for BackgroundClassificationService functionality.
"""

import asyncio
import tempfile
from focus_guard.core.utils.background_tasks import BackgroundClassificationService
from focus_guard.core.cache.multi_level_cache import MultiLevelCache
from focus_guard.core.domain.models import Domain, Category, Classification


async def main():
    print("Testing BackgroundClassificationService...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create cache
        cache = MultiLevelCache(cache_dir=temp_dir)
        
        # Mock classifier that handles string input
        async def mock_classifier(domain_input):
            # Handle both string and Domain object inputs
            if isinstance(domain_input, str):
                domain_obj = Domain(domain_input)
            else:
                domain_obj = domain_input
            
            return Classification(
                domain=domain_obj,
                category=Category.PRODUCTIVITY,
                confidence=0.8,
                metadata={"source": "test"}
            )
        
        # Create service
        service = BackgroundClassificationService(
            cache=cache,
            classifier_func=mock_classifier
        )
        
        try:
            # Test initialization
            assert not service.running
            print("+ Initialization test passed")
            
            # Test warmup domains
            domains = service._get_warmup_domains()
            assert len(domains) > 0
            print(f"+ Generated {len(domains)} warmup domains")
            
            # Test classification
            result = await service._classify_domain_for_warmup("example.com")
            assert result is not None
            print("+ Classification test passed")
            
            # Test statistics
            stats = service.get_stats()
            assert 'service_stats' in stats
            print("+ Statistics test passed")
            
            print("All basic tests passed!")
            
        finally:
            await service.stop()
            await cache.close()


if __name__ == "__main__":
    asyncio.run(main())
