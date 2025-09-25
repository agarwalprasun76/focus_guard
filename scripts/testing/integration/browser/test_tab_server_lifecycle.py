#!/usr/bin/env python3
"""
Test script for improved tab server lifecycle management.

This script tests the enhanced tab server startup, shutdown, health monitoring,
and process management features implemented in Phase 1.2.
"""

import time
import logging
import requests
import sys
import os
from pathlib import Path

# Add the focus_guard package to the path
sys.path.insert(0, str(Path(__file__).parent))

from focus_guard.core.browser.extension.tab_server import get_tab_server, TabServerConfig
from focus_guard.core.browser.extension.process_manager import get_tab_server_process_manager
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_tab_server_singleton():
    """Test that tab server singleton pattern works correctly."""
    logger.info("Testing tab server singleton pattern...")
    
    config1 = TabServerConfig(port=5001, host='localhost')
    config2 = TabServerConfig(port=5002, host='localhost')
    
    server1 = get_tab_server(config1)
    server2 = get_tab_server(config2)
    
    # Should be the same instance
    assert server1 is server2, "Tab server should be singleton"
    logger.info("✓ Singleton pattern working correctly")

def test_port_conflict_handling():
    """Test that tab server handles port conflicts gracefully."""
    logger.info("Testing port conflict handling...")
    
    config = TabServerConfig(port=0)  # Auto-select port
    server = get_tab_server(config)
    
    # Start server - should find available port
    success = server.start()
    assert success, "Server should start successfully with auto port selection"
    
    actual_port = server.port
    logger.info(f"✓ Server started on auto-selected port: {actual_port}")
    
    # Stop server
    server.stop()
    logger.info("✓ Port conflict handling working correctly")

def test_graceful_shutdown():
    """Test graceful shutdown functionality."""
    logger.info("Testing graceful shutdown...")
    
    config = TabServerConfig(port=5003)
    server = get_tab_server(config)
    
    # Start server
    success = server.start()
    assert success, "Server should start successfully"
    
    # Verify server is running
    assert server.is_running(), "Server should be running"
    
    # Test graceful shutdown via HTTP
    try:
        response = requests.post("http://localhost:5003/api/shutdown", timeout=5)
        assert response.status_code == 200, "Shutdown request should succeed"
        logger.info("✓ Graceful shutdown request sent successfully")
        
        # Wait for server to stop
        time.sleep(2)
        assert not server.is_running(), "Server should have stopped"
        logger.info("✓ Server stopped gracefully")
        
    except Exception as e:
        logger.error(f"Graceful shutdown test failed: {e}")
        server.stop()  # Fallback cleanup
        raise

def test_health_monitoring():
    """Test health monitoring endpoints."""
    logger.info("Testing health monitoring...")
    
    config = TabServerConfig(port=5004)
    server = get_tab_server(config)
    
    # Start server
    success = server.start()
    assert success, "Server should start successfully"
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:5004/api/health", timeout=5)
        assert response.status_code in [200, 503], "Health endpoint should respond"
        
        health_data = response.json()
        assert "status" in health_data, "Health data should include status"
        logger.info(f"✓ Health status: {health_data['status']}")
        
        # Test enhanced status endpoint
        response = requests.get("http://localhost:5004/api/status", timeout=5)
        assert response.status_code == 200, "Status endpoint should respond"
        
        status_data = response.json()
        assert "health" in status_data, "Status should include health info"
        assert "port" in status_data, "Status should include port info"
        logger.info("✓ Enhanced status endpoint working")
        
    finally:
        server.stop()

def test_process_manager_health_checks():
    """Test process manager health monitoring."""
    logger.info("Testing process manager health checks...")
    
    # Create process manager with short health check interval for testing
    process_manager = get_tab_server_process_manager(
        health_check_interval=5,  # Check every 5 seconds
        auto_restart=True,
        max_restarts=2
    )
    
    # Start process
    success = process_manager.start()
    assert success, "Process manager should start successfully"
    
    try:
        # Wait for health check to run
        time.sleep(6)
        
        status = process_manager.get_status()
        assert "health_status" in status, "Status should include health status"
        logger.info(f"✓ Process health status: {status['health_status']}")
        
        # Test health status method
        health_status = process_manager.get_health_status()
        assert health_status in ["healthy", "degraded", "unhealthy", "error", "unknown"], \
               f"Health status should be valid: {health_status}"
        logger.info("✓ Process manager health monitoring working")
        
    finally:
        process_manager.stop()

def test_browser_integration_startup():
    """Test browser integration startup with improved reliability."""
    logger.info("Testing browser integration startup...")
    
    # Create browser integration with auto-start
    browser_integration = BrowserIntegration(
        tab_server_url="http://localhost:5005",
        auto_start=True
    )
    
    # Should have started tab server automatically
    time.sleep(2)  # Give it time to start
    
    try:
        # Test that we can get status
        tabs = browser_integration.get_all_tabs()
        assert isinstance(tabs, list), "Should return list of tabs"
        logger.info("✓ Browser integration auto-startup working")
        
        # Test extension connection check
        connected = browser_integration.is_extension_connected()
        logger.info(f"✓ Extension connection status: {connected}")
        
    except Exception as e:
        logger.error(f"Browser integration test failed: {e}")
        raise

def test_startup_verification():
    """Test improved startup verification with exponential backoff."""
    logger.info("Testing startup verification...")
    
    browser_integration = BrowserIntegration(
        tab_server_url="http://localhost:5006",
        auto_start=False  # Don't auto-start
    )
    
    # Manually test the startup verification
    start_time = time.time()
    success = browser_integration._ensure_tab_server_running()
    end_time = time.time()
    
    assert success, "Tab server should start successfully"
    logger.info(f"✓ Server startup took {end_time - start_time:.1f}s")
    
    # Test that subsequent calls are fast (server already running)
    start_time = time.time()
    success = browser_integration._ensure_tab_server_running()
    end_time = time.time()
    
    assert success, "Tab server should still be running"
    assert end_time - start_time < 1.0, "Subsequent startup check should be fast"
    logger.info(f"✓ Subsequent startup check took {end_time - start_time:.3f}s")

def run_all_tests():
    """Run all lifecycle management tests."""
    logger.info("Starting tab server lifecycle management tests...")
    
    tests = [
        test_tab_server_singleton,
        test_port_conflict_handling,
        test_graceful_shutdown,
        test_health_monitoring,
        test_process_manager_health_checks,
        test_browser_integration_startup,
        test_startup_verification,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            logger.info(f"\n--- Running {test.__name__} ---")
            test()
            logger.info(f"✓ {test.__name__} PASSED")
            passed += 1
        except Exception as e:
            logger.error(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        
        # Brief pause between tests
        time.sleep(1)
    
    logger.info(f"\n=== Test Results ===")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    if failed == 0:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error(f"❌ {failed} test(s) failed")
        return False

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        sys.exit(1)
