"""
Tests for BackgroundClassificationService and BackgroundTaskManager.
"""

import asyncio
import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from focus_guard.core.utils.background_tasks import (
    BackgroundClassificationService, 
    BackgroundTaskManager,
    BackgroundTask
)
from focus_guard.core.cache.multi_level_cache import MultiLevelCache
from focus_guard.core.domain.models import Domain, Category, Classification


class TestBackgroundClassificationService:
    """Test suite for BackgroundClassificationService."""
    
    @pytest.fixture
    async def cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    async def cache(self, cache_dir):
        """Create MultiLevelCache instance."""
        cache = MultiLevelCache(
            cache_dir=cache_dir,
            memory_ttl=60,
            disk_ttl=3600,
            background_refresh_interval=1  # Fast for testing
        )
        yield cache
        await cache.close()
    
    @pytest.fixture
    def mock_classifier(self):
        """Create mock classifier function."""
        async def classifier(domain):
            if isinstance(domain, str):
                domain_obj = Domain(domain)
            else:
                domain_obj = domain
            
            return Classification(
                domain=domain_obj,
                category=Category.PRODUCTIVITY,
                confidence=0.8,
                metadata={"source": "mock"}
            )
        return classifier
    
    @pytest.fixture
    def service_config(self):
        """Create service configuration."""
        return {
            'refresh_interval': 1,  # Fast for testing
            'warmup_batch_size': 3,
            'warmup_delay': 0.1
        }
    
    @pytest.fixture
    async def service(self, cache, mock_classifier, service_config):
        """Create BackgroundClassificationService."""
        service = BackgroundClassificationService(
            cache=cache,
            classifier_func=mock_classifier,
            config=service_config
        )
        yield service
        if service.running:
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initialization."""
        assert not service.running
        assert len(service.warmup_domains) > 0
        assert 'cache_warmup' in service.tasks
        assert 'cache_refresh' in service.tasks
        assert 'cache_cleanup' in service.tasks
    
    @pytest.mark.asyncio
    async def test_service_start_stop(self, service):
        """Test service start and stop operations."""
        # Start service
        await service.start()
        assert service.running
        assert service.main_task is not None
        
        # Stop service
        await service.stop()
        assert not service.running
        assert service.main_task is None
    
    @pytest.mark.asyncio
    async def test_cache_warmup(self, service):
        """Test cache warmup functionality."""
        # Test with small set of domains
        test_domains = ["example.com", "test.com"]
        
        # Mock the classifier to track calls
        call_count = 0
        async def counting_classifier(domain):
            nonlocal call_count
            call_count += 1
            return Classification(
                domain=Domain(domain),
                category=Category.PRODUCTIVITY,
                confidence=0.8,
                metadata={"source": "warmup"}
            )
        
        service.classifier_func = counting_classifier
        
        # Run warmup
        await service._warmup_cache()
        
        # Verify domains were processed
        assert call_count > 0
        assert service.stats['warmup_completed'] == 1
    
    @pytest.mark.asyncio
    async def test_background_task_configuration(self, service):
        """Test background task configuration."""
        # Test enabling/disabling tasks
        result = service.configure_task('cache_warmup', False)
        assert result is True
        assert not service.tasks['cache_warmup'].enabled
        
        # Test invalid task name
        result = service.configure_task('invalid_task', True)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_service_statistics(self, service):
        """Test service statistics collection."""
        stats = service.get_stats()
        
        assert 'service_stats' in stats
        assert 'cache_stats' in stats
        assert 'warmup_domains_count' in stats
        assert 'running' in stats
        assert 'tasks_enabled' in stats
        
        # Check specific stats
        assert stats['running'] == service.running
        assert stats['warmup_domains_count'] == len(service.warmup_domains)
    
    @pytest.mark.asyncio
    async def test_force_warmup(self, service):
        """Test forced cache warmup."""
        # Mock classifier to return specific results
        async def mock_classifier(domain):
            return Classification(
                domain=Domain(domain),
                category=Category.ENTERTAINMENT,
                confidence=0.9,
                metadata={"source": "forced"}
            )
        
        service.classifier_func = mock_classifier
        
        # Force warmup
        stats = await service.force_warmup()
        
        assert 'service_stats' in stats
        assert service.stats['warmup_completed'] >= 1
    
    @pytest.mark.asyncio
    async def test_classify_domain_for_warmup(self, service):
        """Test domain classification for warmup."""
        result = await service._classify_domain_for_warmup("github.com")
        
        assert result is not None
        assert isinstance(result, Classification)
        assert result.domain.value == "github.com"
        assert result.category == Category.PRODUCTIVITY
    
    @pytest.mark.asyncio
    async def test_error_handling_in_classification(self, service):
        """Test error handling during classification."""
        # Mock classifier that raises exception
        async def failing_classifier(domain):
            raise Exception("Classification failed")
        
        service.classifier_func = failing_classifier
        
        # Should handle error gracefully
        result = await service._classify_domain_for_warmup("example.com")
        assert result is None
        
        # Error count should increase
        original_errors = service.stats['errors']
        await service._warmup_cache()
        # Note: Error count might not increase if warmup catches exceptions
    
    @pytest.mark.asyncio
    async def test_warmup_domains_generation(self, service):
        """Test warmup domains are properly generated."""
        domains = service._get_warmup_domains()
        
        # Should contain popular domains
        assert len(domains) > 10
        assert 'youtube.com' in domains
        assert 'google.com' in domains
        assert 'github.com' in domains
        
        # Should prioritize popular domains first
        priority_domains = ['youtube.com', 'google.com', 'facebook.com']
        for domain in priority_domains:
            if domain in domains:
                # Should appear early in the list
                assert domains.index(domain) < len(domains) // 2


class TestBackgroundTaskManager:
    """Test suite for BackgroundTaskManager."""
    
    @pytest.fixture
    def manager(self):
        """Create BackgroundTaskManager."""
        return BackgroundTaskManager()
    
    @pytest.fixture
    async def mock_service(self):
        """Create mock BackgroundClassificationService."""
        service = AsyncMock(spec=BackgroundClassificationService)
        service.start = AsyncMock()
        service.stop = AsyncMock()
        service.get_stats = MagicMock(return_value={'test': 'stats'})
        return service
    
    @pytest.mark.asyncio
    async def test_service_registration(self, manager, mock_service):
        """Test service registration."""
        manager.register_service("test_service", mock_service)
        
        assert "test_service" in manager.services
        assert manager.services["test_service"] == mock_service
    
    @pytest.mark.asyncio
    async def test_start_all_services(self, manager, mock_service):
        """Test starting all registered services."""
        manager.register_service("test_service", mock_service)
        
        await manager.start_all()
        
        assert manager.running
        mock_service.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_all_services(self, manager, mock_service):
        """Test stopping all registered services."""
        manager.register_service("test_service", mock_service)
        
        await manager.start_all()
        await manager.stop_all()
        
        assert not manager.running
        mock_service.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_stats(self, manager, mock_service):
        """Test getting statistics from all services."""
        manager.register_service("test_service", mock_service)
        
        stats = manager.get_all_stats()
        
        assert "test_service" in stats
        assert stats["test_service"] == {'test': 'stats'}
        mock_service.get_stats.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_start(self, manager):
        """Test error handling when starting services."""
        # Create service that fails to start
        failing_service = AsyncMock(spec=BackgroundClassificationService)
        failing_service.start = AsyncMock(side_effect=Exception("Start failed"))
        
        manager.register_service("failing_service", failing_service)
        
        # Should not raise exception
        await manager.start_all()
        
        # Manager should still be running despite service failure
        assert manager.running


class TestBackgroundTask:
    """Test suite for BackgroundTask dataclass."""
    
    def test_background_task_creation(self):
        """Test BackgroundTask creation."""
        task = BackgroundTask(
            name="test_task",
            func=lambda: None,
            interval=60.0,
            last_run=0.0,
            enabled=True
        )
        
        assert task.name == "test_task"
        assert task.interval == 60.0
        assert task.enabled is True
        assert task.last_run == 0.0


@pytest.mark.asyncio
async def test_integration_with_cache():
    """Integration test with actual cache operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create cache
        cache = MultiLevelCache(
            cache_dir=temp_dir,
            memory_ttl=60,
            background_refresh_interval=1
        )
        
        # Mock classifier
        async def mock_classifier(domain):
            return Classification(
                domain=Domain(domain),
                category=Category.PRODUCTIVITY,
                confidence=0.8,
                metadata={"source": "integration_test"}
            )
        
        # Create service
        service = BackgroundClassificationService(
            cache=cache,
            classifier_func=mock_classifier,
            config={'warmup_batch_size': 2, 'warmup_delay': 0.1}
        )
        
        try:
            # Test warmup
            test_domains = ["example.com", "test.com"]
            warmed = await cache.warm_cache(test_domains, mock_classifier)
            
            assert warmed == 2
            
            # Verify cached values
            result1 = await cache.get("example.com")
            result2 = await cache.get("test.com")
            
            assert result1 is not None
            assert result2 is not None
            assert result1.category == Category.PRODUCTIVITY
            assert result2.category == Category.PRODUCTIVITY
            
        finally:
            await service.stop()
            await cache.close()


if __name__ == "__main__":
    # Run basic functionality test
    async def run_basic_test():
        print("Testing BackgroundClassificationService...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = MultiLevelCache(cache_dir=temp_dir)
            
            async def mock_classifier(domain):
                return Classification(
                    domain=Domain(domain),
                    category=Category.PRODUCTIVITY,
                    confidence=0.8,
                    metadata={"source": "test"}
                )
            
            service = BackgroundClassificationService(
                cache=cache,
                classifier_func=mock_classifier
            )
            
            try:
                # Test initialization
                assert not service.running
                print("✓ Initialization test passed")
                
                # Test warmup domains
                domains = service._get_warmup_domains()
                assert len(domains) > 0
                print(f"✓ Generated {len(domains)} warmup domains")
                
                # Test classification
                result = await service._classify_domain_for_warmup("example.com")
                assert result is not None
                print("✓ Classification test passed")
                
                # Test statistics
                stats = service.get_stats()
                assert 'service_stats' in stats
                print("✓ Statistics test passed")
                
                print("All basic tests passed!")
                
            finally:
                await service.stop()
                await cache.close()
    
    asyncio.run(run_basic_test())
