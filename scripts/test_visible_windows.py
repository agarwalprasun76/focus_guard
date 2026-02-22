"""Quick test for visible windows tracking."""
import sys
sys.path.insert(0, '.')

from focus_guard.core.activity.monitor import ActivityMonitor

monitor = ActivityMonitor()
windows = monitor.get_visible_windows()

print(f"Found {len(windows)} visible windows:")
for w in windows[:15]:
    app = w.get("app_name", "unknown")
    title = w.get("window_title", "")[:60]
    pct = w.get("percent", 0) * 100
    print(f"  - {app}: {title} ({pct:.1f}%)")
