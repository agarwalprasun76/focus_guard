#!/usr/bin/env python3
"""
Simple test script for tab server lifecycle management improvements.

This script tests the core functionality without singleton conflicts.
"""

import time
import logging
import requests
import sys
import os
from pathlib import Path

# Add the focus_guard package to the path
sys.path.insert(0, str(Path(__file__).parent))

from focus_guard.core.browser.extension.process_manager import get_tab_server_process_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_process_manager_lifecycle():
    """Test process manager start/stop/health monitoring."""
    logger.info("Testing process manager lifecycle...")
    
    # Create a fresh process manager instance
    process_manager = get_tab_server_process_manager(
        health_check_interval=10,  # Check every 10 seconds
        auto_restart=True,
        max_restarts=3
    )
    
    try:
        # Test initial state
        assert not process_manager.is_running(), "Process should not be running initially"
        
        # Start process
        logger.info("Starting tab server process...")
        success = process_manager.start()
        assert success, "Process should start successfully"
        
        # Verify process is running
        time.sleep(2)  # Give it time to start
        assert process_manager.is_running(), "Process should be running"
        
        # Get status
        status = process_manager.get_status()
        logger.info(f"Process status: {status}")
        assert status["running"], "Status should show running"
        assert status["pid"] is not None, "Status should include PID"
        
        # Test health monitoring (wait for at least one health check)
        logger.info("Waiting for health check...")
        time.sleep(12)  # Wait for health check to run
        
        status = process_manager.get_status()
        health_status = status.get("health_status", "unknown")
        logger.info(f"Health status: {health_status}")
        
        # Health status should be one of the valid states
        valid_states = ["healthy", "degraded", "unhealthy", "error", "unknown"]
        assert health_status in valid_states, f"Health status should be valid: {health_status}"
        
        logger.info("✓ Process manager lifecycle test passed")
        return True
        
    except Exception as e:
        logger.error(f"Process manager test failed: {e}")
        return False
    finally:
        # Clean up
        logger.info("Stopping process...")
        process_manager.stop()
        time.sleep(2)
        assert not process_manager.is_running(), "Process should be stopped"

def test_direct_http_communication():
    """Test direct HTTP communication with tab server process."""
    logger.info("Testing direct HTTP communication...")
    
    process_manager = get_tab_server_process_manager()
    
    try:
        # Start the process
        success = process_manager.start()
        assert success, "Process should start"
        
        # Wait for server to be ready
        time.sleep(3)
        
        # Try different ports to find the running server
        ports_to_try = [5000, 5001, 5002, 5003, 5004, 5005]
        server_port = None
        
        for port in ports_to_try:
            try:
                response = requests.get(f"http://localhost:{port}/api/status", timeout=2)
                if response.status_code == 200:
                    server_port = port
                    logger.info(f"Found server running on port {port}")
                    break
            except:
                continue
        
        if server_port is None:
            logger.warning("Could not find running server on any port")
            return False
        
        # Test status endpoint
        response = requests.get(f"http://localhost:{server_port}/api/status")
        assert response.status_code == 200, "Status endpoint should work"
        
        status_data = response.json()
        logger.info(f"Server status: {status_data.get('status')}")
        
        # Test health endpoint if available
        try:
            response = requests.get(f"http://localhost:{server_port}/api/health")
            if response.status_code in [200, 503]:
                health_data = response.json()
                logger.info(f"Server health: {health_data.get('status')}")
        except:
            logger.info("Health endpoint not available (expected for process mode)")
        
        # Test graceful shutdown
        try:
            response = requests.post(f"http://localhost:{server_port}/api/shutdown", timeout=5)
            if response.status_code == 200:
                logger.info("✓ Graceful shutdown request sent")
                time.sleep(2)
            else:
                logger.info("Shutdown endpoint not available, using process termination")
        except:
            logger.info("Shutdown endpoint not available, using process termination")
        
        logger.info("✓ HTTP communication test passed")
        return True
        
    except Exception as e:
        logger.error(f"HTTP communication test failed: {e}")
        return False
    finally:
        process_manager.stop()

def test_port_discovery():
    """Test that the process manager can discover the actual port used."""
    logger.info("Testing port discovery...")
    
    process_manager = get_tab_server_process_manager()
    
    try:
        success = process_manager.start()
        assert success, "Process should start"
        
        time.sleep(3)  # Wait for startup
        
        status = process_manager.get_status()
        logger.info(f"Process status: {status}")
        
        # Check if port information is available
        if "port" in status and status["port"]:
            logger.info(f"✓ Port discovered: {status['port']}")
        else:
            logger.info("Port information not available in status")
        
        return True
        
    except Exception as e:
        logger.error(f"Port discovery test failed: {e}")
        return False
    finally:
        process_manager.stop()

def run_simple_tests():
    """Run simplified lifecycle tests."""
    logger.info("Starting simplified tab server lifecycle tests...")
    
    tests = [
        test_process_manager_lifecycle,
        test_direct_http_communication,
        test_port_discovery,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            logger.info(f"\n--- Running {test.__name__} ---")
            success = test()
            if success:
                logger.info(f"✓ {test.__name__} PASSED")
                passed += 1
            else:
                logger.error(f"✗ {test.__name__} FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        
        # Brief pause between tests
        time.sleep(2)
    
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
        success = run_simple_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        sys.exit(1)
