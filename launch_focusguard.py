"""
FocusGuard Launcher — PyInstaller entry point.

This file is the Analysis entry point for PyInstaller. It bootstraps
sys.path so that the focus_guard package can be found inside the frozen
exe, then delegates to focus_guard.main.main().
"""
import os
import sys

def _bootstrap():
    """Ensure the focus_guard package is importable in the frozen exe."""
    if getattr(sys, 'frozen', False):
        # In a frozen exe, _MEIPASS is the temp extraction directory.
        # The focus_guard package lives there because PyInstaller collected it.
        base = sys._MEIPASS
    else:
        # Running as a normal script — project root is this file's directory.
        base = os.path.dirname(os.path.abspath(__file__))

    if base not in sys.path:
        sys.path.insert(0, base)

_bootstrap()

from focus_guard.main import main  # noqa: E402

if __name__ == "__main__":
    main()
