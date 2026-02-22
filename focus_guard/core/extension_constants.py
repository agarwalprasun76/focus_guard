"""Canonical extension IDs and store URLs for FocusGuard browser extensions.

Every Python module that needs an extension ID or store URL should import
from here instead of hardcoding values.  Non-Python files (PS1, BAT, JSON,
XML) cannot import this module — they carry a comment pointing here so a
future update only requires changing this file plus a quick grep.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Extension IDs (assigned by the respective stores)
# ---------------------------------------------------------------------------

CHROME_EXTENSION_ID = "hnpfnmlcmdhkbhnfifmnonehebeafclp"
EDGE_EXTENSION_ID = "legaalcjhhgofgpgbbpoadafdjllckgg"

EXTENSION_IDS = {
    "chrome": CHROME_EXTENSION_ID,
    "edge": EDGE_EXTENSION_ID,
}

# ---------------------------------------------------------------------------
# Store URLs
# ---------------------------------------------------------------------------

CHROME_STORE_URL = (
    f"https://chromewebstore.google.com/detail/"
    f"focusguard-productivity-t/{CHROME_EXTENSION_ID}"
)

EDGE_STORE_URL = (
    f"https://microsoftedge.microsoft.com/addons/detail/"
    f"focusguard-productivity/{EDGE_EXTENSION_ID}"
)

STORE_URLS = {
    "chrome": CHROME_STORE_URL,
    "edge": EDGE_STORE_URL,
}


def get_store_url(browser_family: str) -> str | None:
    """Return the store URL for *browser_family* ('chrome' or 'edge')."""
    return STORE_URLS.get(browser_family)
