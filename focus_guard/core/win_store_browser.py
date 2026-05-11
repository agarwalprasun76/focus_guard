"""Open store/install URLs in a specific installed browser on Windows."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_CHROME_PATHS = [
    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
]

_EDGE_PATHS = [
    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
]


def _popen_url(exe: Path, url: str) -> bool:
    if not exe.is_file():
        return False
    try:
        subprocess.Popen([str(exe), url], close_fds=True, cwd=str(exe.parent))  # noqa: S603 trusted paths only
        return True
    except OSError as e:
        logger.debug("Launcher failed for %s: %s", exe, e)
        return False


def open_google_chrome_url(url: str) -> bool:
    """Prefer an installed chrome.exe under standard paths."""
    if sys.platform != "win32":
        return False
    for cand in _CHROME_PATHS:
        if _popen_url(Path(cand), url):
            return True
    return False


def open_chrome_extensions_page() -> bool:
    """Open ``chrome://extensions`` in an installed Google Chrome binary."""
    if sys.platform != "win32":
        return False
    for cand in _CHROME_PATHS:
        if _popen_url(Path(cand), "chrome://extensions"):
            return True
    return False


def open_edge_extensions_page() -> bool:
    """Open ``edge://extensions`` in an installed Microsoft Edge binary."""
    if sys.platform != "win32":
        return False
    for cand in _EDGE_PATHS:
        if _popen_url(Path(cand), "edge://extensions"):
            return True
    try:
        subprocess.Popen(["cmd.exe", "/c", "start", "", "msedge", "edge://extensions"])  # noqa: S607
        return True
    except OSError as e:
        logger.debug("Could not open Edge extensions page: %s", e)
        return False


def open_microsoft_edge_url(url: str) -> bool:
    """Prefer Edge URI scheme, then msedge.exe, then `start msedge`."""
    if sys.platform != "win32":
        return False
    try:
        os.startfile(f"microsoft-edge:{url}")  # noqa: S606 Windows shell integration
        return True
    except OSError:
        pass
    for cand in _EDGE_PATHS:
        if _popen_url(Path(cand), url):
            return True
    try:
        subprocess.Popen(["cmd.exe", "/c", "start", "", "msedge", url])  # noqa: S607
        return True
    except OSError as e:
        logger.warning("Could not open Microsoft Edge for URL: %s", e)
        return False
