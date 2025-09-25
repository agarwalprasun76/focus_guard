import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.cross_platform import get_active_window_info

end_time = time.time() + 60  # 2 minutes
interval = 5  # seconds

print("Monitoring active window for 2 minutes. Switch windows to see updates. Press Ctrl+C to stop early.\n")

try:
    while time.time() < end_time:
        info = get_active_window_info()
        print(f"{time.strftime('%H:%M:%S')} | {info}")
        time.sleep(interval)
except KeyboardInterrupt:
    print("\nMonitoring stopped by user.")
