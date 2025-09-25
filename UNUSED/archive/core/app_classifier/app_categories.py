"""
Defines categories of applications and their associated process names.
"""

APP_CATEGORIES = {
    "productivity": [
        "excel.exe", "winword.exe", "powerpnt.exe", "onenote.exe",
        "msedge.exe:newtab", "chrome.exe:newtab", "firefox.exe:newtab"
    ],
    "programming": [
        "code.exe", "pycharm64.exe", "intellij64.exe", "webstorm64.exe",
        "clion64.exe", "rider64.exe", "devenv.exe", "sublime_text.exe"
    ],
    "communication": [
        "teams.exe", "slack.exe", "outlook.exe", "msedge.exe:teams",
        "chrome.exe:teams", "chrome.exe:slack", "chrome.exe:outlook"
    ],
    "browser": ["msedge.exe", "chrome.exe", "firefox.exe", "safari.exe"],
    "entertainment": [
        "spotify.exe", "discord.exe", "steam.exe", "battle.net.exe",
        "epicgameslauncher.exe"
    ],
    "education": [
        "acrobat.exe", "zotero.exe", "mendeley.exe", "anki.exe",
        "chrome.exe:khanacademy", "chrome.exe:coursera", "chrome.exe:edx"
    ],
    "design": [
        "photoshop.exe", "figma.exe", "xd.exe", "illustrator.exe",
        "sketch.exe"
    ],
    "math_science": [
        "matlab.exe", "mathematica.exe", "maple.exe", "wolfram.exe",
        "chrome.exe:overleaf", "chrome.exe:desmos", "chrome.exe:geogebra"
    ],
    "documentation": [
        "chrome.exe:docs.google.com", "chrome.exe:overleaf.com",
        "chrome.exe:readthedocs.io", "chrome.exe:stackoverflow.com"
    ]
}

# Reverse mapping for quick lookup
APP_CATEGORY_MAPPING = {}
for category, apps in APP_CATEGORIES.items():
    for app in apps:
        APP_CATEGORY_MAPPING[app.lower()] = category

def get_app_category(process_name: str, window_title: str = "") -> str:
    """
    Categorize an application based on its process name and window title.
    
    Args:
        process_name: Name of the process (e.g., 'chrome.exe')
        window_title: Optional window title for more specific categorization
        
    Returns:
        str: Category name or 'unknown' if not found
    """
    # Try exact match first
    key = f"{process_name.lower()}:{window_title.lower()}" if window_title else process_name.lower()
    
    # Check for exact match
    if key in APP_CATEGORY_MAPPING:
        return APP_CATEGORY_MAPPING[key]
    
    # Check for process name only
    if process_name.lower() in APP_CATEGORY_MAPPING:
        return APP_CATEGORY_MAPPING[process_name.lower()]
    
    # Try partial matches for browser tabs
    if ":" in key:
        process_part = key.split(":")[0]
        if process_part in ["chrome.exe", "msedge.exe", "firefox.exe"]:
            return "browser"
    
    return "unknown"
