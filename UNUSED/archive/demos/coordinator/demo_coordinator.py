#!/usr/bin/env python
"""
Demo script for the FocusGuard Coordinator

This script demonstrates the usage of the FocusGuard coordinator
to manage and synchronize activity monitoring components.
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path to allow imports
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from core.utils.text_utils import sanitize_console_output, format_for_terminal_output

def main():
    """Main function to demonstrate the FocusGuard coordinator."""
    print("=== FocusGuard Coordinator Demo ===\n")
    
    # Create coordinator with 5-second interval
    coordinator = FocusGuardCoordinator(interval_seconds=5)
    
    # Display configuration
    print("Configuration:")
    print(f"- Log directory: {coordinator.log_dir}")
    print(f"- Native host path: {coordinator.native_host_path}")
    print(f"- Sampling interval: {coordinator.interval} seconds")
    
    # Start coordinator
    print("\nStarting FocusGuard coordinator...")
    coordinator.start()
    
    # Display status
    status = coordinator.get_status()
    print("\nCoordinator Status:")
    for key, value in status.items():
        print(f"- {key}: {value}")
    
    try:
        # Run for a specified duration
        duration = 60  # seconds
        print(f"\nRunning coordinator for {duration} seconds. Switch between applications to see activity logging...")
        
        # Show progress
        for i in range(duration):
            if i % 5 == 0:
                sys.stdout.write(f"\rRunning... {i}/{duration} seconds")
                sys.stdout.flush()
            time.sleep(1)
        
        # Stop coordinator
        print("\n\nStopping FocusGuard coordinator...")
        coordinator.stop()
        
        # Display activity log contents
        activity_log_path = coordinator.activity_logger.get_current_log_path()
        print(f"\nActivity log file contents from {activity_log_path}:\n")
        if activity_log_path.exists():
            try:
                # Read file with errors='replace' to handle encoding issues
                with open(activity_log_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    for line in lines[-20:]:  # Show last 20 entries
                        try:
                            # Use text_utils to handle encoding issues
                            clean_line = sanitize_console_output(line.strip())
                            print(clean_line)
                        except Exception:
                            # Fall back to simple ASCII encoding if sanitize_console_output fails
                            print(line.strip().encode('ascii', 'replace').decode('ascii'))
                
                print(f"\nTotal entries: {len(lines)}")
            except Exception as e:
                print(f"Error reading log file: {e}")
        else:
            print("No activity log file found.")
        
    except KeyboardInterrupt:
        print("\n\nCoordinator interrupted by user.")
        coordinator.stop()
    
    print("\nDemo completed.")

if __name__ == "__main__":
    main()
