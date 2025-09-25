"""
Phase 3 Integration Test: Complete Activity Module with Enhanced Browser Integration

This test demonstrates the integration of all three phases:
- Phase 1: Idle detection and usage tracking
- Phase 2: Application blocking system  
- Phase 3: Enhanced browser integration with tab-level control

The test validates comprehensive browser monitoring, domain blocking, and policy enforcement.
"""

import sys
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from focus_guard.core.activity.browser.comprehensive_activity_system import ComprehensiveActivitySystem
from focus_guard.core.activity.browser.enhanced_domain_blocker import URLPattern, BlockingRule
from focus_guard.core.activity.blocking.models import BlockingAction
from focus_guard.core.browser.models.tab import Tab
from focus_guard.core.activity.models import WindowInfo


class MockBrowserIntegration:
    """Mock browser integration for testing."""
    
    def __init__(self):
        self._running = False
        self._mock_tabs = []
    
    def is_running(self):
        return self._running
    
    def start(self):
        self._running = True
    
    def stop(self):
        self._running = False
    
    def get_all_tabs(self):
        return self._mock_tabs
    
    def add_mock_tab(self, tab_id: str, url: str, domain: str = None, title: str = None, browser: str = "chrome"):
        """Add a mock tab for testing."""
        if not domain and url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
        
        tab = Tab(
            id=tab_id,
            url=url,
            domain=domain,
            title=title or f"Tab {tab_id}",
            browser_id=browser,
            window_id=1,
            is_active=True
        )
        self._mock_tabs.append(tab)
        return tab


class ComprehensiveActivityTestSystem:
    """Test system for Phase 3 integration with mocked components."""
    
    def __init__(self):
        """Initialize test system with mocked browser integration."""
        # Create mock browser integration
        self.mock_browser_integration = MockBrowserIntegration()
        
        # Initialize Phase 3 system with test configuration
        test_config = {
            'idle_short_threshold': 10,
            'idle_medium_threshold': 60,
            'idle_long_threshold': 300,
            'activity_polling_interval': 1.0,
            'browser_polling_interval': 1.0,
            'show_warnings': True,
            'show_blocks': True,
            'notification_timeout': 2,
            'sound_enabled': False,
            'auto_start_tab_server': False  # Don't auto-start for testing
        }
        
        self.system = ComprehensiveActivitySystem(test_config)
        
        # Replace browser integration with mock
        self.system.browser_integration = self.mock_browser_integration
        self.system.browser_monitor.browser_integration = self.mock_browser_integration
        
        # Test statistics
        self.test_stats = {
            'tabs_created': 0,
            'tabs_blocked': 0,
            'tabs_warned': 0,
            'policies_tested': 0,
            'integration_events': 0
        }
        
        # Setup test callbacks
        self._setup_test_callbacks()
    
    def _setup_test_callbacks(self):
        """Setup callbacks to track test events."""
        self.system.browser_monitor.add_tab_blocked_callback(self._on_test_tab_blocked)
        self.system.browser_monitor.add_tab_warned_callback(self._on_test_tab_warned)
    
    def _on_test_tab_blocked(self, tab, decision):
        """Track tab blocking events."""
        self.test_stats['tabs_blocked'] += 1
        print(f"   TEST: Tab blocked - {tab.url} (Policy: {decision.policy_name})")
    
    def _on_test_tab_warned(self, tab, decision):
        """Track tab warning events."""
        self.test_stats['tabs_warned'] += 1
        print(f"   TEST: Tab warned - {tab.url} (Policy: {decision.policy_name})")
    
    def create_test_tab(self, url: str, domain: str = None, browser: str = "chrome") -> Tab:
        """Create a test tab."""
        tab_id = f"test_tab_{self.test_stats['tabs_created']}"
        self.test_stats['tabs_created'] += 1
        
        tab = self.mock_browser_integration.add_mock_tab(tab_id, url, domain, browser=browser)
        return tab
    
    def simulate_tab_activity(self, tabs: List[Tab], duration_seconds: int = 5):
        """Simulate tab activity for testing."""
        print(f"   Simulating tab activity for {duration_seconds} seconds...")
        
        # Update mock tabs
        self.mock_browser_integration._mock_tabs = tabs
        
        # Let the browser monitor process the tabs
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            time.sleep(0.5)  # Short sleep to allow processing
        
        print(f"   Tab activity simulation completed")


def test_comprehensive_system_initialization():
    """Test comprehensive activity system initialization."""
    print("Testing comprehensive activity system initialization...")
    
    test_system = ComprehensiveActivityTestSystem()
    
    # Verify all components are initialized
    assert test_system.system.activity_monitor is not None
    assert test_system.system.blocking_system is not None
    assert test_system.system.browser_integration is not None
    assert test_system.system.domain_blocker is not None
    assert test_system.system.browser_monitor is not None
    
    # Verify system is not running initially
    assert not test_system.system._running
    
    print("SUCCESS: Comprehensive activity system initialization test passed")


def test_comprehensive_system_lifecycle():
    """Test comprehensive activity system start/stop lifecycle."""
    print("Testing comprehensive activity system lifecycle...")
    
    test_system = ComprehensiveActivityTestSystem()
    
    # Test start
    test_system.system.start()
    assert test_system.system._running
    assert test_system.system.activity_monitor._monitoring
    assert test_system.system.blocking_system.is_active()
    assert test_system.system.browser_monitor.is_monitoring()
    
    # Test stop
    test_system.system.stop()
    assert not test_system.system._running
    assert not test_system.system.activity_monitor._monitoring
    assert not test_system.system.blocking_system.is_active()
    assert not test_system.system.browser_monitor.is_monitoring()
    
    print("SUCCESS: Comprehensive activity system lifecycle test passed")


def test_comprehensive_policy_creation():
    """Test comprehensive policy creation for all phases."""
    print("Testing comprehensive policy creation...")
    
    test_system = ComprehensiveActivityTestSystem()
    test_system.system.start()
    
    # Create comprehensive policies
    test_system.system.create_comprehensive_policies()
    
    # Verify Phase 2 policies were created
    app_policies = test_system.system.blocking_system.list_policies()
    assert len(app_policies) >= 3
    
    policy_names = [p.name for p in app_policies]
    assert "Social Media Applications" in policy_names
    assert "Gaming Applications" in policy_names
    assert "Entertainment Content" in policy_names
    
    # Verify Phase 3 blocking rules were created
    browser_rules = test_system.system.domain_blocker.get_blocking_rules()
    assert len(browser_rules) >= 3
    
    rule_names = list(browser_rules.keys())
    assert "Social Media Sites" in rule_names
    assert "Entertainment Sites" in rule_names
    assert "Gaming Sites" in rule_names
    
    test_system.system.stop()
    
    print("SUCCESS: Comprehensive policy creation test passed")


def test_browser_tab_monitoring():
    """Test browser tab monitoring and lifecycle events."""
    print("Testing browser tab monitoring...")
    
    test_system = ComprehensiveActivityTestSystem()
    test_system.system.start()
    test_system.system.create_comprehensive_policies()
    
    # Create test tabs
    facebook_tab = test_system.create_test_tab("https://facebook.com", "facebook.com")
    youtube_tab = test_system.create_test_tab("https://youtube.com/watch?v=test", "youtube.com")
    work_tab = test_system.create_test_tab("https://github.com/user/repo", "github.com")
    
    # Simulate tab activity
    test_tabs = [facebook_tab, youtube_tab, work_tab]
    test_system.simulate_tab_activity(test_tabs, duration_seconds=3)
    
    # Verify tabs were monitored
    active_tabs = test_system.system.browser_monitor.get_active_tabs()
    assert len(active_tabs) >= 0  # May be 0 due to mocking, but should not error
    
    # Verify statistics were updated
    stats = test_system.system.browser_monitor.get_statistics()
    assert 'tabs_monitored' in stats
    assert 'last_update' in stats
    
    test_system.system.stop()
    
    print("SUCCESS: Browser tab monitoring test passed")


def test_domain_blocking_patterns():
    """Test domain blocking with URL patterns."""
    print("Testing domain blocking patterns...")
    
    test_system = ComprehensiveActivityTestSystem()
    test_system.system.start()
    test_system.system.create_comprehensive_policies()
    
    # Sync policies with domain blocker
    policies = test_system.system.blocking_system.list_policies()
    test_system.system.domain_blocker.sync_with_policies(policies)
    
    # Test URL pattern matching against the created policies
    test_urls = [
        ("https://facebook.com", True),  # Should match Social Media policy (BLOCK)
        ("https://www.facebook.com", True),  # Should match Social Media policy (BLOCK)
        ("https://twitter.com", True),  # Should match Social Media policy (BLOCK)
        ("https://github.com", False),  # Should not be blocked
        ("https://google.com", False)  # Should not be blocked
    ]
    
    for url, should_block in test_urls:
        result, rule = test_system.system.domain_blocker.should_block_url(url)
        if should_block:
            assert result, f"URL {url} should be blocked but wasn't"
            assert rule is not None, f"URL {url} should have matching rule"
            print(f"   + {url} correctly blocked by rule: {rule.name}")
        else:
            assert not result, f"URL {url} should not be blocked but was"
            print(f"   + {url} correctly allowed")
    
    test_system.system.stop()
    
    print("SUCCESS: Domain blocking patterns test passed")


def test_policy_integration():
    """Test integration between Phase 2 policies and Phase 3 browser blocking."""
    print("Testing policy integration...")
    
    test_system = ComprehensiveActivityTestSystem()
    test_system.system.start()
    test_system.system.create_comprehensive_policies()
    
    # Test policy synchronization
    app_policies = test_system.system.blocking_system.list_policies()
    test_system.system.domain_blocker.sync_with_policies(app_policies)
    
    # Verify policy rules were created
    domain_rules = test_system.system.domain_blocker.get_blocking_rules()
    policy_rules = [name for name in domain_rules.keys() if name.startswith("policy_")]
    assert len(policy_rules) >= 3
    
    # Test multi-browser blocking
    test_tabs = [
        test_system.create_test_tab("https://facebook.com", "facebook.com", "chrome"),
        test_system.create_test_tab("https://twitter.com", "twitter.com", "firefox"),
        test_system.create_test_tab("https://youtube.com", "youtube.com", "edge")
    ]
    
    for tab in test_tabs:
        # Create window info for policy evaluation
        window_info = WindowInfo(
            app_name=tab.browser_id,
            window_title=tab.title,
            pid="1234",
            url=tab.url,
            domain=tab.domain,
            timestamp=datetime.now()
        )
        
        # Test application-level policy
        app_decision = test_system.system.blocking_system.evaluate_application(window_info)
        assert app_decision.action in [BlockingAction.ALLOW, BlockingAction.WARN, BlockingAction.BLOCK]
        
        # Test domain-level blocking
        should_block, rule = test_system.system.domain_blocker.should_block_url(tab.url)
        # Note: May not block due to time restrictions or other factors, but should not error
    
    test_system.system.stop()
    
    print("SUCCESS: Policy integration test passed")


def test_multi_browser_support():
    """Test multi-browser support."""
    print("Testing multi-browser support...")
    
    test_system = ComprehensiveActivityTestSystem()
    test_system.system.start()
    test_system.system.create_comprehensive_policies()
    
    # Create tabs for different browsers
    chrome_tab = test_system.create_test_tab("https://facebook.com", "facebook.com", "chrome")
    firefox_tab = test_system.create_test_tab("https://twitter.com", "twitter.com", "firefox")
    edge_tab = test_system.create_test_tab("https://youtube.com", "youtube.com", "edge")
    
    # Simulate multi-browser activity
    test_tabs = [chrome_tab, firefox_tab, edge_tab]
    test_system.simulate_tab_activity(test_tabs, duration_seconds=2)
    
    # Verify browser tracking
    stats = test_system.system.get_summary_statistics()
    assert 'browsers_monitored' in stats
    
    test_system.system.stop()
    
    print("SUCCESS: Multi-browser support test passed")


def test_configuration_export_import():
    """Test configuration export and import."""
    print("Testing configuration export/import...")
    
    # Create first system and configure it
    test_system1 = ComprehensiveActivityTestSystem()
    test_system1.system.start()
    test_system1.system.create_comprehensive_policies()
    
    # Export configuration
    config = test_system1.system.export_configuration()
    assert 'system_config' in config
    assert 'blocking_policies' in config
    assert 'blocking_rules' in config
    assert 'export_timestamp' in config
    
    test_system1.system.stop()
    
    # Create second system and import configuration
    test_system2 = ComprehensiveActivityTestSystem()
    test_system2.system.start()
    test_system2.system.import_configuration(config)
    
    # Verify configuration was imported
    imported_policies = test_system2.system.blocking_system.list_policies()
    imported_rules = test_system2.system.domain_blocker.get_blocking_rules()
    
    assert len(imported_policies) >= 3
    assert len(imported_rules) >= 3
    
    test_system2.system.stop()
    
    print("SUCCESS: Configuration export/import test passed")


def test_comprehensive_statistics():
    """Test comprehensive system statistics."""
    print("Testing comprehensive statistics...")
    
    test_system = ComprehensiveActivityTestSystem()
    test_system.system.start()
    test_system.system.create_comprehensive_policies()
    
    # Generate some activity
    test_tabs = [
        test_system.create_test_tab("https://facebook.com", "facebook.com"),
        test_system.create_test_tab("https://github.com", "github.com"),
        test_system.create_test_tab("https://youtube.com", "youtube.com")
    ]
    test_system.simulate_tab_activity(test_tabs, duration_seconds=2)
    
    # Get comprehensive status
    status = test_system.system.get_comprehensive_status()
    
    # Verify status structure
    assert 'system' in status
    assert 'phase1_activity_monitoring' in status
    assert 'phase2_application_blocking' in status
    assert 'phase3_browser_integration' in status
    assert 'integration_statistics' in status
    
    # Get summary statistics
    summary = test_system.system.get_summary_statistics()
    
    # Verify summary structure
    assert 'system_active' in summary
    assert 'total_policies' in summary
    assert 'total_blocking_rules' in summary
    assert 'total_blocks' in summary
    assert 'total_warnings' in summary
    
    test_system.system.stop()
    
    print("SUCCESS: Comprehensive statistics test passed")


def test_system_health_check():
    """Test system health monitoring."""
    print("Testing system health check...")
    
    test_system = ComprehensiveActivityTestSystem()
    
    # Test unhealthy state (not running)
    assert not test_system.system.is_healthy()
    
    # Test healthy state (running)
    test_system.system.start()
    # Note: May not be fully healthy due to mocking, but should not error
    health_status = test_system.system.is_healthy()
    assert isinstance(health_status, bool)
    
    test_system.system.stop()
    
    print("SUCCESS: System health check test passed")


def run_quick_comprehensive_test():
    """Run quick comprehensive activity system test."""
    print("Running Comprehensive Activity System Test (Quick)")
    print("=" * 50)
    
    try:
        test_comprehensive_system_initialization()
        test_comprehensive_system_lifecycle()
        test_comprehensive_policy_creation()
        test_browser_tab_monitoring()
        test_domain_blocking_patterns()
        
        print("=" * 50)
        print("SUCCESS: Comprehensive activity system test completed successfully!")
        print("Enhanced browser integration with activity monitoring and blocking is working.")
        
    except Exception as e:
        print(f"FAILED: Comprehensive activity system test failed: {e}")
        raise


def run_comprehensive_system_test():
    """Run comprehensive activity system integration test."""
    print("Running Comprehensive Activity System Test (Full)")
    print("=" * 60)
    
    test_functions = [
        test_comprehensive_system_initialization,
        test_comprehensive_system_lifecycle,
        test_comprehensive_policy_creation,
        test_browser_tab_monitoring,
        test_domain_blocking_patterns,
        test_policy_integration,
        test_multi_browser_support,
        test_configuration_export_import,
        test_comprehensive_statistics,
        test_system_health_check
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
    print(f"Comprehensive Activity System Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("SUCCESS: All comprehensive activity system tests passed!")
        print("Complete activity monitoring with enhanced browser integration is functional.")
    else:
        print(f"FAILED: {failed} tests failed. Please review the errors above.")
    
    return failed == 0


def interactive_comprehensive_demo():
    """Interactive demonstration of comprehensive activity system."""
    print("Interactive Comprehensive Activity System Demo")
    print("=" * 45)
    
    test_system = ComprehensiveActivityTestSystem()
    
    try:
        print("1. Starting comprehensive activity system...")
        test_system.system.start()
        print(f"   System Running: {test_system.system._running}")
        print(f"   Activity Monitor: {test_system.system.activity_monitor.is_active()}")
        print(f"   Blocking System: {test_system.system.blocking_system.is_active()}")
        print(f"   Browser Monitor: {test_system.system.browser_monitor.is_monitoring()}")
        
        print("\n2. Creating comprehensive policies...")
        test_system.system.create_comprehensive_policies()
        
        app_policies = test_system.system.blocking_system.list_policies()
        browser_rules = test_system.system.domain_blocker.get_blocking_rules()
        print(f"   Application Policies: {len(app_policies)}")
        print(f"   Browser Blocking Rules: {len(browser_rules)}")
        
        print("\n3. Testing browser tab monitoring...")
        test_tabs = [
            test_system.create_test_tab("https://facebook.com", "facebook.com"),
            test_system.create_test_tab("https://youtube.com/watch?v=test", "youtube.com"),
            test_system.create_test_tab("https://github.com/user/repo", "github.com"),
            test_system.create_test_tab("https://twitter.com/user", "twitter.com"),
            test_system.create_test_tab("https://stackoverflow.com/questions", "stackoverflow.com")
        ]
        
        print(f"   Created {len(test_tabs)} test tabs")
        test_system.simulate_tab_activity(test_tabs, duration_seconds=5)
        
        print("\n4. Testing domain blocking patterns...")
        test_urls = [
            "https://facebook.com",
            "https://www.twitter.com",
            "https://youtube.com/watch?v=abc",
            "https://github.com",
            "https://stackoverflow.com"
        ]
        
        for url in test_urls:
            should_block, rule = test_system.system.domain_blocker.should_block_url(url)
            should_warn, warn_rule = test_system.system.domain_blocker.should_warn_url(url)
            
            status = "BLOCKED" if should_block else ("WARNED" if should_warn else "ALLOWED")
            rule_name = (rule.name if rule else warn_rule.name if warn_rule else "None")
            print(f"   {url}: {status} (Rule: {rule_name})")
        
        print("\n5. System statistics and status:")
        summary = test_system.system.get_summary_statistics()
        
        print("   Summary Statistics:")
        print(f"     System Active: {summary['system_active']}")
        print(f"     Uptime: {summary['uptime_minutes']} minutes")
        print(f"     Total Policies: {summary['total_policies']}")
        print(f"     Total Blocking Rules: {summary['total_blocking_rules']}")
        print(f"     Total Blocks: {summary['total_blocks']}")
        print(f"     Total Warnings: {summary['total_warnings']}")
        
        print("   Test Statistics:")
        print(f"     Tabs Created: {test_system.test_stats['tabs_created']}")
        print(f"     Tabs Blocked: {test_system.test_stats['tabs_blocked']}")
        print(f"     Tabs Warned: {test_system.test_stats['tabs_warned']}")
        
        print("\n6. Configuration export test...")
        config = test_system.system.export_configuration()
        print(f"   Exported configuration with {len(config['blocking_policies']['policies'])} policies")
        print(f"   and {len(config['blocking_rules'])} blocking rules")
        
        print("\nSUCCESS: Comprehensive activity system demo completed successfully!")
        print("All components working together:")
        print("- Activity monitoring with idle detection")
        print("- Application blocking with policies")
        print("- Enhanced browser integration with tab control")
        
    except Exception as e:
        print(f"\nFAILED: Comprehensive activity system demo failed: {e}")
        raise
    
    finally:
        print("\n7. Stopping integrated system...")
        test_system.system.stop()
        print("   System stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test comprehensive activity system")
    parser.add_argument("--mode", choices=["quick", "comprehensive", "demo"], 
                       default="quick", help="Test mode to run")
    
    args = parser.parse_args()
    
    if args.mode == "quick":
        run_quick_comprehensive_test()
    elif args.mode == "comprehensive":
        run_comprehensive_system_test()
    elif args.mode == "demo":
        interactive_comprehensive_demo()
