#!/usr/bin/env python
"""
Demo script for the FocusGuard Log Activity Parser

This script demonstrates how to use the LogActivityParser to analyze browser tab activity
from FocusGuard debug logs and generate useful insights.
"""

import os
import sys
import datetime
import pandas as pd
from log_activity_parser import LogActivityParser
from tabulate import tabulate


def format_time(seconds):
    """Format seconds into a human-readable time string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def main():
    # Get today's date in YYYY-MM-DD format
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Parse command line arguments
    date_str = today
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    
    print(f"=== FocusGuard Log Activity Analysis for {date_str} ===\n")
    
    # Initialize parser
    parser = LogActivityParser()
    
    try:
        # Find available log files
        log_files = parser.get_log_files(date_str)
        if not log_files:
            print(f"No log files found for date: {date_str}")
            return
            
        print(f"Found log file: {os.path.basename(log_files[0])}")
        print("Analyzing tab activity...")
        
        # Analyze the log
        parser.analyze_log(date_str)
        
        # Get tab activity summary
        tab_summary = parser.get_activity_summary()
        if tab_summary.empty:
            print("No tab activity found.")
            return
            
        # Add formatted time column
        tab_summary['active_time'] = tab_summary['active_time_seconds'].apply(format_time)
        
        # Print overall statistics
        total_tabs = len(tab_summary)
        total_active_time = tab_summary['active_time_seconds'].sum()
        total_domains = tab_summary['domain'].nunique()
        
        print("\n=== OVERALL STATISTICS ===")
        print(f"Total tabs tracked: {total_tabs}")
        print(f"Total unique domains: {total_domains}")
        print(f"Total active time: {format_time(total_active_time)}")
        
        # Print top tabs by active time
        print("\n=== TOP 10 TABS BY ACTIVE TIME ===")
        top_tabs = tab_summary[['title', 'domain', 'browser', 'active_time']].head(10)
        print(tabulate(top_tabs, headers='keys', tablefmt='grid', showindex=False))
        
        # Get domain summary
        domain_summary = parser.get_domain_summary()
        if not domain_summary.empty:
            # Add formatted time column
            domain_summary['active_time'] = domain_summary['active_time_seconds'].apply(format_time)
            
            print("\n=== TOP 10 DOMAINS BY ACTIVE TIME ===")
            top_domains = domain_summary[['domain', 'tab_count', 'active_time']].head(10)
            print(tabulate(top_domains, headers='keys', tablefmt='grid', showindex=False))
            
            # Calculate percentage of time by domain
            if total_active_time > 0:
                domain_summary['percentage'] = (domain_summary['active_time_seconds'] / total_active_time * 100).round(1)
                
                print("\n=== TIME DISTRIBUTION BY DOMAIN ===")
                domain_dist = domain_summary[['domain', 'active_time', 'percentage']].head(10)
                domain_dist['percentage'] = domain_dist['percentage'].apply(lambda x: f"{x}%")
                print(tabulate(domain_dist, headers=['Domain', 'Active Time', '% of Total'], tablefmt='grid', showindex=False))
        
        # Check for potential distractions (social media, entertainment)
        distraction_domains = ['facebook.com', 'twitter.com', 'instagram.com', 'reddit.com', 
                              'youtube.com', 'netflix.com', 'tiktok.com', 'twitch.tv']
        
        distraction_df = domain_summary[domain_summary['domain'].str.contains('|'.join(distraction_domains), case=False, na=False)]
        
        if not distraction_df.empty:
            print("\n=== POTENTIAL DISTRACTIONS ===")
            distractions = distraction_df[['domain', 'active_time', 'percentage']]
            distractions['percentage'] = distractions['percentage'].apply(lambda x: f"{x}%")
            print(tabulate(distractions, headers=['Domain', 'Active Time', '% of Total'], tablefmt='grid', showindex=False))
            
            total_distraction = distraction_df['active_time_seconds'].sum()
            print(f"\nTotal time on potential distractions: {format_time(total_distraction)} ({(total_distraction/total_active_time*100):.1f}% of browsing time)")
        
        # Print activity timeline
        print("\n=== ACTIVITY TIMELINE ===")
        print("First activity:", tab_summary['first_seen'].min().strftime("%H:%M:%S"))
        print("Last activity:", tab_summary['last_seen'].max().strftime("%H:%M:%S"))
        
    except Exception as e:
        print(f"Error analyzing logs: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
