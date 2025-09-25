#!/usr/bin/env python3
"""
OpenAI Classification Demo

This script demonstrates the OpenAI-based YouTube classifier which
provides more accurate content classification using the OpenAI API.

Usage:
    python demo_openai_classification.py [url] [--model MODEL]
    - If no URL is provided, the script will use sample URLs
    - The optional --model parameter specifies which OpenAI model to use 
      (defaults to gpt-3.5-turbo)
"""

import sys
import os
import time
import json
import argparse
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List

from colorama import Fore, Back, Style, init as colorama_init

# Import classifier
from core.domain_classifier.metadata import metadata_fetcher
# Import directly from the module file with the updated path
from core.domain_classifier.classifiers.llm_classifier.openai_classifier import OpenAIYouTubeClassifier
from core.utils.text_utils import format_for_terminal_output, truncate_text, sanitize_console_output
from core.domain_classifier.url_resolver import URLResolver
from core.domain_classifier.utils import extract_domain

# Create URL resolver instance
url_resolver = URLResolver()

# Check if required packages are installed
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    print(f"{Fore.RED}OpenAI SDK not installed - please install with: pip install openai>=1.0.0{Style.RESET_ALL}")
    OPENAI_AVAILABLE = False

# Initialize colorama
colorama_init()

def print_result(label, value, color=Fore.WHITE):
    """Print a result with consistent formatting"""
    print(f"{Fore.WHITE}{label}: {color}{value}{Style.RESET_ALL}")

def print_metadata(metadata):
    """Print metadata in a nice format."""
    print("Metadata:")
    
    # Skip error and HTML fields to keep output clean
    for key, value in metadata.items():
        if key not in ['error', 'html'] and not key.startswith('_'):
            # Use different colors for different types of metadata
            color = Fore.GREEN if key in ['title', 'channel'] else \
                   Fore.YELLOW if key in ['description'] else \
                   Fore.CYAN
            
            # Create a display-friendly version of the value
            display_value = value
            
            if isinstance(display_value, str):
                # Truncate long strings
                display_value = truncate_text(display_value, 100)
                    
                # Replace newlines with spaces for cleaner display
                display_value = display_value.replace("\n", " ")
                
                # Sanitize for console output
                display_value = sanitize_console_output(display_value)
            
            print(f"  {key}: {color}{display_value}{Style.RESET_ALL}")

def print_classification_result(result):
    """Print classification result with color coding"""
    if not result:
        print(f"{Fore.RED}Classification failed{Style.RESET_ALL}")
        return
    
    # ClassificationResult object has direct properties, not dictionary access
    classification_type = result.label.lower()
    confidence = result.score  # Score is already a percentage
    reason = result.reason if result.reason else "No reason provided"
    
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
    print(f"{Fore.WHITE}Reason: {color}{reason}{Style.RESET_ALL}")
    
    # Print additional metadata if available
    if result.metadata:
        print(f"\n{Fore.WHITE}Classifier used: {Fore.CYAN}{result.metadata.get('classifier', 'Unknown')}{Style.RESET_ALL}")
        if 'model' in result.metadata:
            print(f"{Fore.WHITE}Model: {Fore.CYAN}{result.metadata['model']}{Style.RESET_ALL}")
        if 'response_time' in result.metadata:
            print(f"{Fore.WHITE}Response time: {Fore.CYAN}{result.metadata['response_time']:.2f} seconds{Style.RESET_ALL}")

def main():
    """Main demo function"""
    print(f"\n{Style.BRIGHT}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Style.BRIGHT} FocusGuard OpenAI Classification Demo{Style.RESET_ALL}")
    print(f"{Style.BRIGHT}{'=' * 80}{Style.RESET_ALL}\n")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Demo for OpenAI YouTube classification")
    parser.add_argument("url", nargs="?", help="YouTube URL to classify")
    parser.add_argument("--model", help="Explicit OpenAI model name to use (overrides model_tier)")
    parser.add_argument("--model-tier", choices=["standard", "premium", "fast"], default="standard",
                        help="Model tier to use from config (standard=gpt-3.5-turbo, premium=gpt-4o, fast=gpt-3.5-turbo-0125)")
    parser.add_argument("--api-key", help="OpenAI API key (can also use config file or OPENAI_API_KEY env var)")
    args = parser.parse_args()
    
    # Check if OpenAI is available
    if not OPENAI_AVAILABLE:
        sys.exit(1)
    
    # Look for API key from different sources (in order of precedence):
    # 1. Command line argument
    # 2. Configuration file
    # 3. Environment variable
    
    # Try to load config file
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                             "core", "domain_classifier", "llm_classifier", "config", "openai_config.json")
    config = {}
    
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                print(f"{Fore.GREEN}Loaded configuration from {config_path}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}Error loading config: {e}{Style.RESET_ALL}")
    
    # Get API key from available sources
    api_key = args.api_key or config.get("api_key", "") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print(f"{Fore.RED}No OpenAI API key found. Please either:{Style.RESET_ALL}")
        print(f"  - Add it to {config_path}")
        print(f"  - Set OPENAI_API_KEY environment variable")
        print(f"  - Provide it via --api-key command line argument")
        sys.exit(1)
    
    # Get URL from command line or prompt user
    url = args.url
    if not url:
        # Use a sample URL if none provided
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        print(f"{Fore.YELLOW}Using sample URL: {url}{Style.RESET_ALL}")
    
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
    
    print(f"\n{Fore.WHITE}Step 3: Initializing OpenAI classifier...{Style.RESET_ALL}")
    
    # Determine model info to display
    if args.model:
        model_info = f"Explicit model: {args.model}"
    else:
        model_info = f"Model tier: {args.model_tier}"
    print(f"{model_info}...")
    
    # Initialize and use OpenAI classifier
    try:
        start_time = time.time()
        classifier = OpenAIYouTubeClassifier(
            api_key=api_key, 
            model=args.model,
            model_tier=args.model_tier
        )
        init_time = time.time() - start_time
        print(f"Classifier initialized in {init_time:.2f} seconds")
        print(f"Using model: {classifier.model_name}")
        
        print(f"\n{Fore.WHITE}Step 4: Classifying content...{Style.RESET_ALL}")
        
        # Perform classification
        start_time = time.time()
        result = classifier.classify(final_url, domain, metadata=metadata)
        classification_time = time.time() - start_time
        
        # Print results
        print_classification_result(result)
        print(f"\nClassification completed in {classification_time:.2f} seconds")
        
    except Exception as e:
        print(f"{Fore.RED}Error during classification: {e}{Style.RESET_ALL}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
