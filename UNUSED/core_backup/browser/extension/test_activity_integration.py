#!/usr/bin/env python
"""
Browser Activity Integration Test

This script demonstrates the integration between the browser extension and
the activity tracking system by processing tab snapshots and generating activity events.
"""

import os
import sys
import json
import logging
import argparse
import datetime
from pathlib import Path

# Add parent directory to path to allow importing modules
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from browser_activity_integration import BrowserActivityIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("test_activity_integration")


def setup_argument_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="Test browser activity integration")
    
    parser.add_argument(
        "--output-dir",
        help="Directory where native host outputs tab snapshots"
    )
    
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="Create a sample tab snapshot for testing"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser


def create_sample_snapshot(output_dir: str) -> str:
    """
    Create a sample tab snapshot for testing.
    
    Args:
        output_dir: Directory to save the sample snapshot
        
    Returns:
        str: Path to the created sample snapshot
    """
    logger.info("Creating sample tab snapshot...")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create sample data
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    sample_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "browsers": {
            "chrome": {
                "tabs": [
                    {
                        "id": 1,
                        "windowId": 1,
                        "url": "https://github.com/",
                        "title": "GitHub: Where the world builds software",
                        "active": True,
                        "browser": "chrome"
                    },
                    {
                        "id": 2,
                        "windowId": 1,
                        "url": "https://stackoverflow.com/",
                        "title": "Stack Overflow - Where Developers Learn, Share, & Build Careers",
                        "active": False,
                        "browser": "chrome"
                    },
                    {
                        "id": 3,
                        "windowId": 1,
                        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
                        "active": False,
                        "browser": "chrome"
                    }
                ]
            },
            "firefox": {
                "tabs": [
                    {
                        "id": 1,
                        "windowId": 1,
                        "url": "https://www.wikipedia.org/",
                        "title": "Wikipedia",
                        "active": True,
                        "browser": "firefox"
                    },
                    {
                        "id": 2,
                        "windowId": 1,
                        "url": "https://twitter.com/",
                        "title": "Twitter",
                        "active": False,
                        "browser": "firefox"
                    }
                ]
            }
        }
    }
    
    # Save to file
    snapshot_path = os.path.join(output_dir, f"tabs_snapshot_{today_str}.json")
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, indent=2)
    
    logger.info(f"Sample snapshot created at {snapshot_path}")
    return snapshot_path


def main():
    """Main function."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Determine output directory
    output_dir = args.output_dir
    if not output_dir:
        if os.name == "nt":  # Windows
            output_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.getcwd()), "FocusGuard")
        else:  # Unix-like systems
            output_dir = os.path.join(os.path.expanduser("~"), ".focusguard")
    
    # Create sample snapshot if requested
    if args.create_sample:
        create_sample_snapshot(output_dir)
    
    # Create browser activity integration
    integration = BrowserActivityIntegration(output_dir=output_dir)
    
    # Process tab snapshots
    logger.info("Processing tab snapshots...")
    processed_data = integration.process_tab_snapshots()
    
    if not processed_data:
        logger.warning("No tab snapshots found or processed")
        return 1
    
    # Print summary of processed data
    logger.info("Tab snapshot processed successfully:")
    logger.info(f"  Total tabs: {processed_data.get('total_tabs', 0)}")
    logger.info(f"  Active tabs: {len(processed_data.get('active_tabs', []))}")
    logger.info(f"  Browsers: {', '.join(processed_data.get('browsers', {}).keys())}")
    logger.info(f"  Domains: {', '.join(processed_data.get('domains', {}).keys())}")
    
    # Track browser usage
    logger.info("Tracking browser usage...")
    usage_stats = integration.track_browser_usage()
    
    # Print usage statistics
    logger.info("Browser usage statistics:")
    logger.info(f"  Total tabs: {usage_stats.get('total_tabs', 0)}")
    logger.info(f"  Active tabs: {usage_stats.get('active_tabs', 0)}")
    logger.info(f"  Browsers: {', '.join(usage_stats.get('browsers', {}).keys())}")
    logger.info(f"  Domains: {', '.join(usage_stats.get('domains', {}).keys())}")
    
    if "categories" in usage_stats and usage_stats["categories"]:
        logger.info(f"  Categories: {', '.join(usage_stats.get('categories', {}).keys())}")
    
    logger.info("Integration test completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
