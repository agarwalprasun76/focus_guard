#!/usr/bin/env python
"""
Test Runner for Browser Integration Tests

This script runs all the unit tests for the browser integration components.
"""

from core.logger.logger import setup_logger
setup_logger({"log_to_file": False})
import unittest
import sys
import os
from core.logger.logger import get_logger

logger = get_logger("browser_integration.runner")

# Add project root to Python path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import test modules
from tests.browser_integration.test_process_manager_v2 import TestProcessManagerV2
from tests.browser_integration.test_tab_server_v2 import TestTabServerV2, TestTabServerIntegration
from tests.browser_integration.test_tab_tracker_integration_v2 import TestTabTrackerIntegrationV2
from tests.browser_integration.test_browser_integration_v2 import TestBrowserIntegrationV2
from tests.browser_integration.test_background_js import TestBackgroundJS

def run_tests():
    """Run all browser integration tests"""
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    loader = unittest.TestLoader()

    logger.info("Loading TestProcessManagerV2...")
    test_suite.addTest(loader.loadTestsFromTestCase(TestProcessManagerV2))
    logger.info("Loaded TestProcessManagerV2.")

    logger.info("Loading TestTabServerV2...")
    test_suite.addTest(loader.loadTestsFromTestCase(TestTabServerV2))
    logger.info("Loaded TestTabServerV2.")

    logger.info("Loading TestTabServerIntegration...")
    test_suite.addTest(loader.loadTestsFromTestCase(TestTabServerIntegration))
    logger.info("Loaded TestTabServerIntegration.")

    logger.info("Loading TestTabTrackerIntegrationV2...")
    test_suite.addTest(loader.loadTestsFromTestCase(TestTabTrackerIntegrationV2))
    logger.info("Loaded TestTabTrackerIntegrationV2.")

    logger.info("Loading TestBrowserIntegrationV2...")
    test_suite.addTest(loader.loadTestsFromTestCase(TestBrowserIntegrationV2))
    logger.info("Loaded TestBrowserIntegrationV2.")

    logger.info("Loading TestBackgroundJS...")
    test_suite.addTest(loader.loadTestsFromTestCase(TestBackgroundJS))
    logger.info("Loaded TestBackgroundJS.")

    logger.info("Running all browser integration tests...")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    logger.info("Finished running all browser integration tests.")

    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests())
