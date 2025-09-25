"""
Test runner for session monitoring tests.

This script runs all the unit tests for the session monitoring components.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import the test modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import the test modules
from tests.activity.platform.test_session_monitor import TestSessionListener, TestSessionMonitor
from tests.activity.platform.test_windows_session import TestWindowsSessionMonitor
from tests.activity.test_session_adapter import TestActivitySessionAdapter, TestSessionAdapterSingletonFunctions


def run_tests():
    """Run all session monitoring tests."""
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add the test cases
    test_suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestSessionListener))
    test_suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestSessionMonitor))
    test_suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestWindowsSessionMonitor))
    test_suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestActivitySessionAdapter))
    test_suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestSessionAdapterSingletonFunctions))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return the result
    return result


if __name__ == '__main__':
    result = run_tests()
    # Exit with non-zero code if tests failed
    sys.exit(not result.wasSuccessful())
