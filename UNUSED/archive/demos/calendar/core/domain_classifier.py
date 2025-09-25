"""
Domain Classifier

This module provides core functionality for domain classification and monitoring.
It's designed to be memory-efficient and provides domain categorization based on
predefined rules.

Features:
- Classifies domains into categories (work, social, entertainment, etc.)
- Provides domain allowance checking against calendar context
- Lightweight and efficient implementation

This is a core component used by other modules in the system.
"""

import sys
import os
import time
import datetime
import argparse
import re
import gc
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    import psutil
    def get_memory_usage() -> float:
        """Get current memory usage in MB"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
except ImportError:
    def get_memory_usage() -> float:
        """Fallback when psutil is not available"""
        return 0.0

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Domain categories for classification
# Domain categories for classification
DOMAIN_CATEGORIES = {
    "work": ["office.com", "slack.com", "zoom.us", "github.com", "atlassian.com", "microsoft.com"],
    "social": ["facebook.com", "twitter.com", "instagram.com", "tiktok.com", "snapchat.com", "reddit.com", "linkedin.com"],
    "entertainment": ["youtube.com", "netflix.com", "twitch.tv", "hulu.com", "disneyplus.com", "hbomax.com"],
    "shopping": ["amazon.com", "ebay.com", "etsy.com", "walmart.com", "target.com"],
    "news": ["nytimes.com", "wsj.com", "washingtonpost.com", "cnn.com", "bbc.com"],
    "email": ["gmail.com", "outlook.com", "yahoo.com", "protonmail.com"],
    "development": ["github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com", "stackexchange.com"],
    "productivity": ["notion.so", "trello.com", "asana.com", "todoist.com"]
}
