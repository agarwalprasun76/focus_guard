#!/usr/bin/env python3
"""
Test script for robust error handling and resilience features.

This script tests the Phase 2 implementation including:
- Circuit breaker patterns
- Retry mechanisms with exponential backoff
- Graceful degradation
- Error monitoring and recovery
"""

import asyncio
import logging
import requests
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_circuit_breaker_functionality():
    """Test circuit breaker patterns."""
    logger.info("Testing circuit breaker functionality...")
    
    from focus_guard.core.utils.circuit_breaker import (
        CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError
    )
    
    # Create circuit breaker with low thresholds for testing
    config = CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=1.0,
        success_threshold=1,
        timeout=1.0
    )
    
    breaker = CircuitBreaker(config, "test_breaker")
    
    # Test function that fails
    def failing_function():
        raise ConnectionError("Simulated failure")
    
    # Test function that succeeds
    def success_function():
        return "success"
    
    try:
        # Test normal operation (closed state)
        result = breaker.call(success_function)
        assert result == "success"
        logger.info("✅ Circuit breaker closed state working")
        
        # Cause failures to open circuit
        for i in range(3):
            try:
                breaker.call(failing_function)
            except (ConnectionError, CircuitBreakerError):
                pass
        
        # Circuit should now be open
        try:
            breaker.call(success_function)
            assert False, "Circuit should be open"
        except CircuitBreakerError:
            logger.info("✅ Circuit breaker open state working")
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Should be in half-open state, allow one success to close
        result = breaker.call(success_function)
        assert result == "success"
        logger.info("✅ Circuit breaker recovery working")
        
        return True
        
    except Exception as e:
        logger.error(f"Circuit breaker test failed: {e}")
        return False

def test_retry_mechanisms():
    """Test enhanced retry mechanisms."""
    logger.info("Testing retry mechanisms...")
    
    from focus_guard.core.utils.enhanced_retry import (
        retry, BackoffStrategy, RetryExhaustedError
    )
    
    try:
        # Test successful retry
        attempt_count = 0
        
        @retry(max_attempts=3, base_delay=0.1, backoff_strategy=BackoffStrategy.EXPONENTIAL)
        def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert attempt_count == 3
        logger.info("✅ Retry with eventual success working")
        
        # Test retry exhaustion
        @retry(max_attempts=2, base_delay=0.1)
        def always_failing_function():
            raise ValueError("Always fails")
        
        try:
            always_failing_function()
            assert False, "Should have exhausted retries"
        except RetryExhaustedError as e:
            assert e.attempts == 2
            logger.info("✅ Retry exhaustion working")
        
        return True
        
    except Exception as e:
        logger.error(f"Retry mechanism test failed: {e}")
        return False

def test_browser_integration_resilience():
    """Test browser integration resilience features."""
    logger.info("Testing browser integration resilience...")
    
    from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
    
    try:
        # Create integration with auto_start=False to avoid process conflicts
        integration = BrowserIntegration(
            tab_server_url="http://localhost:5010",
            auto_start=False
        )
        
        # Test classification fallback
        should_block, reason = integration._fallback_classification(
            "https://youtube.com/watch?v=test",
            "youtube.com"
        )
        
        assert should_block == True
        assert reason == "fallback_high_risk"
        logger.info("✅ Classification fallback working")
        
        # Test error recording
        initial_count = integration._error_counts['classification_errors']
        integration._record_error('classification_errors')
        assert integration._error_counts['classification_errors'] == initial_count + 1
        logger.info("✅ Error recording working")
        
        # Test health status
        health = integration.get_health_status()
        assert 'circuit_breakers' in health
        assert 'error_counts' in health
        logger.info("✅ Health status reporting working")
        
        # Test circuit breaker reset
        integration.reset_circuit_breakers()
        logger.info("✅ Circuit breaker reset working")
        
        return True
        
    except Exception as e:
        logger.error(f"Browser integration resilience test failed: {e}")
        return False
    finally:
        try:
            integration.stop()
        except:
            pass

def test_network_retry_decorator():
    """Test network-specific retry decorator."""
    logger.info("Testing network retry decorator...")
    
    from focus_guard.core.utils.enhanced_retry import retry_network_call
    
    try:
        # Mock requests to simulate network failures
        with patch('requests.get') as mock_get:
            # First two calls fail, third succeeds
            mock_get.side_effect = [
                requests.exceptions.ConnectionError("Network error"),
                requests.exceptions.Timeout("Timeout"),
                Mock(status_code=200, json=lambda: {"success": True})
            ]
            
            @retry_network_call(max_attempts=3, base_delay=0.1)
            def make_network_call():
                response = requests.get("http://example.com")
                return response.json()
            
            result = make_network_call()
            assert result["success"] == True
            assert mock_get.call_count == 3
            logger.info("✅ Network retry decorator working")
        
        return True
        
    except Exception as e:
        logger.error(f"Network retry test failed: {e}")
        return False

def test_graceful_degradation():
    """Test graceful degradation scenarios."""
    logger.info("Testing graceful degradation...")
    
    from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
    from focus_guard.core.utils.circuit_breaker import CircuitBreakerError
    
    try:
        integration = BrowserIntegration(
            tab_server_url="http://localhost:5011",
            auto_start=False
        )
        
        # Test classification with circuit breaker open
        with patch.object(integration._classification_breaker, 'call') as mock_call:
            mock_call.side_effect = CircuitBreakerError("Circuit open")
            
            should_block, reason = integration._classify_for_blocking_with_resilience(
                "https://youtube.com/watch?v=test",
                "youtube.com",
                "Chrome",
                "123"
            )
            
            assert should_block == True  # Fallback should still block high-risk domains
            assert "fallback" in reason
            logger.info("✅ Classification graceful degradation working")
        
        # Test tab retrieval with cached data
        integration._tab_cache = [{"id": 1, "url": "https://example.com"}]
        
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
            
            tabs = integration.get_all_tabs()
            assert len(tabs) == 1  # Should return cached data
            logger.info("✅ Tab retrieval graceful degradation working")
        
        return True
        
    except Exception as e:
        logger.error(f"Graceful degradation test failed: {e}")
        return False
    finally:
        try:
            integration.stop()
        except:
            pass

def test_error_monitoring():
    """Test error monitoring and alerting."""
    logger.info("Testing error monitoring...")
    
    from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
    
    try:
        integration = BrowserIntegration(
            tab_server_url="http://localhost:5012",
            auto_start=False
        )
        
        # Test error count tracking
        initial_counts = integration._error_counts.copy()
        
        # Record multiple errors
        for i in range(5):
            integration._record_error('tab_server_connection')
        
        assert integration._error_counts['tab_server_connection'] == initial_counts['tab_server_connection'] + 5
        logger.info("✅ Error count tracking working")
        
        # Test error rate reset
        for i in range(10):  # Exceed max error rate
            integration._record_error('classification_errors')
        
        # Should reset counts
        assert sum(integration._error_counts.values()) < 10
        logger.info("✅ Error rate reset working")
        
        return True
        
    except Exception as e:
        logger.error(f"Error monitoring test failed: {e}")
        return False
    finally:
        try:
            integration.stop()
        except:
            pass

def test_concurrent_resilience():
    """Test resilience under concurrent load."""
    logger.info("Testing concurrent resilience...")
    
    from focus_guard.core.utils.circuit_breaker import get_circuit_breaker, CircuitBreakerConfig
    import concurrent.futures
    
    try:
        # Create circuit breaker for concurrent testing
        config = CircuitBreakerConfig(failure_threshold=10, recovery_timeout=1.0)
        breaker = get_circuit_breaker("concurrent_test", config)
        
        def concurrent_operation(operation_id):
            try:
                if operation_id % 3 == 0:  # Some operations fail
                    raise ConnectionError(f"Operation {operation_id} failed")
                return f"Success {operation_id}"
            except Exception as e:
                raise
        
        # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(breaker.call, concurrent_operation, i) 
                for i in range(50)
            ]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception:
                    pass  # Expected failures
        
        # Should have some successes despite failures
        assert len(results) > 0
        logger.info(f"✅ Concurrent resilience working - {len(results)} successes out of 50 operations")
        
        return True
        
    except Exception as e:
        logger.error(f"Concurrent resilience test failed: {e}")
        return False

def run_all_error_handling_tests():
    """Run all error handling and resilience tests."""
    logger.info("Starting Phase 2 error handling and resilience tests...")
    
    tests = [
        ("Circuit Breaker Functionality", test_circuit_breaker_functionality),
        ("Retry Mechanisms", test_retry_mechanisms),
        ("Browser Integration Resilience", test_browser_integration_resilience),
        ("Network Retry Decorator", test_network_retry_decorator),
        ("Graceful Degradation", test_graceful_degradation),
        ("Error Monitoring", test_error_monitoring),
        ("Concurrent Resilience", test_concurrent_resilience)
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
        time.sleep(0.5)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("ERROR HANDLING TEST SUMMARY")
    logger.info('='*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All error handling tests passed!")
        return True
    else:
        logger.error(f"⚠️  {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = run_all_error_handling_tests()
    exit(0 if success else 1)
