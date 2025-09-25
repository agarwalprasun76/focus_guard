"""
Session monitoring demo for Focus Guard.

This script demonstrates how to use the session monitoring system
with activity logging to automatically pause and resume logging
based on user session events.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta

# Add parent directory to path to import Focus Guard modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_v2.activity.coordinator import (
    get_activity_coordinator, 
    pause_activity_logging, 
    resume_activity_logging
)
from core_v2.activity.parser import get_activity_parser
from core_v2.activity.session_adapter import (
    get_activity_session_adapter,
    start_session_monitoring,
    stop_session_monitoring
)


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


def main():
    """Main demo function."""
    setup_logging()
    logger = logging.getLogger("session_monitoring_demo")
    
    # Get the activity coordinator
    coordinator = get_activity_coordinator()
    
    # Start activity logging
    logger.info("Starting activity logging...")
    coordinator.start()
    
    # Start session monitoring
    logger.info("Starting session monitoring...")
    if start_session_monitoring():
        logger.info("Session monitoring started successfully")
    else:
        logger.warning("Failed to start session monitoring - no supported monitor available")
        logger.info("Continuing with manual pause/resume demonstration")
    
    # Demonstrate manual pause/resume (for systems without session monitoring support)
    logger.info("\n=== Manual Pause/Resume Demonstration ===")
    logger.info("Activity logging is active")
    time.sleep(5)
    
    logger.info("Manually pausing activity logging (simulating user logout)...")
    pause_activity_logging()
    logger.info("Activity logging is now paused")
    time.sleep(5)
    
    logger.info("Manually resuming activity logging (simulating user login)...")
    resume_activity_logging()
    logger.info("Activity logging is now active again")
    time.sleep(5)
    
    # Take a snapshot of current activity
    logger.info("\n=== Taking Activity Snapshot ===")
    snapshot = coordinator.log_snapshot()
    if snapshot:
        app_snapshot = snapshot.get("application")
        browser_snapshot = snapshot.get("browser")
        
        if app_snapshot:
            logger.info(f"Current application: {app_snapshot.get('app_name')} - {app_snapshot.get('window_title')}")
        
        if browser_snapshot:
            logger.info(f"Current browser tab: {browser_snapshot.get('title')} - {browser_snapshot.get('url')}")
    
    # Analyze activity logs
    logger.info("\n=== Analyzing Activity Logs ===")
    parser = get_activity_parser()
    
    # Get today's date
    today = datetime.now().date()
    
    # Parse logs for today
    logger.info(f"Parsing activity logs for {today}...")
    timeline = parser.generate_activity_timeline(str(today))
    
    if timeline:
        logger.info(f"Found {len(timeline)} timeline entries for today")
        
        # Display a sample of the timeline (up to 5 entries)
        sample_size = min(5, len(timeline))
        logger.info(f"Sample of {sample_size} timeline entries:")
        
        for i, entry in enumerate(timeline[:sample_size]):
            entry_type = entry.get("type", "unknown")
            app_name = entry.get("app_name", "unknown")
            title = entry.get("window_title", entry.get("title", "unknown"))
            timestamp = entry.get("timestamp", "unknown")
            
            logger.info(f"  {i+1}. [{entry_type}] {app_name} - {title} at {timestamp}")
        
        # Calculate app usage statistics
        logger.info("\nApplication usage statistics:")
        app_stats = parser.calculate_app_usage_stats(str(today))
        
        for app_name, duration in list(app_stats.items())[:5]:  # Show top 5
            minutes = duration / 60
            logger.info(f"  {app_name}: {minutes:.2f} minutes")
        
        # Calculate domain usage statistics
        logger.info("\nDomain usage statistics:")
        domain_stats = parser.calculate_domain_usage_stats(str(today))
        
        for domain, duration in list(domain_stats.items())[:5]:  # Show top 5
            minutes = duration / 60
            logger.info(f"  {domain}: {minutes:.2f} minutes")
    else:
        logger.info("No activity data found for today")
    
    # Clean up
    logger.info("\n=== Cleaning Up ===")
    logger.info("Stopping session monitoring...")
    stop_session_monitoring()
    
    logger.info("Stopping activity logging...")
    coordinator.stop()
    
    logger.info("Demo completed")


if __name__ == "__main__":
    main()
