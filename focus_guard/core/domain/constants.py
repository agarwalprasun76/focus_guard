"""
Domain constants and predefined configurations.

This module defines constants and predefined configurations for domain
categories, whitelists, and application domains.

As of Section 7 consolidation, the canonical source of truth is
DomainConfigManager (domain_config.json). The values below are kept as
**fallback defaults** and are used only when the manager is unavailable.
"""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


def _get_manager():
    """Lazy import to avoid circular dependencies."""
    try:
        from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
        return get_domain_config_manager()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Fallback hardcoded values (used only when DomainConfigManager is unavailable)
# ---------------------------------------------------------------------------

_FALLBACK_DOMAIN_CATEGORIES: Dict[str, List[str]] = {
    "work": [
        "office.com", "slack.com", "zoom.us", "teams.microsoft.com",
        "github.com", "gitlab.com", "atlassian.com", "jira.com",
        "confluence.com", "asana.com", "trello.com", "notion.so",
        "google.com", "docs.google.com", "drive.google.com", "sheets.google.com",
        "calendar.google.com", "meet.google.com"
    ],
    "social_media": [
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "reddit.com", "pinterest.com", "tiktok.com", "snapchat.com",
        "whatsapp.com", "telegram.org", "discord.com", "pronto.io"
    ],
    "entertainment": [
        "youtube.com", "netflix.com", "hulu.com", "disneyplus.com",
        "hbomax.com", "primevideo.com", "twitch.tv", "spotify.com",
        "soundcloud.com"
    ],
    "shopping": [
        "amazon.com", "ebay.com", "etsy.com", "walmart.com",
        "target.com", "bestbuy.com", "newegg.com", "aliexpress.com"
    ],
    "news": [
        "nytimes.com", "wsj.com", "washingtonpost.com", "theguardian.com",
        "bbc.com", "cnn.com", "reuters.com", "bloomberg.com"
    ],
    "email": [
        "gmail.com", "outlook.com", "yahoo.com", "protonmail.com",
        "zoho.com", "icloud.com", "mail.com"
    ],
    "development": [
        "github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com",
        "stackexchange.com", "dev.to", "medium.com", "devdocs.io"
    ],
    "productivity": [
        "notion.so", "trello.com", "asana.com", "todoist.com",
        "evernote.com", "bear.app", "obsidian.md"
    ],
    "education": [
        "khanacademy.org", "coursera.org", "edx.org", "udemy.com",
        "wikipedia.org", "khanacademy.org", "artofproblemsolving.com"
    ]
}

_FALLBACK_WHITELIST: Set[str] = {
    "google.com", "gstatic.com", "googleapis.com", "microsoft.com",
    "apple.com", "mozilla.org", "mozilla.com", "mozilla.net",
    "windowsupdate.com", "microsoftonline.com", "live.com",
    "cloudfront.net", "akamaihd.net", "akamaized.net", "cloudflare.com",
    "fastly.net", "cloudflare.net", "amazonaws.com",
    "windows.com", "office.com", "office.net", "office365.com"
}


# ---------------------------------------------------------------------------
# Public API — reads from DomainConfigManager, falls back to hardcoded
# ---------------------------------------------------------------------------

def _get_domain_categories() -> Dict[str, List[str]]:
    mgr = _get_manager()
    if mgr:
        return mgr.get_domain_categories()
    return _FALLBACK_DOMAIN_CATEGORIES


def _get_whitelist() -> Set[str]:
    mgr = _get_manager()
    if mgr:
        return mgr.get_system_whitelist()
    return _FALLBACK_WHITELIST


# Module-level attributes for backward compatibility.
# These are properties accessed via the module; callers that import
# DOMAIN_CATEGORIES will get the live value at import time.
# For truly dynamic access, callers should use get_domain_config_manager().
DOMAIN_CATEGORIES: Dict[str, List[str]] = _get_domain_categories()
DOMAIN_WHITELIST: Set[str] = _get_whitelist()

# Application names and their associated domains (not domain-config-managed)
APPLICATION_DOMAINS: Dict[str, List[str]] = {
    "browsers": [
        "chrome.exe", "firefox.exe", "msedge.exe", "safari.exe",
        "opera.exe", "brave.exe", "vivaldi.exe"
    ],
    "development": [
        "code.exe", "pycharm64.exe", "intellij64.exe", "webstorm64.exe",
        "clion64.exe", "goland64.exe", "rider64.exe"
    ],
    "communication": [
        "teams.exe", "slack.exe", "discord.exe", "zoom.exe",
        "whatsapp.exe", "telegram.exe"
    ],
    "productivity": [
        "outlook.exe", "winword.exe", "excel.exe", "powerpnt.exe",
        "onenote.exe", "notion.exe", "todoist.exe"
    ]
}

# Category mapping to enum values
CATEGORY_TO_ENUM_MAPPING: Dict[str, str] = {
    "work": "PRODUCTIVITY",
    "social_media": "SOCIAL_MEDIA",
    "social": "SOCIAL_MEDIA",
    "entertainment": "ENTERTAINMENT",
    "gaming": "GAMING",
    "shopping": "SHOPPING",
    "news": "NEWS",
    "email": "PRODUCTIVITY",
    "development": "TECHNOLOGY",
    "productivity": "PRODUCTIVITY",
    "education": "EDUCATION",
    "adult": "ADULT",
}

# Default configuration
DEFAULT_CONFIG = {
    "domain_categories": DOMAIN_CATEGORIES,
    "whitelist": DOMAIN_WHITELIST,
    "applications": APPLICATION_DOMAINS
}
