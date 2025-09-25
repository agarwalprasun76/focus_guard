#!/usr/bin/env python3
"""
Test script for enhanced real-time tab blocking coordination.

This script tests the improved event-driven tab blocking system with:
- Real-time event streaming from browser extension
- Fast classification pipeline integration
- Preemptive blocking with caching
- Event batching and processing
"""

import asyncio
import json
import logging
import requests
import time
import threading
from typing import Dict, List, Any
from unittest.mock import Mock, patch

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_tab_server_event_endpoints():
    """Test the new event streaming endpoints in the tab server."""
    logger.info("Testing tab server event endpoints...")
    
    from focus_guard.core.browser.extension.tab_server import get_tab_server
    from focus_guard.core.browser.extension.interfaces import TabServerConfig
    
    # Create tab server with test configuration
    config = TabServerConfig(host='localhost', port=5001)
    server = get_tab_server(config)
    
    try:
        # Start the server
        if not server.start(5001):
            logger.error("Failed to start tab server")
            return False
        
        logger.info("Tab server started successfully")
        time.sleep(1)  # Give server time to start
        
        # Test event processing
        test_event = {
            'type': 'tab_created',
            'data': {
                'id': 123,
                'url': 'https://youtube.com/watch?v=test',
                'title': 'Test Video'
            },
            'timestamp': time.time() * 1000,
            'browser': 'Google Chrome'
        }
        
        # Process event directly
        server.process_tab_event(test_event)
        logger.info("Event processed successfully")
        
        # Test event retrieval
        events = server.get_recent_events(browser='Google Chrome', limit=10)
        logger.info(f"Retrieved {len(events)} events")
        
        if len(events) > 0:
            logger.info(f"Latest event: {events[-1]['type']}")
        
        # Test blocking decision
        should_block, reason = server._get_blocking_decision(
            'https://youtube.com/watch?v=test',
            'youtube.com',
            'Google Chrome',
            '123'
        )
        logger.info(f"Blocking decision: {should_block} ({reason})")
        
        # Test HTTP endpoints
        base_url = f"http://localhost:5001"
        
        # Test POST event
        response = requests.post(
            f"{base_url}/api/events",
            json=test_event,
            headers={'X-Event-Type': 'tab_created'}
        )
        
        if response.status_code == 200:
            logger.info("Event POST endpoint working")
        else:
            logger.error(f"Event POST failed: {response.status_code}")
        
        # Test GET events
        response = requests.get(f"{base_url}/api/events?browser=Google Chrome&limit=5")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Event GET endpoint working - {len(data.get('events', []))} events")
        else:
            logger.error(f"Event GET failed: {response.status_code}")
        
        # Test blocking endpoint
        response = requests.get(
            f"{base_url}/api/should_block",
            params={
                'url': 'https://youtube.com/watch?v=test',
                'domain': 'youtube.com',
                'browser': 'Google Chrome',
                'tabId': '123'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Blocking endpoint working - should_block: {data.get('should_block')}")
        else:
            logger.error(f"Blocking endpoint failed: {response.status_code}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing tab server: {e}")
        return False
    finally:
        server.stop()
        logger.info("Tab server stopped")

def test_browser_integration_classification():
    """Test the enhanced browser integration with classification callbacks."""
    logger.info("Testing browser integration classification...")
    
    from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
    
    # Mock classification callback
    def mock_classifier(url: str, domain: str, browser: str, tab_id: str) -> tuple[bool, str]:
        """Mock classification callback for testing."""
        if 'youtube.com' in domain:
            return True, 'blocked_video_streaming'
        elif 'facebook.com' in domain:
            return True, 'blocked_social_media'
        else:
            return False, 'allowed_domain'
    
    try:
        # Create browser integration with auto_start=False to avoid process conflicts
        integration = BrowserIntegration(
            tab_server_url="http://localhost:5002",
            auto_start=False
        )
        
        # Set classification callback
        integration.set_classification_callback(mock_classifier)
        logger.info("Classification callback set")
        
        # Test classification directly
        should_block, reason = integration._classify_for_blocking(
            'https://youtube.com/watch?v=test',
            'youtube.com',
            'Google Chrome',
            '123'
        )
        
        logger.info(f"Classification result: {should_block} ({reason})")
        
        if should_block and reason == 'blocked_video_streaming':
            logger.info("Classification callback working correctly")
        else:
            logger.error(f"Unexpected classification result: {should_block}, {reason}")
            return False
        
        # Test enabling/disabling blocking
        integration.enable_blocking(False)
        should_block, reason = integration._classify_for_blocking(
            'https://youtube.com/watch?v=test',
            'youtube.com',
            'Google Chrome',
            '123'
        )
        
        if not should_block and reason == 'blocking_disabled':
            logger.info("Blocking disable/enable working correctly")
        else:
            logger.error(f"Blocking disable failed: {should_block}, {reason}")
            return False
        
        # Re-enable blocking
        integration.enable_blocking(True)
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing browser integration: {e}")
        return False
    finally:
        try:
            integration.stop()
        except:
            pass

def test_event_batching():
    """Test event batching functionality."""
    logger.info("Testing event batching...")
    
    from focus_guard.core.browser.extension.tab_server import get_tab_server
    from focus_guard.core.browser.extension.interfaces import TabServerConfig
    
    # Create tab server
    config = TabServerConfig(host='localhost', port=5003)
    server = get_tab_server(config)
    
    try:
        if not server.start(5003):
            logger.error("Failed to start tab server for batching test")
            return False
        
        time.sleep(1)
        
        # Create batch of events
        events = []
        for i in range(5):
            events.append({
                'type': 'tab_updated',
                'data': {
                    'tabId': 100 + i,
                    'changeInfo': {'url': f'https://example{i}.com'},
                    'tab': {'id': 100 + i, 'url': f'https://example{i}.com'}
                },
                'timestamp': time.time() * 1000 + i,
                'browser': 'Google Chrome'
            })
        
        # Test batch processing
        batch_data = {'events': events}
        
        response = requests.post(
            f"http://localhost:5003/api/events",
            json=batch_data,
            headers={'X-Event-Batch': 'true'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'batch_processed' and data.get('count') == 5:
                logger.info("Event batching working correctly")
            else:
                logger.error(f"Unexpected batch response: {data}")
                return False
        else:
            logger.error(f"Batch processing failed: {response.status_code}")
            return False
        
        # Verify events were stored
        stored_events = server.get_recent_events(limit=10)
        if len(stored_events) >= 5:
            logger.info(f"Events stored correctly: {len(stored_events)} events")
        else:
            logger.error(f"Not all events stored: {len(stored_events)} events")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing event batching: {e}")
        return False
    finally:
        server.stop()

def test_blocking_cache():
    """Test blocking decision caching."""
    logger.info("Testing blocking decision caching...")
    
    from focus_guard.core.browser.extension.tab_server import get_tab_server
    from focus_guard.core.browser.extension.interfaces import TabServerConfig
    
    config = TabServerConfig(host='localhost', port=5004)
    server = get_tab_server(config)
    
    try:
        if not server.start(5004):
            logger.error("Failed to start tab server for cache test")
            return False
        
        time.sleep(1)
        
        # First call - should compute decision
        start_time = time.time()
        should_block1, reason1 = server._get_blocking_decision(
            'https://youtube.com/watch?v=test',
            'youtube.com',
            'Google Chrome',
            '123'
        )
        first_call_time = time.time() - start_time
        
        # Second call - should use cache
        start_time = time.time()
        should_block2, reason2 = server._get_blocking_decision(
            'https://youtube.com/watch?v=test',
            'youtube.com',
            'Google Chrome',
            '123'
        )
        second_call_time = time.time() - start_time
        
        # Results should be the same
        if should_block1 == should_block2 and reason1 == reason2:
            logger.info(f"Cache consistency verified: {should_block1} ({reason1})")
        else:
            logger.error(f"Cache inconsistency: {should_block1}/{should_block2}, {reason1}/{reason2}")
            return False
        
        # Second call should be faster (cached)
        if second_call_time < first_call_time:
            logger.info(f"Cache performance verified: {first_call_time:.4f}s -> {second_call_time:.4f}s")
        else:
            logger.warning(f"Cache may not be working: {first_call_time:.4f}s -> {second_call_time:.4f}s")
        
        # Test cache size limit
        for i in range(1005):  # Exceed cache limit
            server._get_blocking_decision(
                f'https://test{i}.com',
                f'test{i}.com',
                'Google Chrome',
                str(i)
            )
        
        # Cache should be limited to 1000 entries
        cache_size = len(server._blocking_cache)
        if cache_size <= 1000:
            logger.info(f"Cache size limit working: {cache_size} entries")
        else:
            logger.error(f"Cache size limit failed: {cache_size} entries")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing blocking cache: {e}")
        return False
    finally:
        server.stop()

def test_real_time_performance():
    """Test real-time blocking performance."""
    logger.info("Testing real-time blocking performance...")
    
    from focus_guard.core.browser.extension.tab_server import get_tab_server
    from focus_guard.core.browser.extension.interfaces import TabServerConfig
    
    config = TabServerConfig(host='localhost', port=5005)
    server = get_tab_server(config)
    
    try:
        if not server.start(5005):
            logger.error("Failed to start tab server for performance test")
            return False
        
        time.sleep(1)
        
        # Test blocking decision speed
        test_urls = [
            ('https://youtube.com/watch?v=test', 'youtube.com'),
            ('https://facebook.com/feed', 'facebook.com'),
            ('https://google.com/search', 'google.com'),
            ('https://github.com/user/repo', 'github.com'),
            ('https://stackoverflow.com/questions', 'stackoverflow.com')
        ]
        
        total_time = 0
        decisions = []
        
        for url, domain in test_urls:
            start_time = time.time()
            should_block, reason = server._get_blocking_decision(url, domain, 'Google Chrome', '123')
            decision_time = time.time() - start_time
            
            total_time += decision_time
            decisions.append((url, should_block, reason, decision_time))
            
            logger.info(f"{domain}: {should_block} ({reason}) - {decision_time:.4f}s")
        
        avg_time = total_time / len(test_urls)
        logger.info(f"Average blocking decision time: {avg_time:.4f}s")
        
        # Performance should be under 100ms for real-time blocking
        if avg_time < 0.1:
            logger.info("Real-time performance target met")
        else:
            logger.warning(f"Performance may be too slow for real-time: {avg_time:.4f}s")
        
        # Test concurrent decisions
        import concurrent.futures
        
        def make_decision(i):
            return server._get_blocking_decision(
                f'https://test{i}.com',
                f'test{i}.com',
                'Google Chrome',
                str(i)
            )
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_decision, i) for i in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        concurrent_time = time.time() - start_time
        logger.info(f"50 concurrent decisions completed in {concurrent_time:.4f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing real-time performance: {e}")
        return False
    finally:
        server.stop()

def run_all_tests():
    """Run all real-time blocking tests."""
    logger.info("Starting enhanced real-time tab blocking tests...")
    
    tests = [
        ("Tab Server Event Endpoints", test_tab_server_event_endpoints),
        ("Browser Integration Classification", test_browser_integration_classification),
        ("Event Batching", test_event_batching),
        ("Blocking Cache", test_blocking_cache),
        ("Real-time Performance", test_real_time_performance)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info('='*60)
        
        try:
            result = test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results[test_name] = False
        
        # Small delay between tests
        time.sleep(1)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info('='*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All real-time blocking tests passed!")
        return True
    else:
        logger.error(f"⚠️  {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
