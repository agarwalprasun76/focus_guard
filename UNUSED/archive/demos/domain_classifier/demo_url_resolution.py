#!/usr/bin/env python
"""
URL Resolution Demo

This script demonstrates the URL resolution capabilities of FocusGuard, including:
1. Resolving redirects (like URL shorteners)
2. Handling multi-step redirections
3. Detecting the final destination URL

Usage:
    python demo_url_resolution.py [url]
    - If no URL is provided, the script will use sample URLs
"""

import sys
import logging
import colorama
from colorama import Fore, Style

sys.path.append("../..")  # Add project root to path

from core.domain_classifier.url_resolver import URLResolver
from core.domain_classifier.utils import (
    extract_domain, normalize_url, format_metadata,
    get_embedded_info, get_autoplay_info, summarize_classification
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


def demonstrate_url_resolution(url):
    """Demonstrate URL resolution for a given URL"""
    print_result("Original URL", url, Fore.YELLOW)
    
    # Create URL resolver
    resolver = URLResolver()
    
    # Resolve the URL
    print(f"{Fore.WHITE}Resolving URL...{Style.RESET_ALL}")
    result = resolver.resolve_url(url)
    
    # Print results
    if result.get('is_redirect', False):
        print(f"\n{Fore.GREEN}✓ Redirect detected!{Style.RESET_ALL}")
        print_result("  Final URL", result['final_url'])
        print_result("  Original domain", extract_domain(url))
        print_result("  Final domain", extract_domain(result['final_url']))
        
        # Print redirect chain
        print(f"\n{Fore.WHITE}Redirect chain:{Style.RESET_ALL}")
        for i, redirect_url in enumerate(result.get('redirect_chain', [])):
            print(f"{Fore.YELLOW}  {i+1}. {redirect_url}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  → {result['final_url']}{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}No redirect detected. URL is direct.{Style.RESET_ALL}")
        print_result("URL", result.get('final_url', url))


def main():
    """Main function to run the demo"""
    print_section("FocusGuard URL Resolution Demo")
    
    # Get URL from command line or use samples
    if len(sys.argv) > 1:
        urls = [sys.argv[1]]
    else:
        # Sample URLs for demonstration
        print(f"{Fore.WHITE}Using sample URLs for demonstration.{Style.RESET_ALL}")
        print(f"{Fore.WHITE}You can also provide your own URL as an argument.{Style.RESET_ALL}\n")
        urls = [
            "https://t.co/abcd123",  # Twitter short URL (example)
            "https://bit.ly/3XYZabc", # Bitly short URL (example)
            "https://youtu.be/dQw4w9WgXcQ",  # YouTube short URL
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Direct URL (no redirect)
        ]
    
    # Process each URL
    for i, url in enumerate(urls):
        if i > 0:
            print("\n" + "-" * 60 + "\n")
        demonstrate_url_resolution(normalize_url(url))


if __name__ == "__main__":
    main()
