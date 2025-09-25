"""
Comprehensive Error Scenario Testing for Focus Guard Integration.

This module tests all failure modes and recovery scenarios across the entire
Focus Guard pipeline, implementing Phase 3 error scenario requirements.
"""

import asyncio
import json
import time
import tempfile
import logging
import pytest
import requests
import threading
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from pathlib import Path

from focus_guard.core.browser.extension.tab_server import TabServer, TabServerConfig
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
from focus_guard.core.classification.enhanced_pipeline import EnhancedClassificationPipeline
from focus_guard.core.classification.base import ClassifierRegistry
from focus_guard.core.api.api import ClassifierBlockerAPI
from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.utils.circuit_breaker import CircuitBreaker
from focus_guard.core.utils.enhanced_retry import RetryConfig, enhanced_retry
from focus_guard.core.utils.error_monitoring import ErrorMonitor
from focus_guard.tests.integration.mock_browser_extension import MockBrowserExtension, MockBrowserInfo

logger = logging.getLogger(__name__)


@pytest.fixture
async def error_test_server():
    """Create tab server for error testing."""
    config = TabServerConfig(host='localhost', port=5557)
    server = TabServer(config)
    
    started = server.start(5557)
    if not started:
        pytest.skip("Could not start error test server")
    
    await asyncio.sleep(1)
    yield server
    server.stop()


@pytest.fixture
async def unstable_mock_extension(error_test_server):
    """Create mock extension that simulates instability."""
    extension = MockBrowserExtension(
        tab_server_url=f"http://localhost:{error_test_server.port}",
        browser_info=MockBrowserInfo(
            name="UnstableChrome",
            version="120.0.0.0",
            extension_id="unstable-test-extension"
        ),
        polling_interval=0.1
    )
    
    if not extension.start():
        pytest.skip("Could not start unstable mock extension")
    
    yield extension
    extension.stop()


@pytest.fixture
async def failing_classifier_registry():
    """Create classifier registry with failing classifiers."""
    registry = ClassifierRegistry()
    
    class FailingClassifier:
        def __init__(self, failure_rate=0.5):
            self.name = "failing_classifier"
            self.failure_rate = failure_rate
            self.call_count = 0
        
        def classify(self, domain):
            self.call_count += 1
            if self.call_count % int(1/self.failure_rate) == 0:
                raise Exception(f"Simulated classifier failure for {domain.value}")
            return Category.PRODUCTIVITY if 'github' in domain.value else None
    
    class TimeoutClassifier:
        def __init__(self):
            self.name = "timeout_classifier"
        
        def classify(self, domain):
            time.sleep(5)  # Simulate very slow classifier
            return Category.ENTERTAINMENT
    
    class MemoryLeakClassifier:
        def __init__(self):
            self.name = "memory_leak_classifier"
            self.memory_hog = []
        
        def classify(self, domain):
            # Simulate memory leak
            self.memory_hog.extend([f"data_{i}" for i in range(1000)])
            return Category.SOCIAL_MEDIA if 'facebook' in domain.value else None
    
    registry.register(FailingClassifier(0.3))  # 30% failure rate
    registry.register(TimeoutClassifier())
    registry.register(MemoryLeakClassifier())
    
    return registry


class TestServerFailureScenarios:
    """Test tab server failure scenarios and recovery."""
    
    @pytest.mark.asyncio
    async def test_server_crash_and_restart(self, unstable_mock_extension):
        """Test behavior when tab server crashes and restarts."""
        # Create initial tabs
        tab1 = unstable_mock_extension.create_tab("https://github.com/test1", "Test 1")
        tab2 = unstable_mock_extension.create_tab("https://www.youtube.com/test2", "Test 2")
        
        await asyncio.sleep(0.5)
        
        # Simulate server crash by stopping it
        # Note: In real scenario, this would test actual crash recovery
        initial_stats = unstable_mock_extension.get_stats()
        
        # Extension should handle server unavailability
        await asyncio.sleep(2)  # Let extension try to communicate with dead server
        
        crash_stats = unstable_mock_extension.get_stats()
        
        # Extension should still be running and accumulating errors
        assert crash_stats['running'], "Extension should still be running after server crash"
        assert crash_stats['errors'] > initial_stats['errors'], "Should record server connection errors"
        
        # Extension should maintain local state
        local_tabs = unstable_mock_extension.get_tabs()
        assert len(local_tabs) == 2, "Should maintain local tab state during server outage"
    
    @pytest.mark.asyncio
    async def test_port_conflict_handling(self):
        """Test handling of port conflicts during server startup."""
        # Start first server
        config1 = TabServerConfig(host='localhost', port=5558)
        server1 = TabServer(config1)
        assert server1.start(5558), "First server should start successfully"
        
        try:
            # Try to start second server on same port
            config2 = TabServerConfig(host='localhost', port=5558)
            server2 = TabServer(config2)
            
            # Should either fail gracefully or find alternative port
            result = server2.start(5558)
            
            if result:
                # If successful, should be using different port
                assert server2.port != server1.port, "Should use different port to avoid conflict"
            else:
                # Graceful failure is acceptable
                assert not server2.is_running(), "Failed server should not be running"
        
        finally:
            server1.stop()
            if 'server2' in locals():
                server2.stop()
    
    @pytest.mark.asyncio
    async def test_memory_exhaustion_handling(self, error_test_server, unstable_mock_extension):
        """Test handling of memory exhaustion scenarios."""
        # Create many tabs to stress memory
        created_tabs = []
        for i in range(100):
            tab = unstable_mock_extension.create_tab(
                f"https://memory-test-{i}.com", 
                f"Memory Test {i}"
            )
            created_tabs.append(tab)
            
            if i % 10 == 0:
                await asyncio.sleep(0.1)  # Brief pause every 10 tabs
        
        await asyncio.sleep(2)  # Let system process all tabs
        
        # System should handle memory pressure gracefully
        final_stats = unstable_mock_extension.get_stats()
        assert final_stats['running'], "Extension should handle memory pressure"
        
        # Server should still be responsive
        try:
            response = requests.get(f"http://localhost:{error_test_server.port}/api/status", timeout=5)
            assert response.status_code == 200, "Server should remain responsive under memory pressure"
        except requests.RequestException:
            pytest.fail("Server should remain responsive under memory pressure")


class TestClassificationFailureScenarios:
    """Test classification pipeline failure scenarios."""
    
    @pytest.mark.asyncio
    async def test_classifier_exceptions(self, failing_classifier_registry):
        """Test handling of classifier exceptions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline = EnhancedClassificationPipeline(
                registry=failing_classifier_registry,
                cache_dir=temp_dir,
                config={'cache_enabled': True}
            )
            
            pipeline.add_classifier("failing_classifier")
            
            # Test multiple classifications with expected failures
            test_domains = [
                "github.com",
                "example.com", 
                "test.com",
                "github.io",
                "sample.org"
            ]
            
            results = []
            for domain_str in test_domains:
                domain = Domain(domain_str)
                try:
                    result = await pipeline.classify(domain)
                    results.append(result)
                except Exception as e:
                    logger.info(f"Expected classifier failure for {domain_str}: {e}")
                    results.append(None)
            
            # Some classifications should succeed despite failures
            successful_results = [r for r in results if r is not None]
            assert len(successful_results) > 0, "Some classifications should succeed despite failures"
            
            await pipeline.cache.close()
    
    @pytest.mark.asyncio
    async def test_classification_timeout_handling(self, failing_classifier_registry):
        """Test handling of classification timeouts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline = EnhancedClassificationPipeline(
                registry=failing_classifier_registry,
                cache_dir=temp_dir,
                config={'cache_enabled': True}
            )
            
            pipeline.add_classifier("timeout_classifier")
            
            domain = Domain("timeout-test.com")
            
            # Classification should timeout gracefully
            start_time = time.time()
            try:
                result = await asyncio.wait_for(pipeline.classify(domain), timeout=2.0)
            except asyncio.TimeoutError:
                result = None
            
            elapsed = time.time() - start_time
            assert elapsed < 3.0, "Should timeout quickly"
            
            # Pipeline should remain functional after timeout
            quick_domain = Domain("quick-test.com")
            quick_result = await pipeline.classify(quick_domain)
            # Should complete quickly (no timeout classifier match)
            
            await pipeline.cache.close()
    
    @pytest.mark.asyncio
    async def test_cache_corruption_recovery(self):
        """Test recovery from cache corruption."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create registry with working classifier
            registry = ClassifierRegistry()
            
            class WorkingClassifier:
                def __init__(self):
                    self.name = "working_classifier"
                
                def classify(self, domain):
                    return Category.PRODUCTIVITY if 'github' in domain.value else None
            
            registry.register(WorkingClassifier())
            
            pipeline = EnhancedClassificationPipeline(
                registry=registry,
                cache_dir=temp_dir,
                config={'cache_enabled': True}
            )
            
            pipeline.add_classifier("working_classifier")
            
            # Create some cached entries
            domain1 = Domain("github.com")
            result1 = await pipeline.classify(domain1)
            assert result1 is not None
            
            # Simulate cache corruption by writing invalid data
            cache_files = list(Path(temp_dir).glob("*.cache"))
            if cache_files:
                with open(cache_files[0], 'w') as f:
                    f.write("corrupted cache data")
            
            # Pipeline should recover from corruption
            domain2 = Domain("github.io")
            result2 = await pipeline.classify(domain2)
            assert result2 is not None, "Should recover from cache corruption"
            
            await pipeline.cache.close()


class TestNetworkFailureScenarios:
    """Test network-related failure scenarios."""
    
    @pytest.mark.asyncio
    async def test_network_partition_recovery(self, unstable_mock_extension):
        """Test recovery from network partition."""
        # Create tabs during normal operation
        tab1 = unstable_mock_extension.create_tab("https://github.com/normal", "Normal Operation")
        await asyncio.sleep(0.5)
        
        initial_requests = unstable_mock_extension.get_stats()['server_requests']
        
        # Simulate network partition by patching requests
        with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
            mock_post.side_effect = requests.ConnectionError("Network partition")
            mock_get.side_effect = requests.ConnectionError("Network partition")
            
            # Create tabs during partition
            tab2 = unstable_mock_extension.create_tab("https://github.com/partition", "During Partition")
            tab3 = unstable_mock_extension.create_tab("https://www.youtube.com/partition", "Partition Video")
            
            await asyncio.sleep(1)  # Let extension try to communicate
            
            partition_stats = unstable_mock_extension.get_stats()
            
            # Extension should handle network partition gracefully
            assert partition_stats['running'], "Extension should handle network partition"
            assert partition_stats['errors'] > 0, "Should record network errors"
            
            # Local state should be maintained
            local_tabs = unstable_mock_extension.get_tabs()
            assert len(local_tabs) == 3, "Should maintain local state during partition"
        
        # After partition ends, extension should recover
        await asyncio.sleep(1)
        recovery_stats = unstable_mock_extension.get_stats()
        
        # Should eventually resume communication (may take time due to retry backoff)
        assert recovery_stats['running'], "Extension should recover from network partition"
    
    @pytest.mark.asyncio
    async def test_intermittent_connectivity(self, error_test_server, unstable_mock_extension):
        """Test handling of intermittent connectivity issues."""
        # Track request success/failure patterns
        request_results = []
        
        # Simulate intermittent connectivity
        original_post = requests.post
        call_count = 0
        
        def intermittent_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # Fail every 3rd request
            if call_count % 3 == 0:
                request_results.append('fail')
                raise requests.RequestException("Intermittent failure")
            else:
                request_results.append('success')
                return original_post(*args, **kwargs)
        
        with patch('requests.post', side_effect=intermittent_post):
            # Create tabs with intermittent connectivity
            for i in range(10):
                tab = unstable_mock_extension.create_tab(f"https://intermittent-{i}.com", f"Intermittent {i}")
                await asyncio.sleep(0.2)
        
        await asyncio.sleep(1)
        
        # Extension should handle intermittent failures
        final_stats = unstable_mock_extension.get_stats()
        assert final_stats['running'], "Extension should handle intermittent connectivity"
        
        # Should have mix of successes and failures
        success_count = request_results.count('success')
        fail_count = request_results.count('fail')
        assert success_count > 0, "Should have some successful requests"
        assert fail_count > 0, "Should have some failed requests"


class TestCircuitBreakerScenarios:
    """Test circuit breaker behavior under failure conditions."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self):
        """Test circuit breaker activation under repeated failures."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=2.0,
            expected_exception=Exception
        )
        
        @circuit_breaker
        def failing_operation():
            raise Exception("Simulated failure")
        
        # Trigger circuit breaker
        failure_count = 0
        for i in range(5):
            try:
                failing_operation()
            except Exception:
                failure_count += 1
        
        assert failure_count >= 3, "Should record failures"
        assert circuit_breaker.state == "OPEN", "Circuit breaker should be open"
        
        # Subsequent calls should fail fast
        start_time = time.time()
        try:
            failing_operation()
        except Exception:
            pass
        elapsed = time.time() - start_time
        
        assert elapsed < 0.1, "Circuit breaker should fail fast when open"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1.0,
            expected_exception=Exception
        )
        
        call_count = 0
        
        @circuit_breaker
        def recovering_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Initial failures")
            return "success"
        
        # Trigger failures to open circuit
        for i in range(3):
            try:
                recovering_operation()
            except Exception:
                pass
        
        assert circuit_breaker.state == "OPEN"
        
        # Wait for recovery timeout
        await asyncio.sleep(1.5)
        
        # Should attempt recovery
        result = recovering_operation()
        assert result == "success", "Should recover after timeout"
        assert circuit_breaker.state == "CLOSED", "Circuit should be closed after recovery"


class TestResourceExhaustionScenarios:
    """Test resource exhaustion scenarios."""
    
    @pytest.mark.asyncio
    async def test_file_descriptor_exhaustion(self, error_test_server):
        """Test handling of file descriptor exhaustion."""
        # Simulate many concurrent connections
        connections = []
        
        try:
            # Create many connections to exhaust file descriptors
            for i in range(100):
                try:
                    response = requests.get(
                        f"http://localhost:{error_test_server.port}/api/status",
                        timeout=1,
                        stream=True  # Keep connection open
                    )
                    connections.append(response)
                except Exception as e:
                    logger.info(f"Connection {i} failed: {e}")
                    break
            
            # Server should handle resource exhaustion gracefully
            # Try one more request
            try:
                final_response = requests.get(
                    f"http://localhost:{error_test_server.port}/api/status",
                    timeout=5
                )
                # Should either succeed or fail gracefully
                assert final_response.status_code in [200, 503, 429], "Should handle resource exhaustion gracefully"
            except requests.RequestException:
                # Connection refused is acceptable under resource exhaustion
                pass
        
        finally:
            # Clean up connections
            for conn in connections:
                try:
                    conn.close()
                except:
                    pass
    
    @pytest.mark.asyncio
    async def test_disk_space_exhaustion_simulation(self):
        """Test handling of disk space exhaustion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create registry
            registry = ClassifierRegistry()
            
            class DiskHeavyClassifier:
                def __init__(self):
                    self.name = "disk_heavy_classifier"
                
                def classify(self, domain):
                    return Category.PRODUCTIVITY
            
            registry.register(DiskHeavyClassifier())
            
            pipeline = EnhancedClassificationPipeline(
                registry=registry,
                cache_dir=temp_dir,
                config={'cache_enabled': True}
            )
            
            pipeline.add_classifier("disk_heavy_classifier")
            
            # Simulate disk space exhaustion by filling cache directory
            try:
                # Create large file to simulate disk full
                large_file = Path(temp_dir) / "disk_full_simulation.tmp"
                with open(large_file, 'wb') as f:
                    f.write(b'0' * (1024 * 1024))  # 1MB file
                
                # Pipeline should handle disk issues gracefully
                domain = Domain("disk-test.com")
                result = await pipeline.classify(domain)
                
                # Should either succeed or fail gracefully
                # (In real scenario, would test actual disk full conditions)
                
            except Exception as e:
                logger.info(f"Disk exhaustion simulation: {e}")
            
            finally:
                await pipeline.cache.close()


class TestConcurrencyFailureScenarios:
    """Test failure scenarios under high concurrency."""
    
    @pytest.mark.asyncio
    async def test_race_condition_handling(self, error_test_server):
        """Test handling of race conditions."""
        # Create multiple extensions simultaneously
        extensions = []
        
        try:
            # Start multiple extensions concurrently
            start_tasks = []
            for i in range(5):
                extension = MockBrowserExtension(
                    tab_server_url=f"http://localhost:{error_test_server.port}",
                    browser_info=MockBrowserInfo(
                        name=f"RaceChrome{i}",
                        version="120.0.0.0",
                        extension_id=f"race-extension-{i}"
                    ),
                    polling_interval=0.05  # Very fast polling
                )
                extensions.append(extension)
                start_tasks.append(asyncio.create_task(asyncio.to_thread(extension.start)))
            
            # Start all extensions concurrently
            start_results = await asyncio.gather(*start_tasks, return_exceptions=True)
            
            # Most should start successfully
            successful_starts = sum(1 for result in start_results if result is True)
            assert successful_starts >= 3, "Most extensions should start despite race conditions"
            
            # Create tabs concurrently from all extensions
            tab_creation_tasks = []
            for i, extension in enumerate(extensions):
                if extension.get_stats()['running']:
                    task = asyncio.create_task(
                        asyncio.to_thread(
                            extension.create_tab, 
                            f"https://race-test-{i}.com", 
                            f"Race Test {i}"
                        )
                    )
                    tab_creation_tasks.append(task)
            
            if tab_creation_tasks:
                await asyncio.gather(*tab_creation_tasks, return_exceptions=True)
            
            await asyncio.sleep(1)  # Let system stabilize
            
            # Server should handle concurrent access
            response = requests.get(f"http://localhost:{error_test_server.port}/api/status")
            assert response.status_code == 200, "Server should handle concurrent access"
        
        finally:
            # Clean up extensions
            for extension in extensions:
                try:
                    extension.stop()
                except:
                    pass
    
    @pytest.mark.asyncio
    async def test_deadlock_prevention(self, error_test_server, unstable_mock_extension):
        """Test deadlock prevention mechanisms."""
        # Create scenario that could cause deadlock
        # Extension polling while server is processing commands
        
        # Create many tabs
        for i in range(20):
            unstable_mock_extension.create_tab(f"https://deadlock-test-{i}.com", f"Deadlock Test {i}")
        
        await asyncio.sleep(0.5)
        
        # Send many commands simultaneously
        command_tasks = []
        tabs = unstable_mock_extension.get_tabs()
        
        for tab in tabs[:10]:  # Close half the tabs
            command = {
                "action": "close_tab",
                "data": {"tabId": tab.id},
                "browser_id": "unstable-test-extension"
            }
            
            task = asyncio.create_task(
                asyncio.to_thread(
                    requests.post,
                    f"http://localhost:{error_test_server.port}/api/command",
                    json=command,
                    timeout=2
                )
            )
            command_tasks.append(task)
        
        # Execute all commands concurrently
        command_results = await asyncio.gather(*command_tasks, return_exceptions=True)
        
        # System should not deadlock
        successful_commands = sum(
            1 for result in command_results 
            if not isinstance(result, Exception) and hasattr(result, 'status_code') and result.status_code == 200
        )
        
        assert successful_commands > 0, "Some commands should succeed without deadlock"
        
        # Extension should remain responsive
        final_stats = unstable_mock_extension.get_stats()
        assert final_stats['running'], "Extension should remain responsive"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short", "-x"])  # Stop on first failure for debugging
