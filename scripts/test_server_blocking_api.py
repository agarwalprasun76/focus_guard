"""Test the /api/should_block endpoint with a running server.

Starts the tab server, makes HTTP requests, and verifies classification-based blocking.
"""

import sys
import os
import time
import urllib.request
import urllib.error
import json
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_should_block_api():
    """Test /api/should_block endpoint."""
    from focus_guard.core.browser_v2.tab_server.runner import TabServerRunner
    
    print("=" * 60)
    print("Testing /api/should_block API Endpoint")
    print("=" * 60)
    
    # Use a different port to avoid conflicts
    port = 5001
    runner = TabServerRunner(
        host="127.0.0.1",
        port=port,
        use_persistent_blocking=True,  # Test with persistent blocking enabled
    )
    
    try:
        print(f"\nStarting server on port {port}...")
        if not runner.start():
            print(f"❌ Failed to start server: {runner.get_status().error_message}")
            return 1
        
        print("✅ Server started")
        time.sleep(1)  # Give server time to fully initialize
        
        # Test cases
        test_cases = [
            ("netflix.com", "https://www.netflix.com/browse", True, "ENTERTAINMENT"),
            ("khanacademy.org", "https://www.khanacademy.org/math", False, "EDUCATION"),
            ("youtube.com", "https://www.youtube.com/watch", True, "ENTERTAINMENT"),
            ("github.com", "https://github.com/user/repo", False, "PRODUCTIVITY"),
            ("facebook.com", "https://www.facebook.com", True, "SOCIAL_MEDIA"),
            ("stackoverflow.com", "https://stackoverflow.com/questions", False, "PRODUCTIVITY"),
        ]
        
        all_passed = True
        
        for domain, url, expected_block, category in test_cases:
            print(f"\nTesting {domain}...")
            
            api_url = f"http://127.0.0.1:{port}/api/should_block?url={urllib.parse.quote(url)}&domain={domain}"
            
            try:
                req = urllib.request.Request(api_url, method="GET")
                with urllib.request.urlopen(req, timeout=5.0) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    
                    should_block = data.get("should_block", False)
                    reason = data.get("reason", "")
                    
                    status = "✅" if should_block == expected_block else "❌"
                    print(f"  {status} should_block: {should_block} (expected: {expected_block})")
                    print(f"     reason: {reason}")
                    
                    if should_block != expected_block:
                        all_passed = False
                        print(f"     FAILED: Expected {expected_block}, got {should_block}")
                        
            except urllib.error.URLError as e:
                print(f"  ❌ Request failed: {e}")
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("✅ ALL API TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED")
        print("=" * 60)
        
        return 0 if all_passed else 1
        
    finally:
        print("\nStopping server...")
        runner.stop()
        print("Server stopped")


if __name__ == "__main__":
    import urllib.parse
    sys.exit(test_should_block_api())
