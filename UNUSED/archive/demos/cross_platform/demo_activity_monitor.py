"""
Activity Monitor Demo

This script demonstrates the ActivityMonitor class from core.activity_monitor by continuously
tracking and displaying the currently active window information. It's useful for understanding
window switching behavior and debugging window tracking functionality.

Features:
- Tracks active window changes in real-time
- Displays window title, application name, and process ID
- Updates every 2 seconds until manually stopped

Example Output:
    {
        'app_name': 'msedge.exe',
        'window_title': 'Example - Microsoft Edge',
        'pid': '12345',
        'timestamp': '2025-06-05T14:30:00.000000'
    }

Usage:
    python -m demos.cross_platform.demo_activity_monitor

Note: Currently Windows-only implementation.
"""
import time
from core.activity_monitor import ActivityMonitor

if __name__ == "__main__":
    monitor = ActivityMonitor()
    print("Press Ctrl+C to stop.")
    try:
        while True:
            info = monitor.get_active_window()
            print(info)
            time.sleep(2)
    except KeyboardInterrupt:
        print("Exiting demo.")
