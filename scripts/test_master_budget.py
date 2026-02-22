"""Test script for Master Distraction Budget feature."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from focus_guard.core.browser_v2.tab_server.domain_usage_tracker import (
    get_master_distraction_budget,
    reset_master_distraction_budget,
    MasterDistractionBudget,
    MasterDistractionBudgetConfig,
)


def test_master_budget():
    print("=" * 60)
    print("Master Distraction Budget Test")
    print("=" * 60)
    
    # Reset for clean test
    reset_master_distraction_budget()
    
    # Get fresh instance
    budget = get_master_distraction_budget()
    
    # Check initial status
    status = budget.check_budget()
    print(f"\nInitial status:")
    print(f"  Total limit: {status['total_limit_formatted']}")
    print(f"  Used: {status['total_used_formatted']}")
    print(f"  Remaining: {status['remaining_formatted']}")
    print(f"  Sites visited: {status['sites_count']}")
    print(f"  Budget exhausted: {status['budget_exhausted']}")
    
    # Test recording distraction time
    print("\n--- Recording distraction time ---")
    print("Recording 5 min on netflix.com...")
    budget.record_distraction_time("netflix.com", 300, "ENTERTAINMENT", "DISTRACTION")
    
    print("Recording 3 min on youtube.com...")
    budget.record_distraction_time("youtube.com", 180, "ENTERTAINMENT", "DISTRACTION")
    
    print("Recording 2 min on facebook.com...")
    budget.record_distraction_time("facebook.com", 120, "SOCIAL_MEDIA", "DISTRACTION")
    
    # Check updated status
    status = budget.check_budget()
    print(f"\nUpdated status:")
    print(f"  Used: {status['total_used_formatted']}")
    print(f"  Remaining: {status['remaining_formatted']}")
    print(f"  Usage percent: {status['usage_percent']}%")
    print(f"  Sites visited: {status['sites_count']}")
    print(f"  Warning: {status['warning']}")
    
    # Show sites
    print("\nSites visited today:")
    for site in status["sites_visited"]:
        print(f"  - {site['domain']}: {site['active_time_formatted']} ({site['category']})")
    
    # Test can_access_distraction
    access = budget.can_access_distraction()
    print(f"\nCan access more distractions: {access['allowed']}")
    print(f"Remaining: {access['remaining_seconds']:.0f}s")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


def test_api_endpoint():
    """Test the API endpoint."""
    print("\n" + "=" * 60)
    print("Testing API Endpoint")
    print("=" * 60)
    
    import urllib.request
    import json
    
    try:
        url = "http://127.0.0.1:58392/api/distraction/budget"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            print(f"\nAPI Response:")
            print(f"  Total limit: {data.get('total_limit_formatted')}")
            print(f"  Used: {data.get('total_used_formatted')}")
            print(f"  Remaining: {data.get('remaining_formatted')}")
            print(f"  Sites count: {data.get('sites_count')}")
            print(f"  Budget exhausted: {data.get('budget_exhausted')}")
            
            if data.get("sites_visited"):
                print("\n  Sites visited:")
                for site in data["sites_visited"]:
                    print(f"    - {site['domain']}: {site['active_time_formatted']}")
            
            print("\n✅ API endpoint working!")
    except Exception as e:
        print(f"\n⚠️ Could not reach API (server may not be running): {e}")


if __name__ == "__main__":
    test_master_budget()
    test_api_endpoint()
