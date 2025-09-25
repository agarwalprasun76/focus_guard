#!/usr/bin/env python3
"""
LLM Classifier Demo

This script demonstrates the LLM-based YouTube classifier.
It downloads and uses a small language model (TinyLlama) to classify 
YouTube content as educational, entertainment, or neutral.

Usage:
    python demo_llm_classification.py [YouTube URL]
    
Example:
    python demo_llm_classification.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
"""

import os
import sys
import time
import argparse
from typing import Dict, Any

from colorama import Fore, Back, Style, init as colorama_init

# Import core components
from core.domain_classifier.metadata import metadata_fetcher
from core.domain_classifier.llm_classifier import LLMYouTubeClassifier
from core.utils.text_utils import format_for_terminal_output, truncate_text, sanitize_console_output
from core.domain_classifier.url_resolver import URLResolver
from core.domain_classifier.utils import extract_domain

# Create URL resolver instance
url_resolver = URLResolver()

# Check if required packages are installed
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print(f"{Fore.RED}WARNING: Required packages for LLM classification not installed!{Style.RESET_ALL}")
    print("Please install the required packages by running:")
    print("pip install -r core/domain_classifier/llm_classifier/requirements.txt")
    if "--force" not in sys.argv:
        sys.exit(1)

# Initialize colorama for colored console output
colorama_init()

def print_header():
    """Print demo header"""
    print(f"{Fore.CYAN}")
    print("=" * 80)
    print(" FocusGuard LLM-Based Classification Demo")
    print("=" * 80)
    print(f"{Style.RESET_ALL}")

def print_metadata(metadata: Dict[str, Any]):
    """Print metadata in a nicely formatted way"""
    print(f"{Fore.YELLOW}Metadata:{Style.RESET_ALL}")
    for key, value in metadata.items():
        if key in ['title', 'channel', 'categories']:
            print(f"  {key}: {sanitize_console_output(str(value))}")
        elif key == 'description':
            desc = truncate_text(value, 100)
            print(f"  {key}: {sanitize_console_output(desc)}")
        elif key == 'tags' and value:
            tags = ", ".join(value[:5]) + ("..." if len(value) > 5 else "")
            print(f"  {key}: {sanitize_console_output(tags)}")
        elif key in ['duration', 'view_count', 'upload_date']:
            print(f"  {key}: {value}")

def main():
    """Main demo function"""
    print_header()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LLM-based YouTube content classifier demo")
    parser.add_argument("url", nargs="?", help="YouTube URL to classify")
    parser.add_argument("--model", default="TinyLlama/TinyLlama-1.1B-Chat-v1.0", 
                      help="Model to use (default: TinyLlama-1.1B)")
    parser.add_argument("--force", action="store_true", 
                      help="Force run even if dependencies are missing")
    args = parser.parse_args()
    
    # Get URL from arguments or prompt
    if args.url:
        url = args.url
    else:
        url = input(f"{Fore.WHITE}URL to classify: {Style.RESET_ALL}")
    
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
        
    if not metadata:
        print(f"{Fore.RED}Error: Failed to fetch metadata for URL{Style.RESET_ALL}")
        return
    
    print_metadata(metadata)
    
    print(f"\n{Fore.WHITE}Step 3: Initializing LLM classifier...{Style.RESET_ALL}")
    if not TRANSFORMERS_AVAILABLE:
        print(f"{Fore.RED}Error: Required packages not installed{Style.RESET_ALL}")
        return
    
    try:
        # Create and initialize the classifier
        # This step downloads the model if not already downloaded
        print(f"Loading model: {args.model}...")
        start_time = time.time()
        classifier = LLMYouTubeClassifier(args.model)
        load_time = time.time() - start_time
        print(f"Model loaded in {load_time:.2f} seconds")
        
        # Classify the content
        print(f"\n{Fore.WHITE}Step 4: Classifying content...{Style.RESET_ALL}")
        if classifier.model is None:
            print(f"{Fore.YELLOW}Model not available, using fallback classification{Style.RESET_ALL}")
        
        classify_start = time.time()
        result = classifier.classify(final_url, domain, None, metadata)
        classify_time = time.time() - classify_start
        
        # Display classification result
        classification = result.get("classification", "unknown").upper()
        confidence = result.get("confidence", 0)
        reason = result.get("reason", "No reason provided")
        
        # Show results with appropriate icon and color
        if classification == "USEFUL":
            icon = "+"
            color = Fore.GREEN
        elif classification == "DISTRACTION":
            icon = "X"
            color = Fore.RED
        else:
            icon = "?"
            color = Fore.YELLOW
        
        print(f"\n{color}{icon} Classification: {classification}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Reason: {reason}{Style.RESET_ALL}")
        print(f"\nClassification completed in {classify_time:.2f} seconds")
        
    except Exception as e:
        print(f"{Fore.RED}Error during classification: {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
