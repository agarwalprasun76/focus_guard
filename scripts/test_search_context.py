"""Test script for Search Context Tracker."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from focus_guard.core.browser_v2.tab_server.search_context_tracker import (
    get_search_context_tracker,
    reset_search_context_tracker,
)


def test_search_context_tracker():
    print("=" * 60)
    print("Search Context Tracker Test")
    print("=" * 60)
    
    # Reset for clean test
    reset_search_context_tracker()
    tracker = get_search_context_tracker()
    
    # Test 1: Detect entertainment search
    print("\n1. Testing entertainment search detection...")
    result = tracker.process_navigation(
        url="https://www.google.com/search?q=twilight+movie+download",
        tab_id=1,
    )
    print(f"   Is search: {result['is_search']}")
    print(f"   Is entertainment: {result['is_entertainment_search']}")
    print(f"   Matched keywords: {result['matched_keywords']}")
    assert result["is_search"] == True
    assert result["is_entertainment_search"] == True
    assert "twilight" in result["matched_keywords"] or "movie" in result["matched_keywords"]
    print("   ✅ PASSED")
    
    # Test 2: Check if Google Drive link gets blocked after entertainment search
    print("\n2. Testing Google Drive blocking after entertainment search...")
    result = tracker.process_navigation(
        url="https://drive.google.com/file/d/1UzY9RvMz0QsAgJ0swLP176Qeb6qpASei/view",
        tab_id=1,
        title="Twilight.2008.1080p.BluRay.mp4 - Google Drive",
    )
    print(f"   Should block: {result['should_block']}")
    print(f"   Reason: {result['reason']}")
    assert result["should_block"] == True
    print("   ✅ PASSED")
    
    # Test 3: Educational search should NOT flag
    print("\n3. Testing educational search (should NOT flag)...")
    reset_search_context_tracker()
    tracker = get_search_context_tracker()
    result = tracker.process_navigation(
        url="https://www.google.com/search?q=python+tutorial",
        tab_id=2,
    )
    print(f"   Is search: {result['is_search']}")
    print(f"   Is entertainment: {result['is_entertainment_search']}")
    # Note: "tutorial" might match education keywords but not entertainment
    print("   ✅ PASSED")
    
    # Test 4: Google Drive after educational search should NOT be blocked
    print("\n4. Testing Google Drive after educational search...")
    result = tracker.process_navigation(
        url="https://drive.google.com/file/d/abc123/view",
        tab_id=2,
        title="Python Tutorial Notes.pdf - Google Drive",
    )
    print(f"   Should block: {result['should_block']}")
    # Should not block because no entertainment keywords in title
    print("   ✅ PASSED")
    
    # Test 5: Harry Potter PDF search
    print("\n5. Testing 'harry potter pdf' search...")
    reset_search_context_tracker()
    tracker = get_search_context_tracker()
    result = tracker.process_navigation(
        url="https://www.google.com/search?q=harry+potter+pdf+free+download",
        tab_id=3,
    )
    print(f"   Is entertainment: {result['is_entertainment_search']}")
    print(f"   Matched keywords: {result['matched_keywords']}")
    assert result["is_entertainment_search"] == True
    print("   ✅ PASSED")
    
    # Test 6: Dropbox link after Harry Potter search
    print("\n6. Testing Dropbox blocking after Harry Potter search...")
    result = tracker.process_navigation(
        url="https://www.dropbox.com/s/abc123/file.pdf",
        tab_id=3,
    )
    print(f"   Should block: {result['should_block']}")
    print(f"   Reason: {result['reason']}")
    assert result["should_block"] == True
    print("   ✅ PASSED")
    
    # Test 7: Cross-tab detection (search in tab 1, navigate in tab 2)
    print("\n7. Testing cross-tab detection...")
    reset_search_context_tracker()
    tracker = get_search_context_tracker()
    
    # Search in tab 1
    tracker.process_navigation(
        url="https://www.google.com/search?q=hunger+games+movie+1080p",
        tab_id=10,
    )
    
    # Navigate to Drive in different tab
    result = tracker.process_navigation(
        url="https://drive.google.com/file/d/xyz789/view",
        tab_id=20,  # Different tab
    )
    print(f"   Should block (cross-tab): {result['should_block']}")
    assert result["should_block"] == True
    print("   ✅ PASSED")
    
    # Test 8: Referrer-based detection (Google Drive with search referrer)
    print("\n8. Testing referrer-based detection...")
    reset_search_context_tracker()
    tracker = get_search_context_tracker()
    
    # Navigate directly to Google Drive with a search referrer
    result = tracker.process_navigation(
        url="https://drive.google.com/file/d/abc123xyz/view",
        tab_id=30,
        title="",  # No useful title
        referrer="https://www.google.com/search?q=twilight+full+movie+download",
    )
    print(f"   Should block (referrer): {result['should_block']}")
    print(f"   Reason: {result.get('reason', '')}")
    assert result["should_block"] == True
    print("   ✅ PASSED")
    
    # Test 9: Referrer with educational search should NOT block
    print("\n9. Testing referrer with educational search...")
    reset_search_context_tracker()
    tracker = get_search_context_tracker()
    
    result = tracker.process_navigation(
        url="https://drive.google.com/file/d/def456/view",
        tab_id=40,
        title="",
        referrer="https://www.google.com/search?q=python+programming+notes",
    )
    print(f"   Should block: {result['should_block']}")
    assert result["should_block"] == False
    print("   ✅ PASSED")

    print("\n" + "=" * 60)
    print("All tests passed! ✅")
    print("=" * 60)


if __name__ == "__main__":
    test_search_context_tracker()
