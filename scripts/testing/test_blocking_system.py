"""
Comprehensive tests for the integrated blocking system.

This test suite validates the complete blocking system functionality including
policy management, application blocking, notifications, and override mechanisms.
"""

import sys
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from focus_guard.core.activity.blocking.blocking_system import BlockingSystem
from focus_guard.core.activity.blocking.models import (
    BlockingPolicy, BlockingAction, TimeRestriction, TimeRestrictionType,
    OverrideRequest
)
from focus_guard.core.activity.blocking.notification_manager import NotificationConfig
from focus_guard.core.activity.models import WindowInfo


def create_test_window_info(app_name: str, window_title: str = "Test Window", 
                           url: str = None) -> WindowInfo:
    """Create a test WindowInfo object."""
    return WindowInfo(
        app_name=app_name,
        window_title=window_title,
        pid="1234",  # Mock PID
        url=url,
        domain=url.split('/')[2] if url and '://' in url else None,
        timestamp=datetime.now()
    )


def test_blocking_system_initialization():
    """Test blocking system initialization."""
    print("Testing blocking system initialization...")
    
    # Test default initialization
    system = BlockingSystem()
    assert not system.is_active()
    assert system.total_evaluations == 0
    assert system.total_blocks == 0
    assert system.total_warnings == 0
    assert system.total_overrides == 0
    
    # Test with custom notification config
    notification_config = NotificationConfig(
        show_warnings=True,
        show_blocks=True,
        notification_timeout=5
    )
    system_with_config = BlockingSystem(notification_config)
    assert system_with_config.notification_manager.config.notification_timeout == 5
    
    print("SUCCESS: Blocking system initialization test passed")


def test_policy_management():
    """Test policy management functionality."""
    print("Testing policy management...")
    
    system = BlockingSystem()
    
    # Create test policy
    test_policy = BlockingPolicy(
        name="Test Policy",
        description="A test blocking policy",
        app_patterns=["chrome", "firefox"],
        domain_patterns=["facebook.com", "twitter.com"],
        action=BlockingAction.WARN,
        grace_period_seconds=30,
        warning_message="Test warning message"
    )
    
    # Test adding policy
    system.add_policy(test_policy)
    assert len(system.list_policies()) == 1
    
    # Test getting policy
    retrieved_policy = system.get_policy("Test Policy")
    assert retrieved_policy is not None
    assert retrieved_policy.name == "Test Policy"
    
    # Test updating policy
    updated_policy = BlockingPolicy(
        name="Test Policy",
        description="Updated test policy",
        app_patterns=["chrome", "firefox", "edge"],
        domain_patterns=["facebook.com", "twitter.com"],
        action=BlockingAction.BLOCK,
        grace_period_seconds=60
    )
    
    success = system.update_policy("Test Policy", updated_policy)
    assert success
    
    retrieved_updated = system.get_policy("Test Policy")
    assert retrieved_updated.action == BlockingAction.BLOCK
    assert retrieved_updated.grace_period_seconds == 60
    
    # Test removing policy
    success = system.remove_policy("Test Policy")
    assert success
    assert len(system.list_policies()) == 0
    
    print("SUCCESS: Policy management test passed")


def test_default_policies():
    """Test creation of default policies."""
    print("Testing default policies creation...")
    
    system = BlockingSystem()
    system.create_default_policies()
    
    policies = system.list_policies()
    assert len(policies) >= 3  # Should have at least 3 default policies
    
    policy_names = [p.name for p in policies]
    assert "Social Media Block" in policy_names
    assert "Entertainment Block" in policy_names
    assert "Gaming Block" in policy_names
    
    # Test that policies have expected patterns
    social_policy = system.get_policy("Social Media Block")
    assert "facebook" in social_policy.app_patterns
    assert "facebook.com" in social_policy.domain_patterns
    
    print("SUCCESS: Default policies test passed")


def test_application_evaluation():
    """Test application evaluation and blocking decisions."""
    print("Testing application evaluation...")
    
    system = BlockingSystem()
    
    # Create a blocking policy
    block_policy = BlockingPolicy(
        name="Block Chrome",
        description="Block Chrome browser",
        app_patterns=["chrome"],
        action=BlockingAction.BLOCK,
        grace_period_seconds=5
    )
    system.add_policy(block_policy)
    
    # Create a warning policy
    warn_policy = BlockingPolicy(
        name="Warn Firefox",
        description="Warn for Firefox usage",
        app_patterns=["firefox"],
        action=BlockingAction.WARN,
        grace_period_seconds=10
    )
    system.add_policy(warn_policy)
    
    # Test blocking decision for Chrome
    chrome_window = create_test_window_info("chrome", "Google Chrome")
    decision = system.evaluate_application(chrome_window)
    assert decision.should_block()
    assert decision.policy_name == "Block Chrome"
    
    # Test warning decision for Firefox
    firefox_window = create_test_window_info("firefox", "Mozilla Firefox")
    decision = system.evaluate_application(firefox_window)
    assert decision.should_warn()
    assert decision.policy_name == "Warn Firefox"
    
    # Test allowed application
    notepad_window = create_test_window_info("notepad", "Notepad")
    decision = system.evaluate_application(notepad_window)
    assert decision.action == BlockingAction.ALLOW
    
    # Check statistics
    assert system.total_evaluations == 3
    
    print("SUCCESS: Application evaluation test passed")


def test_system_lifecycle():
    """Test system start/stop lifecycle."""
    print("Testing system lifecycle...")
    
    system = BlockingSystem()
    
    # Test initial state
    assert not system.is_active()
    assert system.system_start_time is None
    
    # Test start
    system.start()
    assert system.is_active()
    assert system.system_start_time is not None
    
    # Test double start (should not cause issues)
    system.start()
    assert system.is_active()
    
    # Test stop
    system.stop()
    assert not system.is_active()
    
    # Test double stop (should not cause issues)
    system.stop()
    assert not system.is_active()
    
    print("SUCCESS: System lifecycle test passed")


def test_override_functionality():
    """Test override request and management."""
    print("Testing override functionality...")
    
    system = BlockingSystem()
    
    # Create a policy that allows overrides
    policy = BlockingPolicy(
        name="Override Test",
        description="Test policy with overrides",
        app_patterns=["test_app"],
        action=BlockingAction.BLOCK,
        override_allowed=True,
        override_duration_minutes=15
    )
    system.add_policy(policy)
    
    # Test requesting override
    success = system.request_override("test_app", reason="Testing override", duration_minutes=10)
    assert success
    assert system.total_overrides == 1
    
    # Test getting active overrides
    overrides = system.get_active_overrides()
    assert len(overrides) > 0
    
    # Test revoking override
    success = system.revoke_override("test_app")
    assert success
    
    # Verify override was removed
    overrides = system.get_active_overrides()
    test_app_overrides = [o for o in overrides.values() if o.get('app_name') == 'test_app']
    assert len(test_app_overrides) == 0
    
    print("SUCCESS: Override functionality test passed")


def test_system_status():
    """Test system status reporting."""
    print("Testing system status reporting...")
    
    system = BlockingSystem()
    system.start()
    
    # Add some policies and perform evaluations
    system.create_default_policies()
    
    # Perform some evaluations
    test_window = create_test_window_info("chrome", "Google Chrome")
    system.evaluate_application(test_window)
    
    # Get status
    status = system.get_system_status()
    
    # Verify status structure
    assert 'active' in status
    assert 'uptime_seconds' in status
    assert 'system_statistics' in status
    assert 'policy_engine' in status
    assert 'application_blocker' in status
    assert 'notification_manager' in status
    
    # Verify statistics
    stats = status['system_statistics']
    assert 'total_evaluations' in stats
    assert 'total_blocks' in stats
    assert 'total_warnings' in stats
    assert 'total_overrides' in stats
    assert 'evaluations_per_hour' in stats
    
    assert status['active'] == True
    assert stats['total_evaluations'] >= 1
    
    system.stop()
    
    print("SUCCESS: System status test passed")


def test_configuration_export_import():
    """Test configuration export and import."""
    print("Testing configuration export/import...")
    
    system1 = BlockingSystem()
    
    # Create some policies
    policy1 = BlockingPolicy(
        name="Export Test 1",
        description="First test policy",
        app_patterns=["app1"],
        action=BlockingAction.BLOCK
    )
    
    policy2 = BlockingPolicy(
        name="Export Test 2",
        description="Second test policy",
        app_patterns=["app2"],
        action=BlockingAction.WARN
    )
    
    system1.add_policy(policy1)
    system1.add_policy(policy2)
    
    # Export configuration
    config = system1.export_configuration()
    
    # Verify export structure
    assert 'policies' in config
    assert 'notification_config' in config
    assert 'export_timestamp' in config
    assert 'version' in config
    
    assert len(config['policies']) == 2
    
    # Create new system and import
    system2 = BlockingSystem()
    system2.import_configuration(config)
    
    # Verify import
    imported_policies = system2.list_policies()
    assert len(imported_policies) == 2
    
    policy_names = [p.name for p in imported_policies]
    assert "Export Test 1" in policy_names
    assert "Export Test 2" in policy_names
    
    print("SUCCESS: Configuration export/import test passed")


def test_statistics_reset():
    """Test statistics reset functionality."""
    print("Testing statistics reset...")
    
    system = BlockingSystem()
    system.start()
    
    # Perform some operations to generate statistics
    system.create_default_policies()
    test_window = create_test_window_info("chrome", "Google Chrome")
    system.evaluate_application(test_window)
    system.request_override("test_app", reason="Test")
    
    # Verify statistics exist
    assert system.total_evaluations > 0
    assert system.total_overrides > 0
    
    original_start_time = system.system_start_time
    
    # Reset statistics
    system.reset_statistics()
    
    # Verify reset
    assert system.total_evaluations == 0
    assert system.total_blocks == 0
    assert system.total_warnings == 0
    assert system.total_overrides == 0
    assert system.system_start_time != original_start_time  # Should be updated
    
    system.stop()
    
    print("SUCCESS: Statistics reset test passed")


def test_concurrent_operations():
    """Test concurrent operations on the blocking system."""
    print("Testing concurrent operations...")
    
    system = BlockingSystem()
    system.start()
    
    # Create a policy
    policy = BlockingPolicy(
        name="Concurrent Test",
        description="Test concurrent access",
        app_patterns=["test"],
        action=BlockingAction.WARN
    )
    system.add_policy(policy)
    
    results = []
    errors = []
    
    def evaluate_worker():
        """Worker function for concurrent evaluations."""
        try:
            for i in range(10):
                window = create_test_window_info(f"test_{i}", f"Test Window {i}")
                decision = system.evaluate_application(window)
                results.append(decision)
                time.sleep(0.01)  # Small delay
        except Exception as e:
            errors.append(e)
    
    def override_worker():
        """Worker function for concurrent override requests."""
        try:
            for i in range(5):
                success = system.request_override(f"test_app_{i}", reason=f"Test {i}")
                results.append(success)
                time.sleep(0.02)  # Small delay
        except Exception as e:
            errors.append(e)
    
    # Start concurrent threads
    threads = []
    for _ in range(3):
        t1 = threading.Thread(target=evaluate_worker)
        t2 = threading.Thread(target=override_worker)
        threads.extend([t1, t2])
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Verify no errors occurred
    assert len(errors) == 0, f"Errors occurred during concurrent operations: {errors}"
    
    # Verify operations completed
    assert len(results) > 0
    assert system.total_evaluations >= 30  # 3 threads * 10 evaluations each
    
    system.stop()
    
    print("SUCCESS: Concurrent operations test passed")


def run_quick_test():
    """Run a quick validation test of core functionality."""
    print("Running quick blocking system test...")
    print("=" * 50)
    
    try:
        # Test basic functionality
        test_blocking_system_initialization()
        test_policy_management()
        test_default_policies()
        test_application_evaluation()
        test_system_lifecycle()
        
        print("=" * 50)
        print("SUCCESS: Quick test completed successfully!")
        print("All core blocking system functionality is working correctly.")
        
    except Exception as e:
        print(f"FAILED: Quick test failed: {e}")
        raise


def run_comprehensive_test():
    """Run comprehensive test suite."""
    print("Running comprehensive blocking system test suite...")
    print("=" * 60)
    
    test_functions = [
        test_blocking_system_initialization,
        test_policy_management,
        test_default_policies,
        test_application_evaluation,
        test_system_lifecycle,
        test_override_functionality,
        test_system_status,
        test_configuration_export_import,
        test_statistics_reset,
        test_concurrent_operations
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"FAILED: {test_func.__name__} failed: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("SUCCESS: All tests passed! Blocking system is fully functional.")
    else:
        print(f"FAILED: {failed} tests failed. Please review the errors above.")
    
    return failed == 0


def interactive_demo():
    """Interactive demonstration of blocking system capabilities."""
    print("Interactive Blocking System Demo")
    print("=" * 40)
    
    system = BlockingSystem()
    
    try:
        print("1. Starting blocking system...")
        system.start()
        print(f"   System active: {system.is_active()}")
        
        print("\n2. Creating default policies...")
        system.create_default_policies()
        policies = system.list_policies()
        print(f"   Created {len(policies)} policies:")
        for policy in policies:
            print(f"   - {policy.name}: {policy.action.value}")
        
        print("\n3. Testing application evaluations...")
        test_apps = [
            ("chrome", "Google Chrome", "https://facebook.com"),
            ("firefox", "Mozilla Firefox", "https://youtube.com"),
            ("notepad", "Notepad", None),
            ("steam", "Steam", None)
        ]
        
        for app_name, window_title, url in test_apps:
            window = create_test_window_info(app_name, window_title, url)
            decision = system.evaluate_application(window)
            print(f"   {app_name}: {decision.action.value} ({decision.reason})")
        
        print("\n4. Testing override functionality...")
        success = system.request_override("steam", reason="Quick gaming session", duration_minutes=30)
        print(f"   Override request for steam: {'GRANTED' if success else 'DENIED'}")
        
        overrides = system.get_active_overrides()
        print(f"   Active overrides: {len(overrides)}")
        
        print("\n5. System status:")
        status = system.get_system_status()
        stats = status['system_statistics']
        print(f"   Evaluations: {stats['total_evaluations']}")
        print(f"   Blocks: {stats['total_blocks']}")
        print(f"   Warnings: {stats['total_warnings']}")
        print(f"   Overrides: {stats['total_overrides']}")
        print(f"   Uptime: {status['uptime_seconds']:.1f} seconds")
        
        print("\n6. Configuration export/import test...")
        config = system.export_configuration()
        print(f"   Exported configuration with {len(config['policies'])} policies")
        
        # Create new system and import
        system2 = BlockingSystem()
        system2.import_configuration(config)
        imported_policies = system2.list_policies()
        print(f"   Imported {len(imported_policies)} policies to new system")
        
        print("\nSUCCESS: Demo completed successfully!")
        
    except Exception as e:
        print(f"\nFAILED: Demo failed: {e}")
        raise
    
    finally:
        print("\n7. Stopping blocking system...")
        system.start()
        print("   System stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Focus Guard blocking system")
    parser.add_argument("--mode", choices=["quick", "comprehensive", "demo"], 
                       default="quick", help="Test mode to run")
    
    args = parser.parse_args()
    
    if args.mode == "quick":
        run_quick_test()
    elif args.mode == "comprehensive":
        run_comprehensive_test()
    elif args.mode == "demo":
        interactive_demo()
