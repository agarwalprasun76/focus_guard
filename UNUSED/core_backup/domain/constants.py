"""
Domain constants and predefined configurations.

This module defines constants and predefined configurations for domain
categories, whitelists, and application domains.
"""

from typing import Dict, List, Set

# Domain categories and their associated domains
DOMAIN_CATEGORIES: Dict[str, List[str]] = {
    "work": [
        "office.com", "slack.com", "zoom.us", "teams.microsoft.com",
        "github.com", "gitlab.com", "atlassian.com", "jira.com",
        "confluence.com", "asana.com", "trello.com", "notion.so",
        "google.com", "docs.google.com", "drive.google.com", "sheets.google.com",
        "calendar.google.com", "meet.google.com"
    ],
    "social": [
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "reddit.com", "pinterest.com", "tiktok.com", "snapchat.com",
        "whatsapp.com", "telegram.org", "discord.com"
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

# Always allowed domains (whitelist)
DOMAIN_WHITELIST: Set[str] = {
    # System domains
    "google.com", "gstatic.com", "googleapis.com", "microsoft.com",
    "apple.com", "mozilla.org", "mozilla.com", "mozilla.net",
    "windowsupdate.com", "microsoftonline.com", "live.com",
    
    # Common CDNs
    "cloudfront.net", "akamaihd.net", "akamaized.net", "cloudflare.com",
    "fastly.net", "cloudflare.net", "amazonaws.com",
    
    # Security/Updates
    "windows.com", "microsoft.com", "windowsupdate.com", "office.com",
    "office.net", "office365.com"
}

# Application names and their associated domains
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
    "social": "SOCIAL_MEDIA",
    "entertainment": "ENTERTAINMENT",
    "shopping": "SHOPPING",
    "news": "NEWS",
    "email": "PRODUCTIVITY",
    "development": "TECHNOLOGY",
    "productivity": "PRODUCTIVITY",
    "education": "EDUCATION"
}

# Default configuration
DEFAULT_CONFIG = {
    "domain_categories": DOMAIN_CATEGORIES,
    "whitelist": DOMAIN_WHITELIST,
    "applications": APPLICATION_DOMAINS
}
