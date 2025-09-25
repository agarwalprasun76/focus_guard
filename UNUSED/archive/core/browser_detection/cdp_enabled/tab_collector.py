import pathlib
import requests
import pandas as pd
import subprocess
import sys
import os
from pathlib import Path
import ctypes

ROOT = pathlib.Path.home() / "AppData/Local/FocusGuard/browser_profiles"

# Helper to detect if any Chrome/Edge shortcut needs patching
# This is a minimal check: looks for .lnk files with no CDP flag in Arguments
import win32com.client
BROWSER_NAMES = [
    ('chrome', 'Google Chrome'),
    ('msedge', 'Microsoft Edge'),
]
CDP_FLAG = '--remote-debugging-port=0'
SHORTCUT_DIRS = [
    Path(os.getenv('APPDATA')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs',
    Path.home() / 'Desktop',
]
def shortcut_needs_patch():
    shell = win32com.client.Dispatch('WScript.Shell')
    for dir_ in SHORTCUT_DIRS:
        for shortcut in dir_.rglob('*.lnk'):
            name = shortcut.stem.lower()
            for exe, pretty in BROWSER_NAMES:
                if exe in name or pretty.lower() in name:
                    s = shell.CreateShortcut(str(shortcut))
                    args = s.Arguments or ''
                    if CDP_FLAG not in args:
                        return True
    return False

def close_browsers():
    import psutil
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and (proc.info['name'].lower().startswith('chrome') or proc.info['name'].lower().startswith('msedge')):
            try: proc.terminate()
            except Exception: pass
    psutil.wait_procs([p for p in psutil.process_iter() if p.name().lower().startswith(('chrome', 'msedge'))], timeout=10)

def ensure_shortcuts_patched():
    if shortcut_needs_patch():
        # Prompt user for auto-close/reopen
        MB_YESNO = 0x00000004
        MB_ICONQUESTION = 0x00000020
        msg = (
            "Chrome/Edge shortcuts must be patched to enable tab access.\n\n"
            "Would you like Focus Guard to automatically close all Chrome/Edge windows and patch shortcuts?\n\n"
            "(If you click No, shortcuts will be patched but you must manually restart browsers to enable tab access.)"
        )
        res = ctypes.windll.user32.MessageBoxW(None, msg, "Focus Guard – Enable Tab Access", MB_YESNO | MB_ICONQUESTION)
        patcher = Path(__file__).parent / 'patch_shortcuts.py'
        if res == 6:  # Yes
            close_browsers()
            subprocess.run([sys.executable, str(patcher)], check=True)
            restore_msg = (
                "Browsers have been closed and shortcuts patched for tab access.\n\n"
                "Please reopen Chrome/Edge. If you see a 'Restore Tabs' prompt, click it to reopen all your previous tabs.\n\n"
                "You can also use Ctrl+Shift+T or the History menu to restore tabs if needed."
            )
            ctypes.windll.user32.MessageBoxW(None, restore_msg, "Focus Guard – Restore Tabs", 0x00000040)
        else:
            subprocess.run([sys.executable, str(patcher)], check=True)
            ctypes.windll.user32.MessageBoxW(None, "Shortcuts patched. Please close and reopen Chrome/Edge for tab access.", "Focus Guard", 0x00000040)


def _port(profile):
    """Return the remote debugging port for a given browser profile, or None if not found."""
    p = profile / "DevToolsActivePort"
    return int(p.read_text().splitlines()[0]) if p.exists() else None

def all_tabs():
    """
    Ensures Chrome/Edge shortcuts are patched to launch with remote debugging enabled, then
    returns a DataFrame of all open Chrome/Edge tabs (including Incognito) launched via Focus Guard wrappers.
    Columns: browser, tab_id, url, title, private
    """
    ensure_shortcuts_patched()
    rows = []
    for prof in ROOT.glob("*"):
        port = _port(prof)
        if not port:
            continue
        try:
            items = requests.get(f"http://127.0.0.1:{port}/json").json()
        except Exception:
            continue
        for item in items:
            if item.get("type") != "page":
                continue
            rows.append({
                "browser": prof.name,
                "tab_id":  item["id"],
                "url":     item["url"],
                "title":   item["title"],
                "private": item.get("incognito", False),
            })
    return pd.DataFrame(rows)
