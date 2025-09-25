#!/usr/bin/env python
"""
List Browser Tabs

This script is a wrapper around the tab_monitor module that lists all open browser tabs
with their URLs and productivity classifications.
"""

import os
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Fix console encoding on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from core.browser_integration.tab_monitor import main

if __name__ == "__main__":
    main()
