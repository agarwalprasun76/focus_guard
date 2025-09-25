"""
Time utility functions.
"""
from datetime import datetime

def get_current_time() -> str:
    """Return the current time as an ISO8601 string."""
    return datetime.now().isoformat()
