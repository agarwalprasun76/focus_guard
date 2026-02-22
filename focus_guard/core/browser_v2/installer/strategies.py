"""Installer strategies for browser extension deployment.

Provides different installation approaches:
- DevUnpackedStrategy: Development mode with --load-extension flag
- StoreInstallStrategy: Guides user to browser extension stores
- EnterpriseStrategy: Registry policy deployment (future)
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import webbrowser
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from focus_guard.core.extension_constants import EXTENSION_IDS as _EXT_IDS, STORE_URLS as _STORE_URLS

logger = logging.getLogger(__name__)


class InstallStatus(str, Enum):
    """Status of extension installation."""

    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"
    CONNECTED = "connected"
    FAILED = "failed"
    PENDING_USER_ACTION = "pending_user_action"


@dataclass
class InstallResult:
    """Result of an installation attempt."""

    success: bool
    status: InstallStatus
    browser: str
    message: str = ""
    store_url: Optional[str] = None
    extension_id: Optional[str] = None
    requires_user_action: bool = False
    error: Optional[str] = None


@dataclass
class BrowserInfo:
    """Information about a detected browser."""

    name: str
    family: str  # chrome, edge, firefox
    executable_path: Optional[str] = None
    version: Optional[str] = None
    profile_path: Optional[str] = None
    is_running: bool = False


class InstallerStrategy(ABC):
    """Base class for extension installation strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for logging and configuration."""
        pass

    @abstractmethod
    def install(self, browser: BrowserInfo, extension_path: Path) -> InstallResult:
        """Attempt to install the extension.

        Args:
            browser: Target browser information.
            extension_path: Path to the extension directory.

        Returns:
            InstallResult with the outcome.
        """
        pass

    @abstractmethod
    def verify(self, browser: BrowserInfo, tab_server_url: str) -> bool:
        """Verify the extension is installed and connected.

        Args:
            browser: Target browser information.
            tab_server_url: URL of the tab server to check connection.

        Returns:
            True if extension is verified as connected.
        """
        pass


class DevUnpackedStrategy(InstallerStrategy):
    """Development installation using --load-extension flag.

    This strategy launches the browser with the extension loaded in developer mode.
    Useful for development and testing, but not persistent across browser restarts.
    """

    @property
    def name(self) -> str:
        return "dev_unpacked"

    def install(self, browser: BrowserInfo, extension_path: Path) -> InstallResult:
        """Launch browser with extension loaded via --load-extension."""
        if not extension_path.exists():
            return InstallResult(
                success=False,
                status=InstallStatus.FAILED,
                browser=browser.name,
                error=f"Extension path does not exist: {extension_path}",
            )

        if not browser.executable_path:
            return InstallResult(
                success=False,
                status=InstallStatus.FAILED,
                browser=browser.name,
                error="Browser executable path not found",
            )

        try:
            # Build command based on browser family
            cmd = self._build_launch_command(browser, extension_path)
            
            logger.info("Launching %s with extension: %s", browser.name, " ".join(cmd))
            
            # Launch browser (non-blocking)
            if sys.platform == "win32":
                subprocess.Popen(
                    cmd,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    cmd,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            return InstallResult(
                success=True,
                status=InstallStatus.INSTALLING,
                browser=browser.name,
                message=f"Browser launched with extension. Waiting for connection...",
                requires_user_action=False,
            )

        except Exception as e:
            logger.exception("Failed to launch browser: %s", e)
            return InstallResult(
                success=False,
                status=InstallStatus.FAILED,
                browser=browser.name,
                error=str(e),
            )

    def _build_launch_command(self, browser: BrowserInfo, extension_path: Path) -> List[str]:
        """Build the browser launch command with extension flags."""
        cmd = [browser.executable_path]
        
        # Common flags for Chromium-based browsers
        if browser.family in ("chrome", "edge"):
            cmd.extend([
                f"--load-extension={extension_path}",
                "--no-first-run",
                "--no-default-browser-check",
            ])
            
            # Use a separate profile to avoid conflicts
            profile_dir = self._get_dev_profile_path(browser)
            if profile_dir:
                cmd.append(f"--user-data-dir={profile_dir}")

        return cmd

    def _get_dev_profile_path(self, browser: BrowserInfo) -> Optional[str]:
        """Get path for development profile."""
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA", "")
        else:
            base = os.path.expanduser("~/.config")

        if not base:
            return None

        profile_name = f"FocusGuard_Dev_{browser.family}"
        return os.path.join(base, "FocusGuard", "BrowserProfiles", profile_name)

    def verify(self, browser: BrowserInfo, tab_server_url: str) -> bool:
        """Check if extension is connected to tab server."""
        import urllib.request
        import urllib.error

        try:
            url = f"{tab_server_url}/api/status"
            with urllib.request.urlopen(url, timeout=5.0) as response:
                if response.status == 200:
                    import json
                    data = json.loads(response.read().decode("utf-8"))
                    browsers = data.get("connected_browsers", [])
                    for b in browsers:
                        if b.get("connected") and browser.family in b.get("browser", "").lower():
                            return True
        except (urllib.error.URLError, OSError) as e:
            logger.debug("Verification failed: %s", e)

        return False


class StoreInstallStrategy(InstallerStrategy):
    """Installation via browser extension stores.

    This strategy guides the user to install from Chrome Web Store or
    Microsoft Edge Add-ons. It's the recommended approach for production.
    """

    STORE_URLS = _STORE_URLS

    EXTENSION_IDS = _EXT_IDS

    @property
    def name(self) -> str:
        return "store_install"

    def install(self, browser: BrowserInfo, extension_path: Path) -> InstallResult:
        """Guide user to install from browser store."""
        extension_id = self.EXTENSION_IDS.get(browser.family)
        
        if not extension_id or extension_id == "pending_publication":
            return InstallResult(
                success=False,
                status=InstallStatus.PENDING_USER_ACTION,
                browser=browser.name,
                message="Extension not yet published to store. Please use developer mode installation.",
                requires_user_action=True,
                error="Extension pending store publication",
            )

        store_url = self.STORE_URLS.get(browser.family, "").format(extension_id=extension_id)
        
        if not store_url:
            return InstallResult(
                success=False,
                status=InstallStatus.FAILED,
                browser=browser.name,
                error=f"No store URL available for {browser.family}",
            )

        try:
            # Open store page in browser
            webbrowser.open(store_url)
            
            return InstallResult(
                success=True,
                status=InstallStatus.PENDING_USER_ACTION,
                browser=browser.name,
                message=f"Please install the extension from the store page that opened in your browser.",
                store_url=store_url,
                extension_id=extension_id,
                requires_user_action=True,
            )

        except Exception as e:
            logger.exception("Failed to open store page: %s", e)
            return InstallResult(
                success=False,
                status=InstallStatus.FAILED,
                browser=browser.name,
                store_url=store_url,
                error=str(e),
            )

    def verify(self, browser: BrowserInfo, tab_server_url: str) -> bool:
        """Check if extension is connected to tab server."""
        import urllib.request
        import urllib.error

        try:
            url = f"{tab_server_url}/api/status"
            with urllib.request.urlopen(url, timeout=5.0) as response:
                if response.status == 200:
                    import json
                    data = json.loads(response.read().decode("utf-8"))
                    browsers = data.get("connected_browsers", [])
                    for b in browsers:
                        if b.get("connected") and browser.family in b.get("browser", "").lower():
                            return True
        except (urllib.error.URLError, OSError) as e:
            logger.debug("Verification failed: %s", e)

        return False

    @classmethod
    def get_store_url(cls, browser_family: str) -> Optional[str]:
        """Get the store URL for a browser family."""
        extension_id = cls.EXTENSION_IDS.get(browser_family)
        if not extension_id or extension_id == "pending_publication":
            return None
        return cls.STORE_URLS.get(browser_family, "").format(extension_id=extension_id)

    @classmethod
    def is_published(cls, browser_family: str) -> bool:
        """Check if extension is published for a browser."""
        extension_id = cls.EXTENSION_IDS.get(browser_family)
        return extension_id is not None and extension_id != "pending_publication"


class EnterpriseStrategy(InstallerStrategy):
    """Enterprise deployment via registry policies.

    This strategy uses Windows registry policies to force-install the extension.
    Requires administrator privileges and is intended for managed environments.

    Note: This is a placeholder for future implementation.
    """

    @property
    def name(self) -> str:
        return "enterprise"

    def install(self, browser: BrowserInfo, extension_path: Path) -> InstallResult:
        """Deploy extension via registry policy."""
        # Placeholder - requires admin privileges and careful implementation
        return InstallResult(
            success=False,
            status=InstallStatus.FAILED,
            browser=browser.name,
            error="Enterprise deployment not yet implemented",
        )

    def verify(self, browser: BrowserInfo, tab_server_url: str) -> bool:
        """Check if extension is connected."""
        return False


def get_default_strategy(for_development: bool = False) -> InstallerStrategy:
    """Get the default installer strategy.

    Args:
        for_development: If True, use dev unpacked strategy.

    Returns:
        Appropriate installer strategy.
    """
    if for_development:
        return DevUnpackedStrategy()
    return StoreInstallStrategy()


def detect_browsers() -> List[BrowserInfo]:
    """Detect installed browsers on the system.

    Returns:
        List of detected browser information.
    """
    browsers = []

    if sys.platform == "win32":
        browsers.extend(_detect_windows_browsers())
    elif sys.platform == "darwin":
        browsers.extend(_detect_macos_browsers())
    else:
        browsers.extend(_detect_linux_browsers())

    return browsers


def _detect_windows_browsers() -> List[BrowserInfo]:
    """Detect browsers on Windows."""
    import winreg

    browsers = []
    
    # Common browser registry paths
    browser_paths = [
        # Chrome
        (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
            "Google Chrome",
            "chrome",
        ),
        # Edge
        (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
            "Microsoft Edge",
            "edge",
        ),
    ]

    for reg_path, name, family in browser_paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                exe_path, _ = winreg.QueryValueEx(key, "")
                if os.path.exists(exe_path):
                    browsers.append(BrowserInfo(
                        name=name,
                        family=family,
                        executable_path=exe_path,
                    ))
        except (FileNotFoundError, OSError):
            pass

    # Fallback: check common installation paths
    common_paths = {
        "chrome": [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ],
        "edge": [
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        ],
    }

    detected_families = {b.family for b in browsers}
    
    for family, paths in common_paths.items():
        if family in detected_families:
            continue
        for path in paths:
            if os.path.exists(path):
                name = "Google Chrome" if family == "chrome" else "Microsoft Edge"
                browsers.append(BrowserInfo(
                    name=name,
                    family=family,
                    executable_path=path,
                ))
                break

    return browsers


def _detect_macos_browsers() -> List[BrowserInfo]:
    """Detect browsers on macOS."""
    browsers = []
    
    app_paths = {
        "chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "edge": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    }

    for family, path in app_paths.items():
        if os.path.exists(path):
            name = "Google Chrome" if family == "chrome" else "Microsoft Edge"
            browsers.append(BrowserInfo(
                name=name,
                family=family,
                executable_path=path,
            ))

    return browsers


def _detect_linux_browsers() -> List[BrowserInfo]:
    """Detect browsers on Linux."""
    import shutil

    browsers = []
    
    executables = {
        "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
        "edge": ["microsoft-edge", "microsoft-edge-stable"],
    }

    for family, exe_names in executables.items():
        for exe in exe_names:
            path = shutil.which(exe)
            if path:
                name = "Google Chrome" if family == "chrome" else "Microsoft Edge"
                browsers.append(BrowserInfo(
                    name=name,
                    family=family,
                    executable_path=path,
                ))
                break

    return browsers
