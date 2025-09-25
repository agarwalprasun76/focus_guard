import os
import sys
import ctypes
import subprocess
import textwrap
from pathlib import Path

def enable_cdp_launchers():
    """
    Set up Chrome & Edge launch wrappers that always start with --remote-debugging-port=0,
    so Focus Guard can read open-tab URLs (including incognito).
    """
    FG_BIN = Path(os.getenv('LOCALAPPDATA')) / 'FocusGuard'
    FG_PROFILES = FG_BIN / 'browser_profiles'
    chrome_wrapper = FG_BIN / 'launch_chrome_cdp.bat'
    edge_wrapper = FG_BIN / 'launch_edge_cdp.bat'

    # Step 1: Detect whether wrappers already exist
    if chrome_wrapper.exists():
        print('Wrappers already installed – skipping task')
        return

    # Step 2: One-time user consent popup
    msg = textwrap.dedent("""
    Focus Guard can show you every open browser tab (including Incognito/InPrivate)
    ONLY if Chrome / Edge are started with a special switch:
       --remote-debugging-port=0

    Do you want Focus Guard to create safe launcher shortcuts that do this?
    Nothing in your existing browser profile will be modified. The application is 
    more useful if you grant it permission to modify your browser profile.
    """)
    res = ctypes.windll.user32.MessageBoxW(
        None, msg, "Focus Guard – permission needed", 0x00000004 | 0x00000040)
    # MB_YESNO | MB_ICONQUESTION
    if res != 6:  # 6 = IDYES, 7 = IDNO
        print('User declined consent. Aborting.')
        return

    # Step 3: Prepare directories
    FG_BIN.mkdir(parents=True, exist_ok=True)
    FG_PROFILES.mkdir(parents=True, exist_ok=True)
    print(f"Created {FG_BIN} and {FG_PROFILES}")

    # Step 4: Write Chrome wrapper
    chrome_profile = FG_PROFILES / 'chrome'
    chrome_wrapper.write_text(f"""@echo off
rem ---------- Chrome CDP wrapper ----------
setlocal EnableDelayedExpansion
set "PROFILE=%LOCALAPPDATA%\\FocusGuard\\browser_profiles\\chrome"
if not exist "%PROFILE%" mkdir "%PROFILE%"
start "" "%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe" ^
  --remote-debugging-port=0 ^
  --user-data-dir="%PROFILE%" ^
  --disable-background-mode --no-first-run --no-default-browser-check ^
  --remote-allow-origins=* %*
endlocal
""")
    print(f"Chrome wrapper written to {chrome_wrapper}")

    # Step 5: Write Edge wrapper
    edge_profile = FG_PROFILES / 'edge'
    edge_wrapper.write_text(f"""@echo off
rem ---------- Edge CDP wrapper ----------
setlocal EnableDelayedExpansion
set "PROFILE=%LOCALAPPDATA%\\FocusGuard\\browser_profiles\\edge"
if not exist "%PROFILE%" mkdir "%PROFILE%"
start "" "%ProgramFiles(x86)%\\Microsoft\\Edge\\Application\\msedge.exe" ^
  --remote-debugging-port=0 ^
  --user-data-dir="%PROFILE%" ^
  --disable-background-mode --no-first-run ^
  --remote-allow-origins=* %*
endlocal
""")
    print(f"Edge wrapper written to {edge_wrapper}")

    # Step 6: Drop Start-menu shortcuts that point to wrappers
    LINKDIR = Path(os.getenv('APPDATA')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'FocusGuard'
    LINKDIR.mkdir(parents=True, exist_ok=True)
    chrome_shortcut = LINKDIR / 'Chrome (FG).lnk'
    edge_shortcut = LINKDIR / 'Edge (FG).lnk'
    subprocess.run([
        'powershell', '-NoProfile', '-Command',
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{chrome_shortcut}');"
        f"$s.TargetPath='{chrome_wrapper}';"
        f"$s.IconLocation='%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe';"
        f"$s.Save()"
    ])
    subprocess.run([
        'powershell', '-NoProfile', '-Command',
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{edge_shortcut}');"
        f"$s.TargetPath='{edge_wrapper}';"
        f"$s.IconLocation='%ProgramFiles(x86)%\\Microsoft\\Edge\\Application\\msedge.exe';"
        f"$s.Save()"
    ])
    print(f"Shortcuts created in {LINKDIR}")

    # Step 7: Prepend FocusGuard bin dir to PATH (non-destructive)
    current_path = os.environ.get('PATH', '')
    fg_bin_str = str(FG_BIN)
    if fg_bin_str not in current_path.split(';'):
        subprocess.run(['setx', 'PATH', f'{fg_bin_str};{current_path}'])
        print(f"Added {fg_bin_str} to PATH. You may need to open a new shell.")
    else:
        print("FocusGuard already in PATH")

    # Step 8: Final message
    print("""
------------------------------------------------------------
  ✅  Focus Guard launchers installed.
  • Use   Start Menu → FocusGuard → Chrome (FG) / Edge (FG)
    OR open a new cmd/pwsh and type `chrome` or `edge`.
  • Focus Guard will read open-tab URLs from
      %LOCALAPPDATA%\FocusGuard\browser_profiles\*\DevToolsActivePort
------------------------------------------------------------
""")

if __name__ == '__main__':
    enable_cdp_launchers()
