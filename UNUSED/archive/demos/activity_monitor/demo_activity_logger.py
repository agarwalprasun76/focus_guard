#!/usr/bin/env python
"""
Demo script for the Activity Logger

This script demonstrates the usage of the activity logger
to monitor and log foreground application activity.
"""

import os
import sys
import time
import datetime
from pathlib import Path

# Add parent directory to path to allow imports
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.activity_monitor.activity_logger import ActivityLogger
from core.utils.text_utils import sanitize_console_output, format_for_terminal_output

def main():
    """Main function to demonstrate the activity logger."""
    print("=== FocusGuard Activity Logger Demo ===\n")
    
    # Create activity logger with 5-second interval
    logger = ActivityLogger(interval_seconds=5)
    
    # Get current log path
    log_path = logger.get_current_log_path()
    print(f"Activity will be logged to: {log_path}")
    
    # Start logging
    print("\nStarting activity logging...")
    logger.start()
    
    try:
        # Log for a specified duration
        duration = 60  # seconds
        print(f"\nLogging activity for {duration} seconds. Switch between applications to see different entries...")
        
        # Show progress
        for i in range(duration):
            if i % 5 == 0:
                sys.stdout.write(f"\rLogging... {i}/{duration} seconds")
                sys.stdout.flush()
            time.sleep(1)
        
        # Stop logging
        print("\n\nStopping activity logging...")
        logger.stop()
        
        # Display log contents
        print(f"\nLog file contents from {log_path}:\n")
        if log_path.exists():
            try:
                # Read file with errors='replace' to handle encoding issues
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    for line in lines[-20:]:  # Show last 20 entries
                        # Use text_utils to handle encoding issues
                        clean_line = sanitize_console_output(line.strip())
                        print(clean_line)
                
                print(f"\nTotal entries: {len(lines)}")
            except Exception as e:
                print(f"Error reading log file: {e}")
        else:
            print("No log file found.")
        
    except KeyboardInterrupt:
        print("\n\nLogging interrupted by user.")
        logger.stop()
    
    print("\nDemo completed.")

if __name__ == "__main__":
    main()
