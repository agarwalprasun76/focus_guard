#!/usr/bin/env python
"""
Focus Guard - Browser Activity Integration Demo

This script demonstrates the integration between the browser extension and
the activity tracking system by processing tab snapshots and generating activity events.

It can be used to:
1. Test the browser activity integration locally
2. Generate sample tab snapshots for development
3. Verify the activity tracking pipeline

Usage:
    # Run with default settings (uses ~/.focus_guard/snapshots)
    python scripts/demo_activity_integration.py
    
    # Specify a custom output directory
    python scripts/demo_activity_integration.py --output-dir /path/to/snapshots
    
    # Generate a sample snapshot file
    python scripts/demo_activity_integration.py --create-sample

Dependencies:
    - focus_guard package must be installed
    - Browser extension should be properly configured
"""

import os
import sys
import json
import logging
import argparse
import datetime
import traceback
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to path to allow importing modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from focus_guard.core.browser.extension.browser_activity_integration import BrowserActivityIntegration
except ImportError as e:
    print(f"Error: Failed to import required modules. Make sure focus_guard is installed.\n{str(e)}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("demo_activity_integration")


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up and return the command line argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Demonstrate browser activity integration for Focus Guard"
    )
    
    parser.add_argument(
        "--output-dir",
        default=os.path.expanduser("~/.focus_guard/snapshots"),
        help="Directory where tab snapshots are stored (default: %(default)s)"
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


def get_default_output_dir() -> str:
    """Get the default output directory for storing tab snapshots.
    
    Returns:
        str: Path to the default output directory
    """
    if os.name == "nt":  # Windows
        return os.path.join(os.environ.get("LOCALAPPDATA", os.getcwd()), "FocusGuard", "snapshots")
    else:  # Unix-like systems
        return os.path.join(os.path.expanduser("~"), ".focusguard", "snapshots")


def display_processing_results(processed_data: Dict[str, Any]) -> None:
    """Display the results of processing tab snapshots.
    
    Args:
        processed_data: Dictionary containing processed tab data
    """
    if not processed_data:
        logger.warning("No data to display")
        return
    
    print("\n" + "📊" * 20)
    print("📊 TAB SNAPSHOT PROCESSING RESULTS")
    print("📊" * 20)
    
    # Display basic statistics
    total_snapshots = len(processed_data.get('snapshots', []))
    total_tabs = sum(len(snap.get('tabs', [])) for snap in processed_data.get('snapshots', []))
    
    print(f"\n🔹 Processed {total_snapshots} snapshot(s) with {total_tabs} total tabs")
    
    # Display browser distribution
    if 'browser_stats' in processed_data:
        print("\n🌐 Browser Distribution:")
        for browser, count in processed_data['browser_stats'].items():
            print(f"  - {browser}: {count} tab(s)")
    
    # Display category breakdown
    if 'category_stats' in processed_data and processed_data['category_stats']:
        print("\n🏷️  Category Breakdown:")
        for category, count in processed_data['category_stats'].items():
            print(f"  - {category}: {count} tab(s)")
    
    # Display time statistics
    if 'time_stats' in processed_data:
        print("\n⏱️  Time Statistics:")
        stats = processed_data['time_stats']
        print(f"  - First snapshot: {stats.get('first_seen', 'N/A')}")
        print(f"  - Last snapshot: {stats.get('last_seen', 'N/A')}")
        print(f"  - Total duration: {stats.get('duration_minutes', 0):.1f} minutes")
    
    print("\n✅ Processing complete!")
    print("📊" * 20 + "\n")


def print_usage_stats(usage_stats: Dict[str, Any]) -> None:
    """Print usage statistics in a formatted way.
    
    Args:
        usage_stats: Dictionary containing usage statistics
    """
    if not usage_stats:
        logger.warning("No usage statistics to display")
        return
    
    print("\n" + "📊" * 20)
    print("📊 USAGE STATISTICS")
    print("📊" * 20)
    
    # Calculate total time
    total_time = usage_stats.get('total_time', 0)
    active_time = usage_stats.get('active_time', 0)
    
    print(f"\n⏱️  Total time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
    print(f"🖱️  Active time: {active_time:.2f} seconds ({active_time/60:.1f} minutes)")
    
    if total_time > 0:
        efficiency = (active_time / total_time) * 100 if total_time > 0 else 0
        print(f"📈 Efficiency: {efficiency:.1f}% active time")
    
    # Display category breakdown
    if "categories" in usage_stats and usage_stats["categories"]:
        print("\n🏷️  Category Breakdown:")
        categories = sorted(usage_stats["categories"].items(), 
                          key=lambda x: x[1].get('time', 0), 
                          reverse=True)
        
        for category, stats in categories:
            time_sec = stats.get('time', 0)
            time_min = time_sec / 60
            percentage = (time_sec / total_time * 100) if total_time > 0 else 0
            print(f"  - {category}: {time_sec:.1f}s ({time_min:.1f}m) - {percentage:.1f}%")
    
    print("📊" * 20 + "\n")


def main() -> int:
    """Run the browser activity integration demo.
    
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command line arguments
        parser = setup_argument_parser()
        args = parser.parse_args()
        
        # Configure logging level
        log_level = logging.DEBUG if args.verbose else logging.INFO
        logger.setLevel(log_level)
        
        logger.info("🔍 Starting Focus Guard Activity Integration Demo")
        
        # Set up output directory
        output_dir = args.output_dir
        if not output_dir:
            output_dir = get_default_output_dir()
            logger.info(f"Using default output directory: {output_dir}")
        
        # Create output directory if it doesn't exist
        try:
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"Ensured output directory exists: {output_dir}")
        except OSError as e:
            logger.error(f"❌ Failed to create output directory '{output_dir}': {e}")
            return 1
        
        # Create sample snapshot if requested
        if args.create_sample:
            try:
                sample_path = create_sample_snapshot(output_dir)
                logger.info(f"✅ Created sample snapshot at: {sample_path}")
                return 0
            except Exception as e:
                logger.error(f"❌ Failed to create sample snapshot: {e}")
                logger.debug(traceback.format_exc())
                return 1
        
        # Initialize the browser activity integration
        try:
            logger.info("🚀 Initializing browser activity integration...")
            integration = BrowserActivityIntegration(output_dir=output_dir)
            logger.debug("Successfully initialized BrowserActivityIntegration")
        except Exception as e:
            logger.error(f"❌ Failed to initialize browser activity integration: {e}")
            logger.debug(traceback.format_exc())
            return 1
        
        # Process tab snapshots
        logger.info(f"🔍 Looking for tab snapshots in: {output_dir}")
        try:
            processed_data = integration.process_tab_snapshots()
            
            if not processed_data:
                logger.warning("⚠️  No tab snapshots found or processed")
                logger.info("Try running with --create-sample to generate a test snapshot")
                return 1
                
            logger.info(f"✅ Successfully processed {len(processed_data.get('snapshots', []))} tab snapshot(s)")
            
            # Display processing results
            display_processing_results(processed_data)
            
            # Track browser usage
            logger.info("📊 Analyzing browser usage...")
            usage_stats = integration.generate_usage_statistics(processed_data)
            
            # Print usage statistics
            print_usage_stats(usage_stats)
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error processing tab snapshots: {e}")
            logger.debug(traceback.format_exc())
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Operation cancelled by user")
        return 1
    except Exception as e:
        logger.critical(f"💥 Unhandled exception: {e}")
        logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
