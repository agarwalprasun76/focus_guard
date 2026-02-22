"""
Quick manual test script for override functionality.

Run this to quickly test the override flow without a browser.
Usage: python quick_test.py [--domain youtube.com] [--budget 60]
"""

import argparse
import time
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from focus_guard.core.browser_v2.tab_server.domain_usage_tracker import (
    DomainUsageTracker, DomainRuleConfig, get_domain_usage_tracker
)
from focus_guard.core.browser_v2.tab_server.override_manager import (
    OverrideManager, get_override_manager
)


def format_time(seconds: float) -> str:
    """Format seconds as mm:ss."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m {secs}s"


def run_test(domain: str, budget_seconds: int, session_seconds: int):
    """Run a quick test of the override flow."""
    print(f"\n{'='*60}")
    print(f"Testing override flow for: {domain}")
    print(f"Budget: {format_time(budget_seconds)}, Session: {format_time(session_seconds)}")
    print(f"{'='*60}\n")
    
    # Get the real tracker and manager (uses actual config files)
    tracker = get_domain_usage_tracker()
    manager = get_override_manager()
    
    # Set a custom rule for testing
    rule = DomainRuleConfig(
        domain=domain,
        max_overrides_per_day=3,
        max_override_duration_seconds=session_seconds,
        max_cumulative_time_seconds=budget_seconds,
    )
    tracker.set_rule(rule)
    print(f"✓ Set rule: {session_seconds}s per session, {budget_seconds}s total budget")
    
    # Check current stats
    stats = tracker.get_daily_stats(domain)
    print(f"\nCurrent stats for {domain}:")
    print(f"  - Override count: {stats.get('override_count', 0)}")
    print(f"  - Total active time: {format_time(stats.get('total_active_seconds', 0))}")
    print(f"  - Session count: {stats.get('session_count', 0)}")
    
    # Check if can override
    can_override = tracker.check_can_override(domain)
    print(f"\nCan override: {can_override['can_override']}")
    if not can_override['can_override']:
        print(f"  Reason: {can_override.get('reason', 'Unknown')}")
        return
    
    print(f"  Remaining time: {format_time(can_override.get('remaining_time_seconds', 0))}")
    print(f"  Remaining overrides: {can_override.get('remaining_overrides', 0)}")
    
    # Request override
    print(f"\n--- Requesting override ---")
    result = manager.request_override(
        domain=domain,
        url=f"https://{domain}",
        block_reason="Test block",
        browser="test",
    )
    
    if result['granted']:
        print(f"✓ Override granted")
        print(f"  Session duration: {format_time(result.get('session_duration_seconds', 0))}")
    else:
        print(f"✗ Override denied: {result.get('message', 'Unknown')}")
        return
    
    # Start usage (simulates navigation)
    print(f"\n--- Starting usage (simulating navigation) ---")
    usage_result = manager.start_override_usage(domain, "test_tab_1")
    print(f"  Started: {usage_result.get('started', False)}")
    print(f"  Daily count: {usage_result.get('daily_count', 'N/A')}")
    
    # Simulate time passing
    print(f"\n--- Simulating {session_seconds}s of usage ---")
    tick_interval = 1  # seconds
    elapsed = 0
    
    while elapsed < session_seconds:
        tracker.tick()
        time.sleep(0.1)  # Speed up for testing (10x faster)
        elapsed += tick_interval
        
        # Check every 10 seconds
        if elapsed % 10 == 0:
            check = manager.check_override(domain)
            remaining = check.get('remaining_seconds', 0)
            effective = check.get('effective_time_used', 0)
            print(f"  [{format_time(elapsed)}] Remaining: {format_time(remaining)}, Effective used: {format_time(effective)}")
            
            if not check['has_override']:
                print(f"\n✓ Override expired after {format_time(elapsed)}")
                break
    
    # End session
    print(f"\n--- Ending session ---")
    tracker.end_session(domain)
    
    # Final stats
    stats = tracker.get_daily_stats(domain)
    print(f"\nFinal stats for {domain}:")
    print(f"  - Override count: {stats.get('override_count', 0)}")
    print(f"  - Total active time: {format_time(stats.get('total_active_seconds', 0))}")
    print(f"  - Effective time: {format_time(stats.get('effective_time_used', 0))}")
    print(f"  - Session count: {stats.get('session_count', 0)}")
    
    # Check if can still override
    can_override = tracker.check_can_override(domain)
    print(f"\nCan still override: {can_override['can_override']}")
    if can_override['can_override']:
        print(f"  Remaining time: {format_time(can_override.get('remaining_time_seconds', 0))}")


def reset_stats(domain: str):
    """Reset stats for a domain."""
    tracker = get_domain_usage_tracker()
    if domain in tracker._daily_stats:
        del tracker._daily_stats[domain]
        tracker._save_daily_stats()
        print(f"✓ Reset stats for {domain}")
    else:
        print(f"No stats to reset for {domain}")


def show_stats(domain: str = None):
    """Show current stats."""
    tracker = get_domain_usage_tracker()
    
    if domain:
        stats = tracker.get_daily_stats(domain)
        rule = tracker.get_rule(domain)
        can_override = tracker.check_can_override(domain)
        
        print(f"\n{'='*60}")
        print(f"Stats for: {domain}")
        print(f"{'='*60}")
        print(f"\nRule:")
        print(f"  - Max overrides/day: {rule.max_overrides_per_day}")
        print(f"  - Max per session: {format_time(rule.max_override_duration_seconds)}")
        print(f"  - Daily budget: {format_time(rule.max_cumulative_time_seconds)}")
        print(f"\nUsage today:")
        print(f"  - Override count: {stats.get('override_count', 0)}")
        print(f"  - Active time: {format_time(stats.get('total_active_seconds', 0))}")
        print(f"  - Effective time: {format_time(stats.get('effective_time_used', 0))}")
        print(f"  - Sessions: {stats.get('session_count', 0)}")
        print(f"\nCan override: {can_override['can_override']}")
        if can_override['can_override']:
            print(f"  - Remaining time: {format_time(can_override.get('remaining_time_seconds', 0))}")
            print(f"  - Remaining overrides: {can_override.get('remaining_overrides', 0)}")
        else:
            print(f"  - Reason: {can_override.get('reason', 'Unknown')}")
    else:
        stats = tracker.get_daily_stats()
        print(f"\n{'='*60}")
        print(f"All domain stats")
        print(f"{'='*60}")
        for d, s in stats.items():
            print(f"\n{d}:")
            print(f"  - Overrides: {s.get('override_count', 0)}")
            print(f"  - Active time: {format_time(s.get('total_active_seconds', 0))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quick test for override functionality")
    parser.add_argument("--domain", default="youtube.com", help="Domain to test")
    parser.add_argument("--budget", type=int, default=300, help="Total budget in seconds")
    parser.add_argument("--session", type=int, default=60, help="Session duration in seconds")
    parser.add_argument("--reset", action="store_true", help="Reset stats for domain")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    
    args = parser.parse_args()
    
    if args.reset:
        reset_stats(args.domain)
    elif args.stats:
        show_stats(args.domain)
    else:
        run_test(args.domain, args.budget, args.session)
