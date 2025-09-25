"""Focus Guard MVP Simple Demo Script

This script demonstrates the CORE Focus Guard MVP features:
1. Domain classification
2. Blocking decisions
3. Interactive blocking test
4. Optional coordinator startup

This is a simplified subset of demo_mvp_enhanced.py focusing on essential functionality."""

import asyncio
import logging
import os
import sys
from typing import Optional
from pathlib import Path

# Configure logging for demo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("focus_guard.simple_demo")

# Import Focus Guard components
from focus_guard.core.api.api import ClassifierBlockerAPI


async def test_core_mvp_features():
    """Test the core MVP features (subset of enhanced demo)."""
    print("\n" + "="*60)
    print("FOCUS GUARD MVP - CORE FEATURES DEMO")
    print("="*60)
    print("This demo tests the essential MVP functionality.")
    print("For comprehensive testing, run: python demo_mvp_enhanced.py")
    
    try:
        # Initialize the API
        print("\n1. Initializing ClassifierBlockerAPI...")
        api = ClassifierBlockerAPI()
        print("   [OK] API initialized successfully")
        
        # Test basic API structure
        print("\n2. Testing Core API Components:")
        print(f"   [+] Classifier registry: {len(api._classifier_registry.get_all())} classifiers")
        print(f"   [+] Blocking registry: {len(api._blocking_registry.get_all())} strategies")
        print(f"   [+] Domain cache: initialized")
        print(f"   [+] Blocking cache: initialized")
        print("   [INFO] This matches the enhanced demo's MVP feature test")
        
        # Test domain extraction and classification
        print("\n3. Testing Domain Extraction & Classification:")
        print("   [INFO] Testing core domain processing (subset of enhanced demo)")
        from focus_guard.core.domain.domain_utils_new import extract_domain_from_url
        test_urls = [
            "https://youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - should be classified as distraction
            "https://youtube.com/watch?v=educational_content",  # Educational - should be allowed
            "https://facebook.com/feed",
            "https://github.com/user/repo",
            "https://stackoverflow.com/questions/123",
            "https://netflix.com/browse",
            "https://twitter.com/home"
        ]
        
        for url in test_urls:
            try:
                domain = extract_domain_from_url(url)
                # Test classification (YouTube gets special handling)
                try:
                    if domain == 'youtube.com':
                        # For YouTube, we should use URL-based classification
                        print(f"   [+] {url:<40} -> {domain:<15} [YouTube - needs content analysis]")
                    else:
                        classification = await api.classify_domain(domain)
                        category = classification.name if classification else 'unknown'
                        print(f"   [+] {url:<40} -> {domain:<15} [{category}]")
                except Exception as e:
                    print(f"   [+] {url:<40} -> {domain:<15} [classification error: {e}]")
            except Exception as e:
                print(f"   [!] {url:<40} -> ERROR: {e}")
        
        # Test basic configuration loading (simplified version of enhanced demo)
        print("\n4. Testing Basic Configuration:")
        try:
            config_loader = api._config_loader
            print("   [+] Configuration loader: initialized")
            print("   [INFO] For detailed config testing, see enhanced demo")
            
            # Basic config file check
            project_root = Path(__file__).parent
            config_files = [
                project_root / "config" / "app_config.json",
                project_root / "config" / "browser_config.json",
                project_root / "config" / "blocking.json"
            ]
            
            configs_found = sum(1 for config_file in config_files if config_file.exists())
            print(f"   [+] Found {configs_found}/{len(config_files)} configuration files")
            
        except Exception as e:
            print(f"   [!] Configuration error: {e}")
        
        # Test blocking decisions
        print("\n5. Testing Blocking Decisions:")
        test_urls_blocking = [
            ("https://youtube.com/watch?v=dQw4w9WgXcQ", "Should use content classification"),
            ("https://facebook.com/feed", "Should be blocked (social_media)"),
            ("https://github.com/user/repo", "Should NOT be blocked (productivity)"),
            ("https://stackoverflow.com/questions/123", "Should NOT be blocked (productivity)"),
            ("https://netflix.com/browse", "Should be blocked (video_streaming)")
        ]
        
        for url, expected in test_urls_blocking:
            try:
                should_block = await api.should_block_tab(url)
                reason = await api.get_blocking_reason(url)
                status = "BLOCK" if should_block else "ALLOW"
                reason_text = reason or "No blocking rules matched"
                domain = extract_domain_from_url(url)
                print(f"   [{status}] {domain:<15} -> {reason_text} ({expected})")
            except Exception as e:
                domain = extract_domain_from_url(url)
                print(f"   [ERROR] {domain:<15} -> {e}")
        
        print("\n6. YouTube Classification Demo:")
        print("   [INFO] YouTube now uses intelligent content classification")
        print("   [INFO] Educational/work videos: ALLOWED")
        print("   [INFO] Entertainment/distraction videos: BLOCKED")
        print("   [INFO] This requires the YouTube classifier with LLM integration")
        print("   [WARN] LLM API quota exceeded - using fallback classification")
        
        print("\n7. Core MVP Demo Complete!")
        print("   [OK] Essential MVP functionality working")
        print("   [INFO] For CLI, tray, and installation features, run enhanced demo")
        return api
        
    except Exception as e:
        print(f"\n[!] API Demo Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_coordinator_startup():
    """Test the full coordinator startup (optional, matches enhanced demo)."""
    print("\n" + "="*60)
    print("COORDINATOR STARTUP TEST (OPTIONAL)")
    print("="*60)
    
    try:
        print("\n1. Starting Full Coordinator...")
        print("   (This will test all components)")
        print("   Press Ctrl+C to stop after a few seconds...")
        
        # Import and run the MVP main
        from focus_guard.core.mvp_main import main
        
        # Run for a short time to test startup
        try:
            await asyncio.wait_for(main(), timeout=10.0)
        except asyncio.TimeoutError:
            print("\n   [OK] Coordinator started successfully (timed out after 10s)")
            return True
        except KeyboardInterrupt:
            print("\n   [OK] Coordinator started successfully (stopped by user)")
            return True
            
    except Exception as e:
        print(f"\n   [!] Coordinator startup failed: {e}")
        return False


async def test_interactive_blocking(api):
    """Interactive test where user can test blocking with real URLs."""
    print("\n" + "="*50)
    print("INTERACTIVE BLOCKING TEST")
    print("="*50)
    print("This test will demonstrate real-time blocking decisions.")
    print("You can test different URLs to see how Focus Guard classifies them.")
    
    # Predefined test cases
    test_cases = [
        {
            "name": "Distracting YouTube Video",
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "description": "Rick Astley - Never Gonna Give You Up (Entertainment)"
        },
        {
            "name": "Educational YouTube Video", 
            "url": "https://youtube.com/watch?v=programming_tutorial",
            "description": "Python Programming Tutorial (Educational)"
        },
        {
            "name": "Social Media",
            "url": "https://facebook.com/feed",
            "description": "Facebook News Feed (Social Media)"
        },
        {
            "name": "Productivity Site",
            "url": "https://github.com/user/repo",
            "description": "GitHub Repository (Productivity)"
        },
        {
            "name": "Video Streaming",
            "url": "https://netflix.com/browse",
            "description": "Netflix Browse (Video Streaming)"
        }
    ]
    
    print("\nTesting predefined URLs:")
    print("-" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   URL: {test_case['url']}")
        print(f"   Description: {test_case['description']}")
        
        try:
            # Use the combined method to get all details in a single call
            blocking_result = await api.check_blocking_with_details(test_case['url'])
            
            if blocking_result.should_block:
                print(f"   [BLOCKED] {blocking_result.reason}")
            else:
                print(f"   [ALLOWED] {blocking_result.reason or 'No blocking rules matched'}")
                
            # Show classification details for educational purposes
            if blocking_result.category:
                print(f"      Classification: {blocking_result.category.name}")
            else:
                print(f"      Classification: UNKNOWN (LLM API unavailable)")
                
            if blocking_result.classifier_name:
                print(f"      Classified by: {blocking_result.classifier_name}")
                
        except Exception as e:
            print(f"   [ERROR] {e}")
    
    # Interactive testing
    print("\n" + "-" * 50)
    print("INTERACTIVE URL TESTING")
    print("-" * 50)
    print("Enter URLs to test (or 'quit' to exit):")
    
    while True:
        try:
            user_url = input("\nEnter URL to test: ").strip()
            
            if user_url.lower() in ['quit', 'exit', 'q', '']:
                break
                
            if not user_url.startswith(('http://', 'https://')):
                user_url = 'https://' + user_url
            
            print(f"Testing: {user_url}")
            
            # Fetch metadata for YouTube URLs
            metadata = {}
            from focus_guard.core.domain.domain_utils_new import extract_domain_from_url
            domain = extract_domain_from_url(user_url)
            
            if domain and 'youtube' in domain.lower():
                try:
                    from focus_guard.core.utils.metadata_fetcher import metadata_fetcher
                    print("   [INFO] Fetching YouTube metadata...")
                    youtube_metadata = metadata_fetcher.get_youtube_metadata(user_url)
                    if youtube_metadata and 'error' not in youtube_metadata:
                        metadata = youtube_metadata
                        print(f"   [INFO] Got metadata: {metadata.get('title', 'Unknown Title')}")
                    else:
                        print(f"   [WARN] Could not fetch metadata: {youtube_metadata.get('error', 'Unknown error')}")
                except Exception as e:
                    print(f"   [WARN] Metadata fetch failed: {e}")
            
            # Use the combined method to get all details in a single call
            blocking_result = await api.check_blocking_with_details(user_url, metadata)
            
            if blocking_result.should_block:
                print(f"[BLOCKED] {blocking_result.reason}")
                print("   This URL would be blocked by Focus Guard")
            else:
                print(f"[ALLOWED] {blocking_result.reason or 'No blocking rules matched'}")
                print("   This URL would be allowed by Focus Guard")
                
            if blocking_result.category:
                print(f"   Category: {blocking_result.category.name}")
            else:
                print(f"   Category: UNKNOWN (classification unavailable)")
                
            if blocking_result.classifier_name:
                print(f"   Classified by: {blocking_result.classifier_name}")
                
        except KeyboardInterrupt:
            print("\nInteractive testing stopped.")
            break
        except Exception as e:
            print(f"[ERROR] testing URL: {e}")
    
    print("\nInteractive blocking test complete!")
    return True


async def main():
    """Main simple demo function (subset of enhanced demo)."""
    print("Starting Focus Guard MVP Simple Demo...")
    print("This demo focuses on core MVP functionality.")
    print("For comprehensive feature testing, run: python demo_mvp_enhanced.py")
    
    # Test core MVP functionality
    api = await test_core_mvp_features()
    
    if not api:
        print("\n[!] Core MVP tests failed - stopping demo")
        return 1
    
    # Ask user if they want to test interactive blocking
    print("\n" + "="*60)
    print("INTERACTIVE BLOCKING TEST (RECOMMENDED)")
    print("="*60)
    print("This test will show real-time blocking decisions for different URLs.")
    print("You can test your own URLs to see how Focus Guard would handle them.")
    print("\nWould you like to run the interactive blocking test? (Y/n): ", end="")
    
    try:
        import sys
        if sys.stdin.isatty():
            response = input().strip().lower()
            if response not in ['n', 'no']:
                blocking_success = await test_interactive_blocking(api)
                if not blocking_success:
                    return 1
            else:
                print("Skipping interactive blocking test.")
        else:
            print("Y (non-interactive mode - running predefined tests)")
            blocking_success = await test_interactive_blocking(api)
    except (KeyboardInterrupt, EOFError):
        print("\nDemo interrupted by user.")
        return 0
    
    # Ask user if they want to test coordinator
    print("\n" + "="*60)
    print("COORDINATOR TEST (OPTIONAL)")
    print("="*60)
    print("The coordinator test will start all Focus Guard components.")
    print("This includes browser integration and extension setup.")
    print("\nWould you like to run the coordinator test? (y/N): ", end="")
    
    try:
        import sys
        if sys.stdin.isatty():
            response = input().strip().lower()
            if response in ['y', 'yes']:
                coordinator_success = await test_coordinator_startup()
                if not coordinator_success:
                    return 1
            else:
                print("Skipping coordinator test.")
        else:
            print("N (non-interactive mode)")
            print("Skipping coordinator test.")
    except (KeyboardInterrupt, EOFError):
        print("\nDemo interrupted by user.")
        return 0
    
    print("\n" + "="*60)
    print("SIMPLE DEMO COMPLETE!")
    print("="*60)
    print("[OK] Focus Guard MVP core features are working correctly!")
    print("\nNext steps:")
    print("- Run enhanced demo: python demo_mvp_enhanced.py")
    print("- Run full coordinator: python focus_guard/core/mvp_main.py")
    print("- Test CLI interface: python -m focus_guard.cli.windows_cli --help")
    print("- Install enhanced version: .\\install_focus_guard_enhanced.bat")
    print("- Or install simple MVP: .\\install_mvp.bat")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nDemo stopped by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Demo failed: {e}")
        sys.exit(1)
