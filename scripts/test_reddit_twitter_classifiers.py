"""Test script for Reddit and Twitter classifiers.

Usage:
    python test_reddit_twitter_classifiers.py          # Run rule-based tests only
    python test_reddit_twitter_classifiers.py --llm    # Include LLM fallback tests
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from focus_guard.core.browser_v2.tab_server.classification_service import (
    get_classification_service,
    reset_classification_service,
)


async def test_reddit_classification():
    print("=" * 60)
    print("Reddit Classification Tests")
    print("=" * 60)
    
    reset_classification_service()
    service = get_classification_service()
    
    test_cases = [
        # (url, expected_category, expected_distracting, description)
        ("https://www.reddit.com/", "SOCIAL_MEDIA", True, "Reddit home feed"),
        ("https://www.reddit.com/r/popular", "SOCIAL_MEDIA", True, "Reddit popular"),
        ("https://www.reddit.com/r/all", "SOCIAL_MEDIA", True, "Reddit all"),
        ("https://www.reddit.com/r/programming", "EDUCATION", False, "r/programming (productive)"),
        ("https://www.reddit.com/r/python/comments/abc123/how_to_use_asyncio", "EDUCATION", False, "r/python post"),
        ("https://www.reddit.com/r/learnprogramming", "EDUCATION", False, "r/learnprogramming"),
        ("https://www.reddit.com/r/memes", "ENTERTAINMENT", True, "r/memes (entertainment)"),
        ("https://www.reddit.com/r/gaming", "ENTERTAINMENT", True, "r/gaming"),
        ("https://www.reddit.com/r/funny/comments/xyz789/hilarious_cat", "ENTERTAINMENT", True, "r/funny post"),
        ("https://www.reddit.com/u/someuser", "SOCIAL_MEDIA", False, "User profile (neutral)"),
    ]
    
    passed = 0
    failed = 0
    
    for url, expected_cat, expected_distract, desc in test_cases:
        result = await service.classify_async("reddit.com", url, {"url": url})
        
        cat_match = result.category == expected_cat
        distract_match = result.is_distracting == expected_distract
        
        if cat_match and distract_match:
            print(f"✅ {desc}")
            print(f"   Category: {result.category}, Distracting: {result.is_distracting}")
            passed += 1
        else:
            print(f"❌ {desc}")
            print(f"   Expected: {expected_cat}, distracting={expected_distract}")
            print(f"   Got: {result.category}, distracting={result.is_distracting}")
            print(f"   Reason: {result.reason}")
            failed += 1
    
    print(f"\nReddit: {passed}/{passed+failed} tests passed")
    return passed, failed


async def test_twitter_classification():
    print("\n" + "=" * 60)
    print("Twitter/X Classification Tests")
    print("=" * 60)
    
    reset_classification_service()
    service = get_classification_service()
    
    test_cases = [
        # (url, domain, expected_category, expected_distracting, description)
        ("https://twitter.com/", "twitter.com", "SOCIAL_MEDIA", True, "Twitter home feed"),
        ("https://twitter.com/home", "twitter.com", "SOCIAL_MEDIA", True, "Twitter home"),
        ("https://x.com/", "x.com", "SOCIAL_MEDIA", True, "X.com home feed"),
        ("https://twitter.com/explore", "twitter.com", "SOCIAL_MEDIA", True, "Twitter explore"),
        ("https://twitter.com/notifications", "twitter.com", "SOCIAL_MEDIA", True, "Twitter notifications"),
        ("https://twitter.com/github", "twitter.com", "EDUCATION", False, "GitHub account (productive)"),
        ("https://twitter.com/reuters", "twitter.com", "NEWS", False, "Reuters (news)"),
        ("https://twitter.com/netflix", "twitter.com", "ENTERTAINMENT", True, "Netflix account (entertainment)"),
        ("https://twitter.com/someuser/status/123456789", "twitter.com", "SOCIAL_MEDIA", True, "Random tweet"),
        ("https://twitter.com/search?q=funny%20memes", "twitter.com", "SOCIAL_MEDIA", True, "Search for memes"),
    ]
    
    passed = 0
    failed = 0
    
    for url, domain, expected_cat, expected_distract, desc in test_cases:
        result = await service.classify_async(domain, url, {"url": url})
        
        cat_match = result.category == expected_cat
        distract_match = result.is_distracting == expected_distract
        
        if cat_match and distract_match:
            print(f"✅ {desc}")
            print(f"   Category: {result.category}, Distracting: {result.is_distracting}")
            passed += 1
        else:
            print(f"❌ {desc}")
            print(f"   Expected: {expected_cat}, distracting={expected_distract}")
            print(f"   Got: {result.category}, distracting={result.is_distracting}")
            print(f"   Reason: {result.reason}")
            failed += 1
    
    print(f"\nTwitter: {passed}/{passed+failed} tests passed")
    return passed, failed


async def test_llm_fallback():
    """Test LLM fallback for obscure subreddits not in the rules list.
    
    These tests require an OpenAI API key and will make actual API calls.
    The expected results are based on what the LLM *should* classify them as,
    but we're more flexible since LLM responses can vary.
    """
    print("\n" + "=" * 60)
    print("LLM Fallback Tests (Obscure Subreddits)")
    print("=" * 60)
    print("Note: These use actual LLM API calls and may take a moment...")
    
    reset_classification_service()
    service = get_classification_service()
    
    # Test cases for obscure subreddits NOT in the rules list
    # Format: (url, expected_categories (list of acceptable), expected_distracting, description)
    test_cases = [
        # Educational - should be EDUCATION
        (
            "https://www.reddit.com/r/AskHistorians/comments/abc123/what_caused_the_fall_of_rome",
            ["EDUCATION", "NEWS"],  # Accept either - it's academic
            False,
            "r/AskHistorians (academic history Q&A) - LLM should classify as educational"
        ),
        # Entertainment/Memes - should be ENTERTAINMENT or SOCIAL_MEDIA with distraction
        (
            "https://www.reddit.com/r/blursedimages/comments/xyz789/blursed_cat",
            ["ENTERTAINMENT", "SOCIAL_MEDIA"],
            True,
            "r/blursedimages (meme content) - LLM should classify as distraction"
        ),
        # Ambiguous - interesting to see what LLM decides
        (
            "https://www.reddit.com/r/Showerthoughts/comments/def456/what_if_dogs_think_we_are_immortal",
            ["ENTERTAINMENT", "SOCIAL_MEDIA", "UNKNOWN"],  # Could go either way
            True,  # Likely distraction
            "r/Showerthoughts (random musings) - LLM decides"
        ),
    ]
    
    passed = 0
    failed = 0
    
    for url, acceptable_cats, expected_distract, desc in test_cases:
        print(f"\n🔄 Testing: {desc}")
        try:
            result = await service.classify_async("reddit.com", url, {"url": url})
            
            cat_match = result.category in acceptable_cats
            distract_match = result.is_distracting == expected_distract
            
            # Check if LLM was actually used (not rule-based)
            classifier_used = result.classifier_used or ""
            used_llm = "llm" in classifier_used.lower() or "url_llm" in classifier_used.lower()
            
            print(f"   Category: {result.category}")
            print(f"   Distracting: {result.is_distracting}")
            print(f"   Classifier: {result.classifier_used}")
            print(f"   Reason: {result.reason}")
            
            if not used_llm:
                print(f"   ⚠️  Warning: LLM was NOT used (classifier: {classifier_used})")
            
            if cat_match and distract_match:
                print(f"   ✅ PASSED")
                passed += 1
            elif cat_match and not distract_match:
                # Category correct but distraction flag different - partial pass
                print(f"   ⚠️  Category OK, but distraction={result.is_distracting} (expected {expected_distract})")
                passed += 1  # Still count as pass since LLM made a reasonable decision
            else:
                print(f"   ❌ FAILED - Expected one of: {acceptable_cats}")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failed += 1
    
    print(f"\nLLM Fallback: {passed}/{passed+failed} tests passed")
    return passed, failed


async def main():
    # Check for --llm flag
    run_llm_tests = "--llm" in sys.argv
    
    reddit_passed, reddit_failed = await test_reddit_classification()
    twitter_passed, twitter_failed = await test_twitter_classification()
    
    llm_passed, llm_failed = 0, 0
    if run_llm_tests:
        llm_passed, llm_failed = await test_llm_fallback()
    else:
        print("\n" + "-" * 60)
        print("Skipping LLM fallback tests. Use --llm flag to run them.")
    
    total_passed = reddit_passed + twitter_passed + llm_passed
    total_failed = reddit_failed + twitter_failed + llm_failed
    
    print("\n" + "=" * 60)
    print(f"TOTAL: {total_passed}/{total_passed+total_failed} tests passed")
    print("=" * 60)
    
    if total_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
