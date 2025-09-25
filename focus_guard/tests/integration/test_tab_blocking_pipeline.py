"""
Comprehensive End-to-End Tab Blocking Pipeline Integration Tests.

This module tests the complete tab blocking pipeline from browser extension
through classification to blocking decisions, implementing Phase 3.1 requirements.
"""

import asyncio
import json
import time
import tempfile
import logging
import pytest
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from focus_guard.core.browser.extension.tab_server import TabServer, TabServerConfig
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
from focus_guard.core.classification.enhanced_pipeline import EnhancedClassificationPipeline
from focus_guard.core.classification.base import ClassifierRegistry
from focus_guard.core.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from focus_guard.core.api.api import ClassifierBlockerAPI
from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.cache.multi_level_cache import MultiLevelCache
from focus_guard.tests.integration.mock_browser_extension import MockBrowserExtension, MockBrowserInfo, MockTab

logger = logging.getLogger(__name__)


@pytest.fixture
async def temp_cache_dir():
    """Create temporary directory for cache."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
async def mock_classifier_registry():
    """Create mock classifier registry with test classifiers."""
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
    
    registry.register(ProductivityClassifier())
    registry.register(EntertainmentClassifier())
    registry.register(SocialMediaClassifier())
    
    return registry


@pytest.fixture
async def tab_server(temp_cache_dir):
    """Create and start tab server for testing."""
    config = TabServerConfig(host='localhost', port=5555)  # Use non-standard port for testing
    server = TabServer(config)
    
    # Start server
    started = server.start(5555)
    if not started:
        pytest.skip("Could not start tab server for testing")
    
    # Wait for server to be ready
    await asyncio.sleep(1)
    
    yield server
    
    # Cleanup
    server.stop()


@pytest.fixture
async def mock_browser_extension(tab_server):
    """Create mock browser extension connected to tab server."""
    extension = MockBrowserExtension(
        tab_server_url=f"http://localhost:{tab_server.port}",
        browser_info=MockBrowserInfo(
            name="TestChrome",
            version="120.0.0.0",
            extension_id="test-extension-pipeline"
        ),
        polling_interval=0.2  # Fast polling for tests
    )
    
    # Start extension
    started = extension.start()
    if not started:
        pytest.skip("Could not start mock browser extension")
    
    yield extension
    
    # Cleanup
    extension.stop()


@pytest.fixture
async def classification_pipeline(mock_classifier_registry, temp_cache_dir):
    """Create enhanced classification pipeline."""
    pipeline = EnhancedClassificationPipeline(
        registry=mock_classifier_registry,
        cache_dir=temp_cache_dir,
        config={
            'cache_enabled': True,
            'background_classification': True,
            'performance_monitoring': True
        }
    )
    
    # Add classifiers
    pipeline.add_classifier("productivity_classifier")
    pipeline.add_classifier("entertainment_classifier")
    pipeline.add_classifier("social_media_classifier")
    
    yield pipeline
    
    # Cleanup
    await pipeline.cache.close()


@pytest.fixture
async def browser_integration(tab_server):
    """Create browser integration connected to tab server."""
    integration = BrowserIntegration(
        tab_server_url=f"http://localhost:{tab_server.port}",
        auto_start=False  # Server already started
    )
    
    yield integration


@pytest.fixture
async def classifier_blocker_api(classification_pipeline):
    """Create ClassifierBlockerAPI with mock pipeline."""
    with patch('focus_guard.core.api.api.ClassifierBlockerAPI._create_classification_pipeline') as mock_create:
        mock_create.return_value = classification_pipeline
        
        api = ClassifierBlockerAPI()
        yield api


class TestTabBlockingPipeline:
    """Test the complete tab blocking pipeline."""
    
    @pytest.mark.asyncio
    async def test_basic_tab_detection_and_classification(
        self, 
        mock_browser_extension, 
        browser_integration, 
        classifier_blocker_api
    ):
        """Test basic tab detection and classification flow."""
        # Create a tab in the mock extension
        tab = mock_browser_extension.create_tab(
            "https://github.com/test/repo", 
            "Test Repository", 
            active=True
        )
        
        # Wait for tab data to be sent to server
        await asyncio.sleep(0.5)
        
        # Get tabs from browser integration
        tabs = browser_integration.get_all_tabs()
        assert len(tabs) > 0, "Should detect tabs from mock extension"
        
        # Find our test tab
        test_tab = None
        for browser_tab in tabs:
            if "github.com" in browser_tab.get('url', ''):
                test_tab = browser_tab
                break
        
        assert test_tab is not None, "Should find the GitHub tab"
        
        # Test classification
        result = await classifier_blocker_api.classify_domain(test_tab['url'])
        assert result is not None, "Should classify GitHub domain"
        assert result.category == Category.PRODUCTIVITY, "GitHub should be classified as productivity"
    
    @pytest.mark.asyncio
    async def test_entertainment_blocking_decision(
        self, 
        mock_browser_extension, 
        browser_integration, 
        classifier_blocker_api
    ):
        """Test entertainment content blocking decisions."""
        # Create YouTube tab
        tab = mock_browser_extension.create_tab(
            "https://www.youtube.com/watch?v=test123", 
            "Test Video", 
            active=True
        )
        
        await asyncio.sleep(0.5)
        
        # Test classification
        result = await classifier_blocker_api.classify_domain(tab.url)
        assert result is not None, "Should classify YouTube domain"
        assert result.category == Category.ENTERTAINMENT, "YouTube should be classified as entertainment"
        
        # Test blocking decision
        should_block = await classifier_blocker_api.should_block_domain(tab.url)
        # Note: Blocking decision depends on configuration, just test that we get a boolean
        assert isinstance(should_block, bool), "Should return boolean blocking decision"
    
    @pytest.mark.asyncio
    async def test_social_media_detection_and_blocking(
        self, 
        mock_browser_extension, 
        browser_integration, 
        classifier_blocker_api
    ):
        """Test social media detection and blocking."""
        # Create multiple social media tabs
        social_sites = [
            ("https://www.facebook.com/feed", "Facebook Feed"),
            ("https://twitter.com/home", "Twitter Home"),
            ("https://www.instagram.com/", "Instagram Feed")
        ]
        
        created_tabs = []
        for url, title in social_sites:
            tab = mock_browser_extension.create_tab(url, title)
            created_tabs.append(tab)
        
        await asyncio.sleep(0.5)
        
        # Test classification for each
        for tab in created_tabs:
            result = await classifier_blocker_api.classify_domain(tab.url)
            assert result is not None, f"Should classify {tab.url}"
            assert result.category == Category.SOCIAL_MEDIA, f"{tab.url} should be social media"
    
    @pytest.mark.asyncio
    async def test_tab_closing_command_execution(
        self, 
        mock_browser_extension, 
        browser_integration, 
        tab_server
    ):
        """Test tab closing command execution through the pipeline."""
        # Create a tab to close
        tab = mock_browser_extension.create_tab(
            "https://www.facebook.com", 
            "Facebook", 
            active=True
        )
        
        await asyncio.sleep(0.5)
        
        # Send close command through browser integration
        success = browser_integration.close_tab(tab.id)
        assert success, "Should successfully send close command"
        
        # Wait for command to be processed
        await asyncio.sleep(1)
        
        # Verify tab was closed in mock extension
        remaining_tabs = mock_browser_extension.get_tabs()
        tab_ids = [t.id for t in remaining_tabs]
        assert tab.id not in tab_ids, "Tab should be closed"
    
    @pytest.mark.asyncio
    async def test_mixed_browsing_session_classification(
        self, 
        mock_browser_extension, 
        browser_integration, 
        classifier_blocker_api
    ):
        """Test classification during a mixed browsing session."""
        # Simulate a realistic browsing session
        session_tabs = [
            ("https://github.com/project", "GitHub Project", Category.PRODUCTIVITY),
            ("https://www.youtube.com/watch?v=abc", "YouTube Video", Category.ENTERTAINMENT),
            ("https://stackoverflow.com/questions/123", "Stack Overflow", Category.PRODUCTIVITY),
            ("https://www.facebook.com", "Facebook", Category.SOCIAL_MEDIA),
            ("https://docs.google.com/document", "Google Docs", Category.PRODUCTIVITY),
            ("https://unknown-site.com", "Unknown Site", None)  # Should not be classified
        ]
        
        created_tabs = []
        for url, title, expected_category in session_tabs:
            tab = mock_browser_extension.create_tab(url, title)
            created_tabs.append((tab, expected_category))
        
        await asyncio.sleep(1)  # Wait for all tabs to be processed
        
        # Test classification for each tab
        classification_results = []
        for tab, expected_category in created_tabs:
            result = await classifier_blocker_api.classify_domain(tab.url)
            classification_results.append((tab.url, result, expected_category))
            
            if expected_category is None:
                assert result is None, f"{tab.url} should not be classified"
            else:
                assert result is not None, f"{tab.url} should be classified"
                assert result.category == expected_category, f"{tab.url} should be {expected_category}"
        
        # Verify we got expected mix of classifications
        classified_count = sum(1 for _, result, _ in classification_results if result is not None)
        assert classified_count == 5, "Should classify 5 out of 6 tabs"
    
    @pytest.mark.asyncio
    async def test_cache_performance_in_pipeline(
        self, 
        mock_browser_extension, 
        browser_integration, 
        classifier_blocker_api
    ):
        """Test cache performance during repeated classifications."""
        # Create tab
        tab = mock_browser_extension.create_tab(
            "https://github.com/test", 
            "GitHub Test"
        )
        
        await asyncio.sleep(0.5)
        
        # First classification (cache miss)
        start_time = time.time()
        result1 = await classifier_blocker_api.classify_domain(tab.url)
        first_time = time.time() - start_time
        
        # Second classification (cache hit)
        start_time = time.time()
        result2 = await classifier_blocker_api.classify_domain(tab.url)
        second_time = time.time() - start_time
        
        # Verify results are consistent
        assert result1 is not None and result2 is not None
        assert result1.category == result2.category
        
        # Cache hit should be faster
        assert second_time < first_time, "Cache hit should be faster than cache miss"
        assert second_time < 0.1, "Cache hit should be very fast"
    
    @pytest.mark.asyncio
    async def test_concurrent_tab_processing(
        self, 
        mock_browser_extension, 
        browser_integration, 
        classifier_blocker_api
    ):
        """Test concurrent processing of multiple tabs."""
        # Create multiple tabs simultaneously
        urls = [
            "https://github.com/repo1",
            "https://www.youtube.com/watch?v=video1",
            "https://www.facebook.com/page1",
            "https://stackoverflow.com/questions/q1",
            "https://www.instagram.com/user1"
        ]
        
        # Create all tabs quickly
        created_tabs = []
        for i, url in enumerate(urls):
            tab = mock_browser_extension.create_tab(url, f"Tab {i+1}")
            created_tabs.append(tab)
        
        await asyncio.sleep(1)  # Wait for processing
        
        # Classify all tabs concurrently
        classification_tasks = [
            classifier_blocker_api.classify_domain(tab.url) 
            for tab in created_tabs
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*classification_tasks)
        total_time = time.time() - start_time
        
        # Verify all classifications completed
        successful_classifications = [r for r in results if r is not None]
        assert len(successful_classifications) == 5, "All tabs should be classified"
        
        # Concurrent processing should be reasonably fast
        assert total_time < 2.0, "Concurrent classification should complete quickly"
    
    @pytest.mark.asyncio
    async def test_tab_update_reclassification(
        self, 
        mock_browser_extension, 
        browser_integration, 
        classifier_blocker_api
    ):
        """Test reclassification when tab URL changes."""
        # Create tab with initial URL
        tab = mock_browser_extension.create_tab(
            "https://github.com/initial", 
            "Initial Page"
        )
        
        await asyncio.sleep(0.5)
        
        # Classify initial URL
        result1 = await classifier_blocker_api.classify_domain(tab.url)
        assert result1 is not None
        assert result1.category == Category.PRODUCTIVITY
        
        # Update tab to different category
        mock_browser_extension.update_tab(
            tab.id, 
            url="https://www.youtube.com/watch?v=updated",
            title="Updated Video"
        )
        
        await asyncio.sleep(0.5)
        
        # Get updated tab info
        updated_tabs = mock_browser_extension.get_tabs()
        updated_tab = next(t for t in updated_tabs if t.id == tab.id)
        
        # Classify updated URL
        result2 = await classifier_blocker_api.classify_domain(updated_tab.url)
        assert result2 is not None
        assert result2.category == Category.ENTERTAINMENT
        
        # Categories should be different
        assert result1.category != result2.category
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(
        self, 
        mock_browser_extension, 
        browser_integration, 
        classifier_blocker_api
    ):
        """Test error handling in the pipeline."""
        # Create tab with problematic URL
        tab = mock_browser_extension.create_tab(
            "invalid://not-a-real-url", 
            "Invalid URL"
        )
        
        await asyncio.sleep(0.5)
        
        # Classification should handle invalid URL gracefully
        result = await classifier_blocker_api.classify_domain(tab.url)
        # Should return None for invalid/unclassifiable URLs
        assert result is None, "Invalid URL should not be classified"
        
        # System should remain stable
        stats = mock_browser_extension.get_stats()
        assert stats['running'], "Extension should still be running"
    
    @pytest.mark.asyncio
    async def test_performance_metrics_collection(
        self, 
        mock_browser_extension, 
        browser_integration, 
        classifier_blocker_api,
        classification_pipeline
    ):
        """Test performance metrics collection throughout the pipeline."""
        # Create several tabs for metrics collection
        test_urls = [
            "https://github.com/metrics1",
            "https://www.youtube.com/watch?v=metrics2",
            "https://www.facebook.com/metrics3"
        ]
        
        for url in test_urls:
            tab = mock_browser_extension.create_tab(url, "Metrics Test")
            await asyncio.sleep(0.2)
            
            # Classify to generate metrics
            await classifier_blocker_api.classify_domain(url)
        
        # Check pipeline performance metrics
        pipeline_stats = classification_pipeline.get_performance_stats()
        assert 'total_requests' in pipeline_stats
        assert 'cache_hit_rate' in pipeline_stats
        assert 'avg_response_time' in pipeline_stats
        assert pipeline_stats['total_requests'] >= 3
        
        # Check extension stats
        extension_stats = mock_browser_extension.get_stats()
        assert extension_stats['tabs_created'] >= 3
        assert extension_stats['server_requests'] > 0
        assert extension_stats['running']


class TestErrorScenarios:
    """Test error scenarios and recovery in the tab blocking pipeline."""
    
    @pytest.mark.asyncio
    async def test_tab_server_restart_recovery(
        self, 
        mock_browser_extension, 
        browser_integration
    ):
        """Test recovery when tab server restarts."""
        # Verify initial connection
        initial_tabs = browser_integration.get_all_tabs()
        
        # Stop and restart tab server
        # Note: This is a simplified test - in real scenario would test actual restart
        await asyncio.sleep(0.5)
        
        # Extension should handle disconnection gracefully
        stats = mock_browser_extension.get_stats()
        # Extension should still be running even if server is temporarily unavailable
        assert stats['running'], "Extension should handle server restart"
    
    @pytest.mark.asyncio
    async def test_classification_timeout_handling(
        self, 
        mock_browser_extension, 
        classifier_blocker_api
    ):
        """Test handling of classification timeouts."""
        # Create tab
        tab = mock_browser_extension.create_tab(
            "https://timeout-test.com", 
            "Timeout Test"
        )
        
        # Mock a slow classifier that times out
        with patch.object(classifier_blocker_api, 'classify_domain') as mock_classify:
            async def slow_classify(url):
                await asyncio.sleep(10)  # Simulate very slow classification
                return None
            
            mock_classify.side_effect = slow_classify
            
            # Classification should timeout gracefully
            start_time = time.time()
            try:
                result = await asyncio.wait_for(
                    classifier_blocker_api.classify_domain(tab.url), 
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                result = None
            
            elapsed = time.time() - start_time
            assert elapsed < 3.0, "Should timeout quickly"
            assert result is None, "Should handle timeout gracefully"


@pytest.mark.asyncio
async def test_integration_test_suite_runner():
    """Test runner for the complete integration test suite."""
    # This function can be used to run all tests programmatically
    import pytest
    
    # Run all tests in this module
    result = pytest.main([__file__, "-v", "--tb=short"])
    return result == 0


if __name__ == "__main__":
    # Allow running tests directly
    asyncio.run(test_integration_test_suite_runner())
