"""Test script to verify classification-based blocking integration.

Tests that:
1. ClassificationBlocker works correctly in isolation
2. The blocking_checker in runner.py integrates classification
3. /api/should_block returns correct results for Netflix vs Khan Academy
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_classification_blocker_direct():
    """Test ClassificationBlocker directly."""
    print("\n=== Test 1: ClassificationBlocker Direct ===")
    
    from focus_guard.core.browser_v2.tab_server.classification_blocker import (
        get_classification_blocker,
        ClassificationBlocker,
    )
    
    blocker = get_classification_blocker()
    
    # Test Netflix (should be blocked - ENTERTAINMENT)
    print("\nTesting netflix.com...")
    decision = blocker.check_blocking("https://www.netflix.com/browse", "netflix.com")
    print(f"  should_block: {decision.should_block}")
    print(f"  reason: {decision.reason}")
    assert decision.should_block, "Netflix should be blocked!"
    
    # Test Khan Academy (should be allowed - EDUCATION)
    print("\nTesting khanacademy.org...")
    decision = blocker.check_blocking("https://www.khanacademy.org/math", "khanacademy.org")
    print(f"  should_block: {decision.should_block}")
    print(f"  reason: {decision.reason}")
    assert not decision.should_block, "Khan Academy should NOT be blocked!"
    
    # Test YouTube (should be blocked - ENTERTAINMENT)
    print("\nTesting youtube.com...")
    decision = blocker.check_blocking("https://www.youtube.com/watch?v=abc", "youtube.com")
    print(f"  should_block: {decision.should_block}")
    print(f"  reason: {decision.reason}")
    
    # Test GitHub (should be allowed - PRODUCTIVITY)
    print("\nTesting github.com...")
    decision = blocker.check_blocking("https://github.com/user/repo", "github.com")
    print(f"  should_block: {decision.should_block}")
    print(f"  reason: {decision.reason}")
    
    print("\n✅ ClassificationBlocker direct test passed!")


def test_blocking_manager_integration():
    """Test that BlockingManager uses the external checker."""
    print("\n=== Test 2: BlockingManager Integration ===")
    
    from focus_guard.core.browser_v2.tab_server.blocking import get_blocking_manager
    from focus_guard.core.browser_v2.tab_server.classification_blocker import (
        setup_classification_blocking,
    )
    
    # Set up classification blocking
    setup_classification_blocking()
    
    blocking_manager = get_blocking_manager()
    
    # Verify external checker is set
    print(f"\nExternal checker set: {blocking_manager._external_checker is not None}")
    assert blocking_manager._external_checker is not None, "External checker should be set!"
    
    # Test through BlockingManager
    print("\nTesting netflix.com through BlockingManager...")
    decision = blocking_manager.should_block("https://www.netflix.com/browse", "netflix.com")
    print(f"  should_block: {decision.should_block}")
    print(f"  reason: {decision.reason}")
    assert decision.should_block, "Netflix should be blocked through BlockingManager!"
    
    print("\nTesting khanacademy.org through BlockingManager...")
    decision = blocking_manager.should_block("https://www.khanacademy.org/math", "khanacademy.org")
    print(f"  should_block: {decision.should_block}")
    assert not decision.should_block, "Khan Academy should NOT be blocked!"
    
    print("\n✅ BlockingManager integration test passed!")


def test_runner_blocking_checker():
    """Test that the runner creates a blocking_checker that uses classification."""
    print("\n=== Test 3: Runner Blocking Checker ===")
    
    # This simulates what happens in runner.py
    from focus_guard.core.browser_v2.tab_server.classification_blocker import (
        setup_classification_blocking,
        get_classification_blocker,
    )
    from focus_guard.core.browser_v2.tab_server.blocking import get_blocking_manager
    
    # Set up classification (as runner.py does)
    setup_classification_blocking()
    classification_blocker = get_classification_blocker()
    blocking = get_blocking_manager()
    
    # Simulate the blocking_checker function from runner.py (in-memory path)
    def blocking_checker(url: str, domain: str):
        return blocking.should_block(url, domain)
    
    # Test
    print("\nTesting netflix.com through simulated blocking_checker...")
    decision = blocking_checker("https://www.netflix.com/browse", "netflix.com")
    print(f"  should_block: {decision.should_block}")
    print(f"  reason: {decision.reason}")
    assert decision.should_block, "Netflix should be blocked!"
    
    print("\n✅ Runner blocking checker test passed!")


def test_api_endpoint_simulation():
    """Simulate what /api/should_block does."""
    print("\n=== Test 4: API Endpoint Simulation ===")
    
    from focus_guard.core.browser_v2.tab_server.classification_blocker import (
        setup_classification_blocking,
        get_classification_blocker,
    )
    from focus_guard.core.browser_v2.tab_server.blocking import get_blocking_manager
    
    # Reset and set up fresh
    blocking = get_blocking_manager()
    blocking.clear_cache()
    setup_classification_blocking()
    
    # Simulate what TabServerContext.check_blocking does
    def check_blocking(url: str, domain: str):
        return blocking.should_block(url, domain)
    
    # Test Netflix
    print("\nSimulating /api/should_block?url=https://netflix.com&domain=netflix.com")
    decision = check_blocking("https://netflix.com", "netflix.com")
    result = {
        "should_block": decision.should_block,
        "reason": decision.reason,
    }
    print(f"  Response: {result}")
    assert result["should_block"], "Netflix should be blocked!"
    
    # Test Khan Academy
    print("\nSimulating /api/should_block?url=https://khanacademy.org&domain=khanacademy.org")
    decision = check_blocking("https://khanacademy.org", "khanacademy.org")
    result = {
        "should_block": decision.should_block,
        "reason": decision.reason,
    }
    print(f"  Response: {result}")
    assert not result["should_block"], "Khan Academy should NOT be blocked!"
    
    print("\n✅ API endpoint simulation test passed!")


def main():
    print("=" * 60)
    print("Classification-Based Blocking Integration Tests")
    print("=" * 60)
    
    try:
        test_classification_blocker_direct()
        test_blocking_manager_integration()
        test_runner_blocking_checker()
        test_api_endpoint_simulation()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
