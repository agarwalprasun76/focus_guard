#!/usr/bin/env python
"""
Demo script for the enhanced log parser that correlates browser tab activity with
foreground application activity logs.

This script demonstrates how to use the EnhancedLogParser to analyze browser tab activity
with improved accuracy by integrating with the activity monitor logs.
"""

import os
import sys
import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path to allow imports
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.browser_detection.browser_integration.enhanced_log_parser import EnhancedLogParser
from core.utils.text_utils import sanitize_console_output, format_for_terminal_output


def get_activity_log_path(date_str: Optional[str] = None) -> Path:
    """
    Get the path to the activity log file for the specified date.
    
    Args:
        date_str: Optional date string in YYYY-MM-DD format
        
    Returns:
        Path to the activity log file
    """
    if date_str is None:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
    local_appdata = os.environ.get("LOCALAPPDATA", os.getcwd())
    output_dir = Path(local_appdata) / "FocusGuard"
    return output_dir / f"activity_log_{date_str}.log"


def main():
    """Main function to demonstrate the enhanced log parser."""
    print("=== FocusGuard Enhanced Log Parser Demo ===\n")
    
    # Get today's date in YYYY-MM-DD format
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Parse command line arguments
    date_str = today
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    
    print(f"Analyzing log activity for {date_str}...")
    
    # Get the activity log path
    activity_log_path = get_activity_log_path(date_str)
    print(f"Activity log path: {activity_log_path}")
    
    # Check if activity log exists
    if not activity_log_path.exists():
        print(f"Warning: Activity log file not found at {activity_log_path}")
        print("Will analyze browser logs without activity correlation.")
        activity_log_path = None
    else:
        print(f"Activity log file found: {activity_log_path}")
        
        # Display a sample of the activity log
        print("\nActivity log sample:")
        try:
            with open(activity_log_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                for line in lines[:5]:  # Show first 5 entries
                    print(sanitize_console_output(line.strip()))
                if len(lines) > 5:
                    print("...")
        except Exception as e:
            print(f"Error reading activity log: {e}")
    
    # Initialize the enhanced log parser
    parser = EnhancedLogParser()
    
    try:
        # Analyze logs with activity correlation if available
        parser.analyze_log(date_str, str(activity_log_path) if activity_log_path else None)
        
        # Get tab activity summary
        print("\nGenerating tab activity summary...")
        tab_summary = parser.get_activity_summary(use_foreground_time=True)
        if tab_summary.empty:
            print("No tab activity found.")
        else:
            print("\n=== Tab Activity Summary (Foreground Time) ===")
            print(f"Total tabs tracked: {len(tab_summary)}")
            print("\nTop 10 tabs by foreground time:")
            
            # Display the summary with safe terminal output
            summary_str = tab_summary[['title', 'domain', 'browser', 'foreground_time_minutes', 'browser_active_time_minutes']].head(10).to_string()
            print(sanitize_console_output(summary_str))
        
        # Get domain summary
        print("\nGenerating domain activity summary...")
        domain_summary = parser.get_domain_summary(use_foreground_time=True)
        if not domain_summary.empty:
            print("\n=== Domain Activity Summary (Foreground Time) ===")
            print(f"Total domains: {len(domain_summary)}")
            print("\nTop 10 domains by foreground time:")
            
            # Display the summary with safe terminal output
            summary_str = domain_summary[['domain', 'foreground_time_minutes', 'browser_active_time_minutes', 'tab_count']].head(10).to_string()
            print(sanitize_console_output(summary_str))
            
        # Show the difference between browser active time and foreground time
        if not tab_summary.empty:
            print("\n=== Browser Active vs. Foreground Time Comparison ===")
            total_browser_active = tab_summary['browser_active_time_minutes'].sum()
            total_foreground = tab_summary['foreground_time_minutes'].sum()
            print(f"Total browser active time: {total_browser_active:.2f} minutes")
            print(f"Total foreground time: {total_foreground:.2f} minutes")
            if total_browser_active > 0:
                accuracy_improvement = ((total_browser_active - total_foreground) / total_browser_active) * 100
                print(f"Accuracy improvement: {accuracy_improvement:.2f}% reduction in estimated active time")
        
        # Get application summary
        print("\nGenerating application activity summary...")
        app_summary = parser.get_application_summary()
        if not app_summary.empty:
            print("\n=== Application Activity Summary ===")
            print(f"Total applications: {len(app_summary)}")
            print("\nTop 10 applications by total time:")
            
            # Display the summary with safe terminal output
            summary_str = app_summary[['app_name', 'total_time_minutes', 'avg_screen_percent', 'is_browser']].head(10).to_string()
            print(sanitize_console_output(summary_str))
            
            # Show non-browser applications
            non_browser_apps = app_summary[~app_summary['is_browser']]
            if not non_browser_apps.empty:
                print("\n=== Non-Browser Applications ===")
                print(f"Total non-browser applications: {len(non_browser_apps)}")
                print("\nTop 10 non-browser applications by total time:")
                
                # Display the summary with safe terminal output
                summary_str = non_browser_apps[['app_name', 'total_time_minutes', 'avg_screen_percent']].head(10).to_string()
                print(sanitize_console_output(summary_str))
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error analyzing logs: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nDemo completed.")


if __name__ == "__main__":
    main()
