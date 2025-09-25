"""
Activity Logging Demo for Focus Guard.

This script demonstrates how to use the Focus Guard activity logging system,
including application and browser activity tracking, pause/resume functionality,
and activity analysis.
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import Focus Guard modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_v2.activity.coordinator import (
    get_activity_coordinator, start_coordinated_logging,
    stop_coordinated_logging, pause_activity_logging,
    resume_activity_logging, take_activity_snapshot
)
from core_v2.activity.parser import (
    get_activity_parser, get_activity_timeline,
    get_app_usage_stats, get_domain_usage_stats
)


def setup_demo_logging():
    """Set up logging for the demo."""
    import logging
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    return logging.getLogger("activity_demo")


def simulate_user_session(logger, duration_seconds=60):
    """
    Simulate a user session with activity logging.
    
    Args:
        logger: Logger instance
        duration_seconds: Duration of the simulation in seconds
    """
    # Start coordinated activity logging
    logger.info("Starting activity logging...")
    start_coordinated_logging(interval_seconds=2)
    
    # Take initial snapshot
    logger.info("Taking initial activity snapshot...")
    snapshot = take_activity_snapshot("demo_start", {"demo": True})
    logger.info(f"Initial snapshot: {json.dumps(snapshot, indent=2)}")
    
    # Simulate normal activity
    logger.info("Simulating normal activity...")
    time.sleep(10)
    
    # Take another snapshot
    snapshot = take_activity_snapshot("demo_active", {"demo": True})
    logger.info(f"Activity snapshot: {json.dumps(snapshot, indent=2)}")
    
    # Simulate user logout
    logger.info("Simulating user logout...")
    pause_activity_logging()
    time.sleep(5)
    
    # Simulate user login
    logger.info("Simulating user login...")
    resume_activity_logging()
    time.sleep(10)
    
    # Take final snapshot
    snapshot = take_activity_snapshot("demo_end", {"demo": True})
    logger.info(f"Final snapshot: {json.dumps(snapshot, indent=2)}")
    
    # Stop activity logging
    logger.info("Stopping activity logging...")
    stop_coordinated_logging()


def analyze_activity_logs(logger):
    """
    Analyze activity logs for today.
    
    Args:
        logger: Logger instance
    """
    # Get today's date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get activity parser
    parser = get_activity_parser()
    
    # Check available dates
    available_dates = parser.get_available_dates()
    logger.info(f"Available activity log dates: {available_dates}")
    
    if today in available_dates:
        # Generate activity timeline
        logger.info(f"Generating activity timeline for {today}...")
        timeline = get_activity_timeline(today)
        logger.info(f"Timeline entries: {len(timeline)}")
        
        # Print first few timeline entries
        for i, entry in enumerate(timeline[:3]):
            logger.info(f"Timeline entry {i+1}:")
            logger.info(f"  App: {entry['app_name']}")
            logger.info(f"  Duration: {entry['duration_seconds']:.2f} seconds")
            logger.info(f"  Browser: {entry['is_browser']}")
            logger.info(f"  Browser activities: {len(entry['browser_activities'])}")
        
        # Calculate app usage statistics
        logger.info(f"Calculating app usage statistics for {today}...")
        app_stats = get_app_usage_stats(today)
        
        # Print top apps
        logger.info("Top applications by usage time:")
        for app, time_spent in app_stats["top_apps"]:
            percentage = app_stats["app_percentages"][app]
            logger.info(f"  {app}: {time_spent:.2f} seconds ({percentage:.1f}%)")
        
        # Calculate domain usage statistics
        logger.info(f"Calculating domain usage statistics for {today}...")
        domain_stats = get_domain_usage_stats(today)
        
        # Print top domains
        logger.info("Top domains by usage time:")
        for domain, time_spent in domain_stats["top_domains"][:5]:
            percentage = domain_stats["domain_percentages"][domain]
            logger.info(f"  {domain}: {time_spent:.2f} seconds ({percentage:.1f}%)")
    else:
        logger.warning(f"No activity logs found for {today}")


def main():
    """Main function to run the activity logging demo."""
    logger = setup_demo_logging()
    
    logger.info("Starting Activity Logging Demo")
    logger.info("=" * 50)
    
    try:
        # Simulate user session with activity logging
        simulate_user_session(logger)
        
        # Wait a moment for logs to be written
        logger.info("Waiting for logs to be written...")
        time.sleep(2)
        
        # Analyze the activity logs
        analyze_activity_logs(logger)
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
        stop_coordinated_logging()
    except Exception as e:
        logger.exception(f"Error in demo: {e}")
        stop_coordinated_logging()
    
    logger.info("=" * 50)
    logger.info("Activity Logging Demo completed")


if __name__ == "__main__":
    main()
