#!/usr/bin/env python
"""
Embedded Content Detection Demo

This script demonstrates the ability of FocusGuard to detect embedded content,
especially YouTube videos embedded on search engines like Bing and Google.

Usage:
    python demo_embedded_content.py [url]
    - If no URL is provided, the script will use sample URLs
"""

import sys
import logging
import colorama
from colorama import Fore, Style
import json

sys.path.append("../..")  # Add project root to path

from core.domain_classifier.url_resolver import EmbeddedContentAnalyzer
from core.domain_classifier.utils import (
    extract_domain, normalize_url, format_metadata, 
    get_embedded_info, get_autoplay_info
)

# Initialize colorama for colored output
colorama.init()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(levelname)s: %(message)s')


def print_section(title):
    """Print a section header with formatting"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + f"{Style.RESET_ALL}\n")


def print_result(label, value, color=Fore.GREEN):
    """Print a result with formatting"""
    print(f"{Fore.WHITE}{label}: {color}{value}{Style.RESET_ALL}")


def demonstrate_embedded_content(url):
    """Demonstrate embedded content detection for a given URL"""
    print_result("Analyzing URL", url, Fore.YELLOW)
    print_result("Domain", extract_domain(url))
    
    # Create embedded content analyzer
    analyzer = EmbeddedContentAnalyzer()
    
    # Analyze the page for embedded content
    print(f"{Fore.WHITE}Searching for embedded content...{Style.RESET_ALL}")
    
    try:
        embedded_content = analyzer.extract_embedded_content(url)
        
        if embedded_content:
            count = len(embedded_content)
            print(f"\n{Fore.GREEN}✓ Found {count} embedded content items!{Style.RESET_ALL}")
            
            # Print each embedded content item
            for i, (content_id, content) in enumerate(embedded_content.items()):
                print(f"\n{Fore.WHITE}Content #{i+1}:{Style.RESET_ALL}")
                print(f"  {Fore.YELLOW}Type: {content.get('type', 'Unknown')}{Style.RESET_ALL}")
                
                if content.get('type') == 'youtube':
                    print(f"  {Fore.GREEN}YouTube Video{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Video ID: {Fore.YELLOW}{content.get('video_id', 'Unknown')}{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Platform: {Fore.YELLOW}{content.get('platform', 'Unknown')}{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Title: {Fore.YELLOW}{content.get('title', 'Unknown')}{Style.RESET_ALL}")
                    
                    # Original embed URL
                    if 'embed_url' in content:
                        print(f"  {Fore.WHITE}Embed URL: {Fore.BLUE}{content['embed_url']}{Style.RESET_ALL}")
                    
                    # Direct link to YouTube
                    youtube_url = f"https://www.youtube.com/watch?v={content.get('video_id')}"
                    print(f"  {Fore.WHITE}Direct URL: {Fore.GREEN}{youtube_url}{Style.RESET_ALL}")
                else:
                    # Print other content types
                    for key, value in content.items():
                        if key != 'type':
                            print(f"  {Fore.WHITE}{key}: {Fore.YELLOW}{value}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}No embedded content detected.{Style.RESET_ALL}")
    
    except Exception as e:
        print(f"\n{Fore.RED}Error analyzing page: {str(e)}{Style.RESET_ALL}")


def demonstrate_autoplay_detection(url, current_video_id=None):
    """Demonstrate autoplay content detection"""
    print_result("Analyzing for autoplay", url, Fore.YELLOW)
    
    # Create embedded content analyzer
    analyzer = EmbeddedContentAnalyzer()
    
    # Analyze for autoplay content
    print(f"{Fore.WHITE}Checking for autoplay content...{Style.RESET_ALL}")
    
    try:
        autoplay_info = analyzer.detect_autoplay_content(url, current_video_id)
        
        if autoplay_info.get('has_autoplay', False):
            print(f"\n{Fore.RED}⚠ Autoplay content detected!{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Video ID: {Fore.YELLOW}{autoplay_info.get('video_id', 'Unknown')}{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Title: {Fore.YELLOW}{autoplay_info.get('title', 'Unknown')}{Style.RESET_ALL}")
            if 'url' in autoplay_info:
                print(f"  {Fore.WHITE}URL: {Fore.BLUE}{autoplay_info['url']}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.GREEN}✓ No autoplay content detected.{Style.RESET_ALL}")
    
    except Exception as e:
        print(f"\n{Fore.RED}Error detecting autoplay: {str(e)}{Style.RESET_ALL}")


def main():
    """Main function to run the demo"""
    print_section("FocusGuard Embedded Content Detection Demo")
    
    # Get URL from command line or use samples
    if len(sys.argv) > 1:
        url = sys.argv[1]
        demonstrate_embedded_content(normalize_url(url))
        
        # If it's a YouTube URL, also check for autoplay
        if "youtube.com" in url or "youtu.be" in url:
            print("\n" + "-" * 60 + "\n")
            demonstrate_autoplay_detection(url)
    else:
        # Sample URLs for demonstration
        print(f"{Fore.WHITE}Using sample URLs for demonstration.{Style.RESET_ALL}")
        print(f"{Fore.WHITE}You can also provide your own URL as an argument.{Style.RESET_ALL}\n")
        
        # Embedded content demo
        print_section("Part 1: Embedded Content Detection")
        embedded_urls = [
            "https://www.bing.com/videos/search?q=python+tutorial",
            "https://www.google.com/search?tbm=vid&q=python+programming"
        ]
        
        for i, url in enumerate(embedded_urls):
            if i > 0:
                print("\n" + "-" * 60 + "\n")
            demonstrate_embedded_content(url)
        
        # Autoplay demo
        print_section("Part 2: Autoplay Detection")
        autoplay_urls = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ")
        ]
        
        for url, video_id in autoplay_urls:
            demonstrate_autoplay_detection(url, video_id)


if __name__ == "__main__":
    main()
