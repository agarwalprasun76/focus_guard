#!/usr/bin/env python
"""
Enhanced YouTube Classification Demo

This script demonstrates the full YouTube classification pipeline with URL resolution,
embedded content detection, and metadata integration. It showcases how FocusGuard
can properly classify YouTube content even when accessed via indirect URLs like
search engines and embedded videos.

Usage:
    python demo_classification.py [url]
    - If no URL is provided, the script will use sample URLs
"""

import sys
import argparse
import json
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List

from colorama import Fore, Back, Style, init as colorama_init

# Import keyword lists for debugging
from core.domain_classifier.utils import EDUCATIONAL_KEYWORDS, ENTERTAINMENT_KEYWORDS

# Import text utilities
from core.utils.text_utils import format_for_terminal_output, truncate_text, sanitize_console_output

# Initialize colorama
colorama_init()

sys.path.append("../..")  # Add project root to path

from core.domain_classifier.url_resolver import URLResolver, EmbeddedContentAnalyzer
from core.domain_classifier.utils import (
    extract_domain, is_youtube_url, format_metadata,
    get_embedded_info, get_autoplay_info, summarize_classification
)
from core.domain_classifier.metadata import MetadataFetcher
from core.domain_classifier.classifier_registry import ClassifierRegistry
from core.domain_classifier.classifiers.youtube_classifier import YouTubeClassifier

# Configure logging
import logging
import traceback
logging.basicConfig(level=logging.DEBUG, 
                    format='%(levelname)s: %(message)s')


def print_section(title):
    """Print a section header with formatting"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + f"{Style.RESET_ALL}\n")


def print_result(label, value, color=Fore.GREEN):
    """Print a result with formatting"""
    print(f"{Fore.WHITE}{label}: {color}{value}{Style.RESET_ALL}")


def print_metadata(metadata):
    """Print metadata with color coding using text utilities"""
    if not metadata:
        print(f"{Fore.YELLOW}No metadata available{Style.RESET_ALL}")
        return {}
        
    print(f"{Fore.WHITE}Metadata:{Style.RESET_ALL}")
    formatted_metadata = {}
    
    for key, value in metadata.items():
        if key in ['error', 'html'] or key.startswith('_'):
            continue
            
        formatted_metadata[key] = value
        
        # Set color based on key type
        if key in ['title', 'channel']:
            color = Fore.CYAN
        elif key in ['tags', 'description']:
            color = Fore.YELLOW
        elif key in ['has_autoplay', 'autoplay_info']:
            color = Fore.RED
        else:
            color = Fore.WHITE
            
        # Format value for display using text utilities
        if isinstance(value, bool):
            str_value = format_for_terminal_output(value)
            color = Fore.GREEN if not value else Fore.RED if key == 'has_autoplay' else Fore.GREEN
        else:
            str_value = format_for_terminal_output(value)
            
        # For description, truncate if too long
        if key == 'description':
            str_value = truncate_text(str_value, 100, True)
            
        # Ensure output is safe for console
        str_value = sanitize_console_output(str_value)
            
        print(f"  {Fore.WHITE}{key}: {color}{str_value}{Style.RESET_ALL}")
    
    return formatted_metadata


def print_classification(classification):
    """Print classification result with nice formatting"""
    if not classification:
        print(f"{Fore.RED}Classification failed{Style.RESET_ALL}")
        return
    
    # Get a summary of the classification using the utility function    
    summary = summarize_classification(classification)
    
    # Get the classification type and confidence
    classification_type = summary.get('classification', 'unknown')
    confidence = summary.get('confidence', 0)
    
    # Determine color and icon based on classification
    if classification_type == 'useful':
        color = Fore.GREEN
        icon = "+"
    elif classification_type == 'distraction':
        color = Fore.RED
        icon = "X"
    else:
        color = Fore.YELLOW
        icon = "?"
        
    # Print classification result
    print(f"\n{color}{Style.BRIGHT}{icon} Classification: {classification_type.upper()}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Confidence: {color}{confidence:.1f}%{Style.RESET_ALL}")
    
    # Print embedded info if present
    if summary.get('embedded', False) and 'embedded_info' in summary:
        embedded_info = summary['embedded_info']
        print(f"\n{Fore.YELLOW}[Embedded Content]{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Embedded on: {Fore.YELLOW}{embedded_info.get('embedded_on_domain', 'unknown')}{Style.RESET_ALL}")
        if 'source' in embedded_info:
            print(f"  {Fore.WHITE}Source: {Fore.YELLOW}{embedded_info['source']}{Style.RESET_ALL}")
        if 'original_url' in embedded_info:
            print(f"  {Fore.WHITE}Original URL: {Fore.BLUE}{embedded_info['original_url']}{Style.RESET_ALL}")
    
    # Print autoplay info if present
    if summary.get('has_autoplay', False) and 'autoplay_info' in summary:
        autoplay_info = summary['autoplay_info']
        print(f"\n{Fore.RED}[Autoplay Content Detected]{Style.RESET_ALL}")
        if autoplay_info:
            print(f"  {Fore.WHITE}Next video: {Fore.YELLOW}{autoplay_info.get('title', 'Unknown')}{Style.RESET_ALL}")
            
    # Print classifier used
    if 'classifier' in summary:
        print(f"\n{Fore.WHITE}Classifier used: {Fore.CYAN}{summary['classifier']}{Style.RESET_ALL}")
    
    return summary


def classify_url(url):
    """Perform full classification of a URL with all enhanced features"""
    print_result("URL to classify", url, Fore.YELLOW)
    
    # Create components
    url_resolver = URLResolver()
    metadata_fetcher = MetadataFetcher()
    analyzer = EmbeddedContentAnalyzer()

    # Create and register classifiers
    classifier_registry = ClassifierRegistry()
    youtube_classifier = YouTubeClassifier()  # Uses the singleton metadata_fetcher
    classifier_registry.register(youtube_classifier)

    # Log registered classifiers
    logging.info(f"Registered {len(classifier_registry.classifiers)} classifiers for demo")
    
    try:
        print(f"\n{Fore.WHITE}Step 1: Resolving URL...{Style.RESET_ALL}")
        # Resolve URL (follow redirects)
        resolution = url_resolver.resolve_url(url)
        final_url = resolution.get('final_url', url)
        is_redirect = resolution.get('is_redirect', False)
        
        if is_redirect:
            print(f"{Fore.GREEN}URL resolved to: {final_url}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}Direct URL: {url}{Style.RESET_ALL}")
        
        # Extract domain
        domain = extract_domain(final_url)
        print(f"{Fore.WHITE}Domain: {Fore.YELLOW}{domain}{Style.RESET_ALL}")
        
        print(f"\n{Fore.WHITE}Step 2: Fetching metadata...{Style.RESET_ALL}")
        # Fetch metadata (handles redirects and embedded content)
        metadata = metadata_fetcher.get_metadata_from_url(final_url)
        
        # Check if this is embedded YouTube content
        is_embedded = metadata.get('embedded', False)
        if is_embedded:
            print(f"{Fore.GREEN}Detected embedded YouTube content on {metadata.get('embedded_on_domain', 'third-party site')}{Style.RESET_ALL}")
        
        # Print metadata
        print_metadata(metadata)
        
        print(f"\n{Fore.WHITE}Step 3: Classifying content...{Style.RESET_ALL}")
        
        # DEBUG: Check for educational keywords in metadata
        logger = logging.getLogger('demo_classification')
        
        # Convert all metadata text to lowercase for matching
        all_text = f"{metadata.get('title', '')} {metadata.get('description', '')} {metadata.get('channel', '')} {' '.join(metadata.get('tags', []))}".lower()
        
        print("\nDEBUG: Checking for educational keywords:")
        for keyword in EDUCATIONAL_KEYWORDS:
            if keyword.lower() in all_text:
                position = all_text.find(keyword.lower())
                context_start = max(0, position - 30)
                context_end = min(len(all_text), position + 30)
                context = all_text[context_start:context_end]
                print(f"   FOUND '{keyword}' at position {position}")
                print(f"   Context: ...{context}...")
        
        print("\nDEBUG: Checking for entertainment keywords:")
        for keyword in ENTERTAINMENT_KEYWORDS:
            if keyword.lower() in all_text:
                position = all_text.find(keyword.lower())
                # Only print first few matches to avoid overwhelming output
                if ENTERTAINMENT_KEYWORDS.index(keyword) < 5:  
                    context_start = max(0, position - 30)
                    context_end = min(len(all_text), position + 30)
                    context = all_text[context_start:context_end]
                    print(f"   FOUND '{keyword}' at position {position}")
                    print(f"   Context: ...{context}...")
        
        # Count matches
        edu_matches = [keyword for keyword in EDUCATIONAL_KEYWORDS if keyword.lower() in all_text]
        ent_matches = [keyword for keyword in ENTERTAINMENT_KEYWORDS if keyword.lower() in all_text]
        print(f"\nDEBUG: Found {len(edu_matches)} educational keywords: {edu_matches}")
        print(f"DEBUG: Found {len(ent_matches)} entertainment keywords: {ent_matches}\n")
        
        # Classify the URL
        classification = classifier_registry.classify(final_url, domain, None, metadata)
        
        # Print classification results
        print_classification(classification)
        
        return classification
    except Exception as e:
        print(f"{Fore.RED}Error resolving URL: {str(e)}{Style.RESET_ALL}")
        import traceback
        print("\nDETAILED TRACEBACK:")
        traceback.print_exc()
        print("\nEND TRACEBACK\n")
    # Fetch metadata (handles redirects and embedded content)
    metadata = metadata_fetcher.get_metadata_from_url(final_url)
    
    # Check if this is embedded YouTube content
    is_embedded = metadata.get('embedded', False)
    if is_embedded:
        print(f"{Fore.GREEN}✓ Detected embedded YouTube content on {metadata.get('embedded_on_domain', 'third-party site')}{Style.RESET_ALL}")
    
    # Print metadata
    print_metadata(metadata)
    
    print(f"\n{Fore.WHITE}Step 3: Classifying content...{Style.RESET_ALL}")
    # Classify the URL
    classification = classifier_registry.classify(final_url, domain, None, metadata)
    
    # Print classification results
    print_classification(classification)
    
    return classification


def main():
    """Main function to run the demo"""
    print_section("FocusGuard Enhanced Classification Demo")
    
    # Get URL from command line or use samples
    if len(sys.argv) > 1:
        url = sys.argv[1]
        classify_url(url)
    else:
        # Sample URLs for demonstration
        print(f"{Fore.WHITE}Using sample URLs for demonstration.{Style.RESET_ALL}")
        print(f"{Fore.WHITE}You can also provide your own URL as an argument.{Style.RESET_ALL}\n")
        
        urls = [
            # Direct YouTube URL
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            
            # YouTube short URL (redirect)
            "https://youtu.be/dQw4w9WgXcQ",
            
            # Bing video search result with embedded YouTube
            "https://www.bing.com/videos/search?q=python+tutorial",
            
            # Google video search result with embedded YouTube
            "https://www.google.com/search?tbm=vid&q=python+programming",
            
            # Educational YouTube content
            "https://www.youtube.com/watch?v=rfscVS0vtbw"  # Python tutorial
        ]
        
        for i, url in enumerate(urls):
            if i > 0:
                print("\n" + "-" * 60 + "\n")
            classify_url(url)


if __name__ == "__main__":
    main()
