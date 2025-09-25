import os
import shutil
import ctypes
import sys
from pathlib import Path
import win32com.client
import time

# Directories to search for shortcuts (expanded for robustness)
SHORTCUT_DIRS = [
    Path(os.getenv('APPDATA')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs',  # Current user Start Menu
    Path.home() / 'Desktop',  # Current user Desktop
    Path('C:/Users/Public/Desktop'),  # Public Desktop
    Path(os.getenv('PROGRAMDATA', 'C:/ProgramData')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs',  # All users Start Menu
]
# Note: Taskbar pins are not normal shortcuts and require special handling not included here. See comments below.

# Backup directory for original shortcuts
BACKUP_DIR = Path(os.getenv('LOCALAPPDATA')) / 'FocusGuard' / 'shortcut_backups'
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Chrome and Edge shortcut patterns
BROWSER_NAMES = [
    ('chrome', 'Google Chrome'),
    ('msedge', 'Microsoft Edge'),
]

CDP_FLAG = '--remote-debugging-port=0'


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


def patch_shortcut(shortcut_path, browser):
    import pywintypes
    shell = win32com.client.Dispatch('WScript.Shell')
    try:
        shortcut = shell.CreateShortcut(str(shortcut_path))
        orig_target = shortcut.TargetPath
        orig_args = shortcut.Arguments or ''

        fg_bin = Path(os.getenv('LOCALAPPDATA')) / 'FocusGuard'
        chrome_bat = str(fg_bin / 'launch_chrome_cdp.bat')
        edge_bat = str(fg_bin / 'launch_edge_cdp.bat')

        if browser == 'chrome':
            new_target = chrome_bat
        elif browser == 'msedge':
            new_target = edge_bat
        else:
            print(f"[SKIPPED] {shortcut_path} (Unknown browser: {browser})")
            return False

        # Only patch if not already pointing to the batch file
        if os.path.normcase(orig_target) != os.path.normcase(new_target):
            shortcut.TargetPath = new_target
            shortcut.Arguments = ''
            try:
                shortcut.Save()
                print(f"[PATCHED] {shortcut_path} (Target: {new_target})")
                return True
            except (pywintypes.com_error, PermissionError, OSError) as e:
                print(f"[FAILED] {shortcut_path} (Permission denied or error: {e})")
                return False
        else:
            print(f"[SKIPPED] {shortcut_path} already points to batch file.")
        return False
    except Exception as e:
        print(f"[ERROR] Could not process {shortcut_path}: {e}")
        return False


def restore_shortcut(shortcut_path):
    backup = BACKUP_DIR / shortcut_path.name
    if backup.exists():
        shutil.copy2(backup, shortcut_path)
        return True
    return False


def backup_shortcut(shortcut_path):
    backup = BACKUP_DIR / shortcut_path.name
    if not backup.exists():
        shutil.copy2(shortcut_path, backup)


def patch_all_shortcuts():
    patched = []
    for shortcut, exe, name in find_browser_shortcuts():
        print(f"[FOUND] {shortcut} (Browser: {exe})")
        backup_shortcut(shortcut)
        if patch_shortcut(shortcut, exe):
            patched.append(shortcut)
    if not patched:
        print("No new shortcuts patched.")
    else:
        print(f"Patched {len(patched)} shortcut(s).")
    return patched


def restore_all_shortcuts():
    restored = []
    for shortcut, exe, name in find_browser_shortcuts():
        if restore_shortcut(shortcut):
            print(f"[RESTORED] {shortcut}")
            restored.append(shortcut)
    if not restored:
        print("No shortcuts restored.")
    else:
        print(f"Restored {len(restored)} shortcut(s).")
    return restored


def popup_message(msg, title="Focus Guard – Shortcuts"):
    ctypes.windll.user32.MessageBoxW(None, msg, title, 0x00000040)  # MB_ICONINFORMATION


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        restored = restore_all_shortcuts()
        if restored:
            popup_message(f"Restored {len(restored)} Chrome/Edge shortcuts from backup.")
        else:
            popup_message("No backups found to restore.")
        return

    patched = patch_all_shortcuts()
    if patched:
        popup_message(f"Patched {len(patched)} Chrome/Edge shortcuts to always launch with remote debugging enabled.\n\nYou can restore originals with:\npython patch_shortcuts.py restore")
    else:
        popup_message("No Chrome/Edge shortcuts found or all already patched.")

if __name__ == "__main__":
    print("Focus Guard Shortcut Patcher")
    print("---------------------------------")
    main()
    print("\nNote: Taskbar pins are not normal .lnk files and will not be patched by this script. To update taskbar pins, unpin and re-pin from a patched shortcut.")
