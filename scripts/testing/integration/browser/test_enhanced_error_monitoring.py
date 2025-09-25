#!/usr/bin/env python3
"""
Comprehensive test for enhanced error monitoring and Phase 2 completion.

This script validates the complete Phase 2 implementation including:
- Enhanced error monitoring and alerting
- Component health tracking
- Error metrics and analytics
- Integration with browser components
"""

import asyncio
import logging
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

def test_error_monitoring_system():
    """Test the enhanced error monitoring system."""
    logger.info("Testing enhanced error monitoring system...")
    
    from focus_guard.core.utils.error_monitoring import (
        ErrorMonitor, ErrorSeverity, AlertType, get_error_monitor
    )
    
    try:
        # Create error monitor
        monitor = ErrorMonitor(error_rate_threshold=5.0, alert_cooldown=1.0)
        
        # Track alerts
        alerts_received = []
        def test_alert_handler(alert):
            alerts_received.append(alert)
        
        monitor.add_alert_handler(test_alert_handler)
        
        # Test error recording
        monitor.record_error(
            component="test_component",
            error_type="connection_error",
            message="Test connection failure",
            severity=ErrorSeverity.HIGH
        )
        
        # Test success recording
        monitor.record_success("test_component")
        
        # Generate multiple errors to trigger rate alert
        for i in range(6):
            monitor.record_error(
                component="test_component",
                error_type="rate_test_error",
                message=f"Rate test error {i}",
                severity=ErrorSeverity.MEDIUM
            )
        
        # Wait a moment for alert processing
        time.sleep(0.1)
        
        # Verify alerts were triggered
        assert len(alerts_received) > 0, "No alerts were triggered"
        
        # Test health status
        health = monitor.get_health_status()
        assert 'overall_status' in health
        assert 'component_health' in health
        assert 'metrics' in health
        
        # Test metrics
        metrics = monitor.metrics.get_error_summary()
        assert metrics['total_errors'] >= 7  # 1 + 6 rate test errors
        assert metrics['error_rate_per_minute'] > 0
        
        logger.info("✅ Enhanced error monitoring system working")
        return True
        
    except Exception as e:
        logger.error(f"Error monitoring system test failed: {e}")
        return False

def test_browser_integration_monitoring():
    """Test browser integration with enhanced monitoring."""
    logger.info("Testing browser integration monitoring...")
    
    from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
    from focus_guard.core.utils.error_monitoring import get_error_monitor
    
    try:
        # Get global monitor to track integration errors
        monitor = get_error_monitor()
        initial_health = monitor.get_health_status()
        
        # Create integration
        integration = BrowserIntegration(
            tab_server_url="http://localhost:5013",
            auto_start=False
        )
        
        # Test error recording in integration
        integration._record_error(
            "test_error",
            "Test error message",
            severity=integration.ErrorSeverity.HIGH,
            context={"test": "context"}
        )
        
        # Test success recording
        integration._record_success("test_operation")
        
        # Verify error was recorded in global monitor
        updated_health = monitor.get_health_status()
        assert 'browser_integration' in updated_health['component_health']
        
        # Test health status includes monitoring data
        health = integration.get_health_status()
        assert 'circuit_breakers' in health
        assert 'error_counts' in health
        assert 'error_monitoring' in health
        
        logger.info("✅ Browser integration monitoring working")
        return True
        
    except Exception as e:
        logger.error(f"Browser integration monitoring test failed: {e}")
        return False
    finally:
        try:
            integration.stop()
        except:
            pass

def test_component_health_tracking():
    """Test component health tracking and degradation detection."""
    logger.info("Testing component health tracking...")
    
    from focus_guard.core.utils.error_monitoring import (
        ErrorMonitor, ErrorSeverity
    )
    
    try:
        monitor = ErrorMonitor()
        
        # Test healthy component
        monitor.record_success("healthy_component")
        health = monitor.get_health_status()
        assert health['component_health']['healthy_component']['status'] == 'healthy'
        
        # Test degraded component (3 consecutive errors)
        for i in range(3):
            monitor.record_error(
                component="degraded_component",
                error_type="test_error",
                message=f"Error {i}",
                severity=ErrorSeverity.MEDIUM
            )
        
        health = monitor.get_health_status()
        assert health['component_health']['degraded_component']['status'] == 'degraded'
        
        # Test critical component (5+ consecutive errors)
        for i in range(5):
            monitor.record_error(
                component="critical_component",
                error_type="test_error",
                message=f"Critical error {i}",
                severity=ErrorSeverity.HIGH
            )
        
        health = monitor.get_health_status()
        assert health['component_health']['critical_component']['status'] == 'critical'
        assert 'critical_component' in health['critical_components']
        
        # Test recovery
        monitor.record_success("critical_component")
        health = monitor.get_health_status()
        assert health['component_health']['critical_component']['status'] == 'healthy'
        
        logger.info("✅ Component health tracking working")
        return True
        
    except Exception as e:
        logger.error(f"Component health tracking test failed: {e}")
        return False

def test_alert_system():
    """Test the alerting system with different alert types."""
    logger.info("Testing alert system...")
    
    from focus_guard.core.utils.error_monitoring import (
        ErrorMonitor, ErrorSeverity, AlertType
    )
    
    try:
        monitor = ErrorMonitor(error_rate_threshold=2.0, alert_cooldown=0.5)
        
        alerts_by_type = {}
        def categorize_alerts(alert):
            if alert.alert_type not in alerts_by_type:
                alerts_by_type[alert.alert_type] = []
            alerts_by_type[alert.alert_type].append(alert)
        
        monitor.add_alert_handler(categorize_alerts)
        
        # Trigger error rate alert
        for i in range(5):
            monitor.record_error(
                component="rate_test",
                error_type="rate_error",
                message=f"Rate error {i}",
                severity=ErrorSeverity.MEDIUM
            )
        
        # Trigger classification failure alert
        monitor.record_error(
            component="classifier",
            error_type="classification_failure",
            message="Classification failed",
            severity=ErrorSeverity.HIGH
        )
        
        # Trigger service unavailable alert (critical component)
        for i in range(5):
            monitor.record_error(
                component="critical_service",
                error_type="service_error",
                message=f"Service error {i}",
                severity=ErrorSeverity.CRITICAL
            )
        
        time.sleep(0.1)  # Allow alert processing
        
        # Verify different alert types were triggered
        assert AlertType.ERROR_RATE_EXCEEDED in alerts_by_type
        assert AlertType.CLASSIFICATION_FAILURE in alerts_by_type
        assert AlertType.SERVICE_UNAVAILABLE in alerts_by_type
        
        logger.info("✅ Alert system working")
        return True
        
    except Exception as e:
        logger.error(f"Alert system test failed: {e}")
        return False

def test_metrics_and_analytics():
    """Test error metrics and analytics."""
    logger.info("Testing metrics and analytics...")
    
    from focus_guard.core.utils.error_monitoring import (
        ErrorMonitor, ErrorSeverity
    )
    
    try:
        monitor = ErrorMonitor()
        
        # Generate test data
        components = ["web_server", "database", "classifier"]
        error_types = ["connection_error", "timeout", "validation_error"]
        
        for i in range(20):
            component = components[i % len(components)]
            error_type = error_types[i % len(error_types)]
            
            monitor.record_error(
                component=component,
                error_type=error_type,
                message=f"Test error {i}",
                severity=ErrorSeverity.MEDIUM
            )
        
        # Test metrics
        metrics = monitor.metrics.get_error_summary()
        
        # Verify metrics structure
        assert 'total_errors' in metrics
        assert 'error_rate_per_minute' in metrics
        assert 'top_error_types' in metrics
        assert 'component_breakdown' in metrics
        
        # Verify data
        assert metrics['total_errors'] == 20
        assert len(metrics['top_error_types']) > 0
        assert len(metrics['component_breakdown']) == 3
        
        # Test component-specific metrics
        for component in components:
            component_data = metrics['component_breakdown'][component]
            assert 'total_errors' in component_data
            assert 'error_rate' in component_data
            assert 'top_errors' in component_data
        
        # Test error rate calculation
        error_rate = monitor.metrics.get_error_rate(time_window=60.0)
        assert error_rate > 0
        
        logger.info("✅ Metrics and analytics working")
        return True
        
    except Exception as e:
        logger.error(f"Metrics and analytics test failed: {e}")
        return False

def test_integration_with_circuit_breakers():
    """Test integration between error monitoring and circuit breakers."""
    logger.info("Testing integration with circuit breakers...")
    
    from focus_guard.core.utils.error_monitoring import get_error_monitor
    from focus_guard.core.utils.circuit_breaker import get_circuit_breaker, CircuitBreakerConfig
    
    try:
        monitor = get_error_monitor()
        
        # Create circuit breaker
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0)
        breaker = get_circuit_breaker("integration_test", config)
        
        # Track alerts
        circuit_alerts = []
        def track_circuit_alerts(alert):
            if "circuit" in alert.message.lower():
                circuit_alerts.append(alert)
        
        monitor.add_alert_handler(track_circuit_alerts)
        
        # Function that fails
        def failing_operation():
            # Record error in monitoring
            monitor.record_error(
                component="circuit_test",
                error_type="operation_failure",
                message="Operation failed",
                severity=monitor.ErrorSeverity.HIGH
            )
            raise ConnectionError("Simulated failure")
        
        # Trigger circuit breaker failures
        for i in range(5):
            try:
                breaker.call(failing_operation)
            except:
                pass
        
        # Verify monitoring tracked the errors
        health = monitor.get_health_status()
        assert 'circuit_test' in health['component_health']
        
        logger.info("✅ Circuit breaker integration working")
        return True
        
    except Exception as e:
        logger.error(f"Circuit breaker integration test failed: {e}")
        return False

def run_all_enhanced_monitoring_tests():
    """Run all enhanced error monitoring tests."""
    logger.info("Starting Phase 2 Enhanced Error Monitoring Tests...")
    
    tests = [
        ("Error Monitoring System", test_error_monitoring_system),
        ("Browser Integration Monitoring", test_browser_integration_monitoring),
        ("Component Health Tracking", test_component_health_tracking),
        ("Alert System", test_alert_system),
        ("Metrics and Analytics", test_metrics_and_analytics),
        ("Circuit Breaker Integration", test_integration_with_circuit_breakers)
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
    logger.info("ENHANCED ERROR MONITORING TEST SUMMARY")
    logger.info('='*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All enhanced error monitoring tests passed!")
        logger.info("✅ Phase 2: Robust Error Handling and Retry Mechanisms COMPLETED")
        return True
    else:
        logger.error(f"⚠️  {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = run_all_enhanced_monitoring_tests()
    exit(0 if success else 1)
