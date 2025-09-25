import os
from pathlib import Path
import win32com.client

# Directories to search for shortcuts
SHORTCUT_DIRS = [
    Path(os.getenv('APPDATA')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs',
    Path.home() / 'Desktop',
    Path('C:/Users/Public/Desktop'),
    Path(os.getenv('PROGRAMDATA', 'C:/ProgramData')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs',
]

BROWSER_NAMES = [
    ('chrome', 'Google Chrome'),
    ('msedge', 'Microsoft Edge'),
]


def find_browser_shortcuts():
    """Yield (shortcut_path, browser_key, shortcut_name) for each Chrome/Edge shortcut found."""
    for dir_ in SHORTCUT_DIRS:
        if not dir_.exists():
            continue
        for shortcut in dir_.rglob('*.lnk'):
            name = shortcut.stem.lower()
            for exe, pretty in BROWSER_NAMES:
                if exe in name or pretty.lower() in name:
                    yield shortcut, exe, shortcut.stem


def print_shortcut_details():
    shell = win32com.client.Dispatch('WScript.Shell')
    print(f"{'Shortcut Path':<80}  {'Browser':<8}  {'Target':<60}  Arguments")
    print("-" * 150)
    for shortcut, exe, name in find_browser_shortcuts():
        shortcut_obj = shell.CreateShortcut(str(shortcut))
        print(f"{str(shortcut):<80}  {exe:<8}  {shortcut_obj.TargetPath:<60}  {shortcut_obj.Arguments}")

if __name__ == "__main__":
    print_shortcut_details()
