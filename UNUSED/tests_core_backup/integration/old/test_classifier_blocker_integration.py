#!/usr/bin/env python
"""
Integration test for the end-to-end flow:
tab opens/updates → classifier decision → blocker action

This script tests the complete integration between:
- Browser tab detection
- Domain classification (including context-aware classification)
- Tab blocking decision
- Tab blocking action
"""

import os
import sys
import time
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import components
from core.browser_detection.browser_integration.tab_server_v2 import TabServer
from core.blocker.browser_tab_blocker import BrowserTabBlocker
from core.integrations.classifier_blocker_api import ClassifierBlockerAPI, TabInfo
from core.domain_classifier.classifiers.youtube_classifier import youtube_classifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("integration_test")

class IntegrationTest:
    """Test harness for integration testing of classifier and blocker."""
    
    def __init__(self):
        """Initialize the test components."""
        # Start tab server on a test port
        self.tab_server = TabServer(host="localhost", port=8123)
        self.tab_server.start()
        
        # Initialize classifier-blocker API with test categories
        self.classifier_api = ClassifierBlockerAPI(
            block_categories=["social", "entertainment", "distraction"],
            context_aware=True
        )
        
        # Initialize browser tab blocker
        self.tab_blocker = BrowserTabBlocker(
            block_categories=["social", "entertainment", "distraction"],
            use_extension=True,
            use_cdp_fallback=False
        )
        
        # Track test results
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "details": []
        }
    
    def cleanup(self):
        """Clean up resources."""
        if self.tab_server:
            self.tab_server.stop()
    
    def simulate_tab_open(self, tab_info: Dict[str, Any]) -> None:
        """
        Simulate a tab opening in the browser.
        
        Args:
            tab_info: Dictionary with tab information
        """
        # Convert to TabInfo object if needed
        if not isinstance(tab_info, TabInfo):
            tab_info = TabInfo.from_dict(tab_info)
        
        # Log the simulated tab open
        logger.info(f"Simulating tab open: {tab_info.url}")
        
        # 1. Check if tab should be blocked preemptively
        should_block, reason = self.classifier_api.should_block_tab(tab_info)
        
        if should_block:
            logger.info(f"Tab should be blocked preemptively: {tab_info.url} (Reason: {reason})")
            
            # 2. Simulate blocking action via browser tab blocker
            if tab_info.tab_id and tab_info.window_id:
                success = self.tab_blocker.close_browser_tab(
                    tab_id=tab_info.tab_id,
                    window_id=tab_info.window_id,
                    url=tab_info.url,
                    domain=tab_info.domain,
                    reason=reason
                )
                logger.info(f"Tab blocking {'succeeded' if success else 'failed'}")
                return success
        else:
            logger.info(f"Tab allowed: {tab_info.url} (Reason: {reason})")
            return False
    
    def run_test_case(self, test_case: Dict[str, Any]) -> bool:
        """
        Run a single test case.
        
        Args:
            test_case: Dictionary with test case information
                - name: Test case name
                - tab_info: Tab information
                - expected_block: Whether the tab should be blocked
                - expected_reason: Expected reason for blocking/allowing
                
        Returns:
            bool: True if test passed, False otherwise
        """
        name = test_case.get("name", "Unnamed test")
        tab_info = test_case.get("tab_info", {})
        expected_block = test_case.get("expected_block", False)
        expected_reason = test_case.get("expected_reason", "")
        
        logger.info(f"Running test case: {name}")
        
        # Create TabInfo object
        tab_obj = TabInfo.from_dict(tab_info)
        
        # Get blocking decision
        should_block, reason = self.classifier_api.should_block_tab(tab_obj)
        
        # Check if decision matches expectation
        decision_correct = should_block == expected_block
        reason_match = expected_reason in reason if expected_reason else True
        
        # Log result
        if decision_correct and reason_match:
            logger.info(f"✓ Test passed: {name}")
            self.test_results["passed"] += 1
        else:
            logger.error(f"✗ Test failed: {name}")
            logger.error(f"  Expected block: {expected_block}, Got: {should_block}")
            logger.error(f"  Expected reason to contain: {expected_reason}, Got: {reason}")
            self.test_results["failed"] += 1
        
        # Record details
        self.test_results["details"].append({
            "name": name,
            "url": tab_info.get("url", ""),
            "expected_block": expected_block,
            "actual_block": should_block,
            "expected_reason": expected_reason,
            "actual_reason": reason,
            "passed": decision_correct and reason_match
        })
        
        return decision_correct and reason_match
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all integration tests.
        
        Returns:
            Dict[str, Any]: Test results
        """
        # Define test cases
        test_cases = [
            {
                "name": "Social media blocking",
                "tab_info": {
                    "url": "https://www.facebook.com",
                    "domain": "facebook.com",
                    "title": "Facebook",
                    "tab_id": 1,
                    "window_id": 1
                },
                "expected_block": True,
                "expected_reason": "social"
            },
            {
                "name": "Work site allowed",
                "tab_info": {
                    "url": "https://github.com/focus-guard/focus-guard",
                    "domain": "github.com",
                    "title": "focus-guard/focus-guard: Productivity tool",
                    "tab_id": 2,
                    "window_id": 1
                },
                "expected_block": False,
                "expected_reason": "allowed"
            },
            {
                "name": "YouTube entertainment video blocked",
                "tab_info": {
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "domain": "youtube.com",
                    "title": "Rick Astley - Never Gonna Give You Up",
                    "tab_id": 3,
                    "window_id": 1,
                    "context": {
                        "title": "Rick Astley - Never Gonna Give You Up",
                        "description": "Official music video for Rick Astley",
                        "channel": "Rick Astley",
                        "tags": ["Rick Astley", "music", "pop"]
                    }
                },
                "expected_block": True,
                "expected_reason": "entertainment"
            },
            {
                "name": "YouTube educational video allowed",
                "tab_info": {
                    "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc",
                    "domain": "youtube.com",
                    "title": "Python Tutorial for Beginners",
                    "tab_id": 4,
                    "window_id": 1,
                    "context": {
                        "title": "Python Tutorial for Beginners - Learn Python in 5 Hours",
                        "description": "This Python tutorial for beginners shows how to get started with Python quickly.",
                        "channel": "Programming with Mosh",
                        "tags": ["python", "programming", "tutorial", "beginners"]
                    }
                },
                "expected_block": False,
                "expected_reason": "education"
            }
        ]
        
        # Run each test case
        for test_case in test_cases:
            self.run_test_case(test_case)
        
        # Print summary
        logger.info("=" * 50)
        logger.info(f"Test Summary: {self.test_results['passed']} passed, {self.test_results['failed']} failed")
        logger.info("=" * 50)
        
        return self.test_results


def main():
    """Main entry point for integration tests."""
    logger.info("Starting classifier-blocker integration tests")
    
    test = IntegrationTest()
    
    try:
        results = test.run_all_tests()
        
        # Output results
        print(json.dumps(results, indent=2))
        
        # Exit with appropriate code
        sys.exit(0 if results["failed"] == 0 else 1)
    finally:
        test.cleanup()


if __name__ == "__main__":
    main()
