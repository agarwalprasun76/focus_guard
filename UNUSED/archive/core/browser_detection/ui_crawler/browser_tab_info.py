"""
Robust Windows browser tab detection (minimal, production-ready).
Detects tabs for Chrome, Edge, Brave, Opera, Vivaldi, Firefox.
Uses CDP if available, falls back to UI Automation. Detects incognito/private tabs.
Returns a pandas DataFrame with: browser, window_handle, tab_title, url, is_private, source, etc.
"""
import contextlib
import socket
import json
import re
from typing import List, Dict, Any
import psutil
import requests
import uiautomation as auto
import pandas as pd

# --- Improved UI Automation fallback for URL extraction ---
URL_REGEX = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*://')

def _scrape_url_from_window(win: auto.Control) -> str | None:
    """
    Breadth-first walk of the subtree rooted at `win`.  
    Return the first Edit control whose ValuePattern looks like a URL.
    """
    for ctrl, depth in auto.WalkControl(win, maxDepth=12):   # BFS up to depth 12
        if ctrl.ControlType != auto.ControlType.EditControl:
            continue
        vp = ctrl.GetValuePattern()
        if not vp:
            continue
        val = vp.Value
        if val and URL_REGEX.match(val):
            return val
    return None

def _detect_private(title: str) -> bool:
    return any(title.endswith(suffix) for suffix in PRIVATE_SUFFIXES)

def _strip_private(title: str) -> str:
    for suffix in PRIVATE_SUFFIXES:
        if title.endswith(suffix):
            return title[: -len(suffix)]
    return title

def fetch_tabs_uiautomation(proc_names):
    """
    Enumerate *all* top-level windows that belong to the browsers
    and pull (title, url) out of each tab.
    """
    result = []
    desktop = auto.GetRootControl()

    for tw in desktop.GetChildren():
        proc_name = getattr(tw, "ProcessName", None)
        if not proc_name or proc_name.lower() not in proc_names:
            continue

        # Each tab is its own *tab item* child.  If no tab items exist
        # (Firefox pre-117, some Brave builds) treat the T-L window as the tab.
        tab_items = tw.GetChildren(controlType=auto.ControlType.TabItemControl)
        tab_items = tab_items or [tw]

        for tab in tab_items:
            title = tab.Name or tw.Name           # fallback
            url   = _scrape_url_from_window(tab)  # <- new magic
            result.append({
                "browser"   : tw.ProcessName,
                "window_handle" : tw.NativeWindowHandle,
                "tab_title"    : title,
                "url"       : url,
                "is_private": _detect_private(title),
                "source"    : "uia-deep",
                "pid"       : tw.ProcessId,
            })
    return result

# Browser configuration
BROWSER_CONFIG = {
    "chrome.exe": {"family": "chromium", "default_cdp_port": 9222, "display_name": "Chrome"},
    "msedge.exe": {"family": "chromium", "default_cdp_port": 9223, "display_name": "Edge"},
    "brave.exe": {"family": "chromium", "default_cdp_port": 9226, "display_name": "Brave"},
    "opera.exe": {"family": "chromium", "default_cdp_port": 9227, "display_name": "Opera"},
    "vivaldi.exe": {"family": "chromium", "default_cdp_port": 9228, "display_name": "Vivaldi"},
    "firefox.exe": {"family": "firefox", "display_name": "Firefox"},
}

PRIVATE_SUFFIXES = [
    " - Incognito", " - InPrivate", " - Private Browsing"
]


def _port_is_open(port: int, host: str = "127.0.0.1") -> bool:
    with contextlib.closing(socket.socket()) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0

def _detect_private(title: str) -> bool:
    return any(title.endswith(suffix) for suffix in PRIVATE_SUFFIXES)

def _strip_private(title: str) -> str:
    for suffix in PRIVATE_SUFFIXES:
        if title.endswith(suffix):
            return title[: -len(suffix)]
    return title

def _get_chromium_tabs(proc: psutil.Process, exe: str, config: dict) -> List[dict]:
    tabs = []
    port = config.get("default_cdp_port", 9222)
    if not _port_is_open(port):
        return []
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/json", timeout=0.5)
        for entry in resp.json():
            if entry.get("type") != "page":
                continue
            tabs.append({
                "browser": config["display_name"],
                "window_handle": entry.get("id"),
                "tab_title": entry.get("title", ""),
                "url": entry.get("url", ""),
                "is_private": entry.get("incognito", False),
                "source": "cdp",
                "pid": proc.pid,
            })
    except Exception:
        pass
    return tabs

def _get_firefox_tabs(proc: psutil.Process, exe: str, config: dict) -> List[dict]:
    tabs = []
    # Use UIA for Firefox
    for window in auto.GetRootControl().GetChildren():
        if not window.ClassName.startswith("MozillaWindowClass"):
            continue
        title = window.Name
        if not title or title in ("", "Mozilla Firefox"):
            continue
        tabs.append({
            "browser": config["display_name"],
            "window_handle": window.NativeWindowHandle,
            "tab_title": _strip_private(title),
            "url": "",  # URL not available via UIA
            "is_private": _detect_private(title),
            "source": "uia",
            "pid": proc.pid,
        })
    return tabs

def _get_chromium_tabs_uia(proc: psutil.Process, exe: str, config: dict) -> List[dict]:
    tabs = []
    for window in auto.GetRootControl().GetChildren():
        if not window.ClassName.startswith("Chrome_WidgetWin_1"):
            continue
        title = window.Name
        if not title or title in ("", config["display_name"]):
            continue
        tabs.append({
            "browser": config["display_name"],
            "window_handle": window.NativeWindowHandle,
            "tab_title": _strip_private(title),
            "url": "",  # URL not available via UIA
            "is_private": _detect_private(title),
            "source": "uia",
            "pid": proc.pid,
        })
    return tabs

def get_all_browser_tabs() -> pd.DataFrame:
    """Get all open browser tabs as a pandas DataFrame."""
    # Use improved UIA fallback for all browsers
    # Normalize proc_names by stripping .exe
    proc_names = set(k.replace('.exe','').lower() for k in BROWSER_CONFIG.keys())
    rows = fetch_tabs_uiautomation(proc_names)
    # Try to get CDP tabs for Chromium browsers and merge/override if possible
    for proc in psutil.process_iter(["name", "pid"]):
        exe = proc.info["name"].lower()
        if exe not in BROWSER_CONFIG:
            continue
        config = BROWSER_CONFIG[exe]
        family = config["family"]
        if family == "chromium":
            cdp_tabs = _get_chromium_tabs(proc, exe, config)
            # If CDP tabs found, replace UIA tabs for this browser+pid
            if cdp_tabs:
                # Remove UIA tabs for this browser+pid
                rows = [r for r in rows if not (r["browser"].lower() == config["display_name"].lower() or r["browser"].lower() == exe)]
                rows.extend(cdp_tabs)
    if not rows:
        return pd.DataFrame(columns=["browser", "window_handle", "tab_title", "url", "is_private", "source", "pid"])
    df = pd.DataFrame(rows)
    return df

if __name__ == "__main__":
    df = get_all_browser_tabs()
    # Deduplicate by browser and tab_title
    df_dedup = df.drop_duplicates(subset=["browser", "tab_title"]).reset_index(drop=True)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    print("\n==== DEDUPLICATED TABLE ====")
    print(df_dedup)
    print("\n==== FIRST 10 ROWS (DEDUPLICATED) ====")
    print(df_dedup.head(10))
    print(f"\nTotal unique tabs: {len(df_dedup)}")
    if df_dedup['url'].replace('', pd.NA).isna().all():
        print("\n[WARNING] No URLs detected. To get URLs for Chrome/Edge/Brave/etc., you must launch the browser with the remote debugging port enabled.\n")
        print("For example, run Chrome with: chrome.exe --remote-debugging-port=9222")
        print("Then re-run this script while that browser is open.")
