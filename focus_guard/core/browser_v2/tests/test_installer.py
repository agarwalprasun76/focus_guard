"""Tests for installer module."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from ..installer.strategies import (
    BrowserInfo,
    InstallResult,
    InstallStatus,
    DevUnpackedStrategy,
    StoreInstallStrategy,
    detect_browsers,
)
from ..installer.core_installer import (
    ExtensionInstaller,
    InstallMode,
    InstallationStatus,
)


class TestBrowserInfo:
    """Tests for BrowserInfo dataclass."""

    def test_basic_creation(self):
        """Should create browser info with required fields."""
        info = BrowserInfo(name="Google Chrome", family="chrome")
        
        assert info.name == "Google Chrome"
        assert info.family == "chrome"
        assert info.executable_path is None

    def test_with_executable(self):
        """Should store executable path."""
        info = BrowserInfo(
            name="Google Chrome",
            family="chrome",
            executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        )
        
        assert info.executable_path is not None


class TestInstallResult:
    """Tests for InstallResult dataclass."""

    def test_success_result(self):
        """Should create successful result."""
        result = InstallResult(
            success=True,
            status=InstallStatus.INSTALLED,
            browser="Google Chrome",
            message="Installed successfully",
        )
        
        assert result.success is True
        assert result.status == InstallStatus.INSTALLED
        assert result.error is None

    def test_failure_result(self):
        """Should create failure result with error."""
        result = InstallResult(
            success=False,
            status=InstallStatus.FAILED,
            browser="Google Chrome",
            error="Installation failed",
        )
        
        assert result.success is False
        assert result.status == InstallStatus.FAILED
        assert result.error == "Installation failed"


class TestDevUnpackedStrategy:
    """Tests for DevUnpackedStrategy."""

    def test_name(self):
        """Strategy should have correct name."""
        strategy = DevUnpackedStrategy()
        assert strategy.name == "dev_unpacked"

    def test_install_missing_extension_path(self):
        """Should fail if extension path doesn't exist."""
        strategy = DevUnpackedStrategy()
        browser = BrowserInfo(
            name="Google Chrome",
            family="chrome",
            executable_path="C:\\chrome.exe",
        )
        
        result = strategy.install(browser, Path("nonexistent/path"))
        
        assert result.success is False
        assert result.status == InstallStatus.FAILED
        assert "does not exist" in result.error

    def test_install_missing_executable(self):
        """Should fail if browser executable not found."""
        strategy = DevUnpackedStrategy()
        browser = BrowserInfo(name="Google Chrome", family="chrome")
        
        # Create a temp directory to simulate extension path
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = strategy.install(browser, Path(tmpdir))
        
        assert result.success is False
        assert result.status == InstallStatus.FAILED
        assert "executable" in result.error.lower()


class TestStoreInstallStrategy:
    """Tests for StoreInstallStrategy."""

    def test_name(self):
        """Strategy should have correct name."""
        strategy = StoreInstallStrategy()
        assert strategy.name == "store_install"

    def test_is_published_returns_false_for_pending(self):
        """Should return False for pending publication."""
        assert StoreInstallStrategy.is_published("chrome") is False
        assert StoreInstallStrategy.is_published("edge") is False

    def test_get_store_url_returns_none_for_pending(self):
        """Should return None for pending publication."""
        assert StoreInstallStrategy.get_store_url("chrome") is None
        assert StoreInstallStrategy.get_store_url("edge") is None

    def test_install_pending_publication(self):
        """Should return pending status when not published."""
        strategy = StoreInstallStrategy()
        browser = BrowserInfo(name="Google Chrome", family="chrome")
        
        result = strategy.install(browser, Path("."))
        
        assert result.status == InstallStatus.PENDING_USER_ACTION
        assert result.requires_user_action is True


class TestExtensionInstaller:
    """Tests for ExtensionInstaller."""

    def test_init_with_defaults(self):
        """Should initialize with default values."""
        installer = ExtensionInstaller()
        
        assert installer._mode == InstallMode.AUTO
        assert installer._tab_server_url == "http://127.0.0.1:58392"

    def test_init_with_custom_config(self):
        """Should accept custom configuration."""
        installer = ExtensionInstaller(
            tab_server_url="http://localhost:8080",
            mode=InstallMode.DEV,
        )
        
        assert installer._mode == InstallMode.DEV
        assert installer._tab_server_url == "http://localhost:8080"

    def test_detect_browsers(self):
        """Should detect browsers (platform-dependent)."""
        installer = ExtensionInstaller()
        browsers = installer.detect_browsers()
        
        # Just verify it returns a list (actual browsers depend on system)
        assert isinstance(browsers, list)

    def test_get_store_urls(self):
        """Should return store URLs dictionary."""
        installer = ExtensionInstaller()
        urls = installer.get_store_urls()
        
        assert "chrome" in urls
        assert "edge" in urls

    def test_status_starts_empty(self):
        """Status should start empty."""
        installer = ExtensionInstaller()
        status = installer.status
        
        assert len(status.browsers) == 0
        assert status.all_connected is False
        assert status.any_connected is False


class TestInstallationStatus:
    """Tests for InstallationStatus."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        status = InstallationStatus()
        status.browsers["Chrome"] = InstallResult(
            success=True,
            status=InstallStatus.CONNECTED,
            browser="Chrome",
        )
        status.any_connected = True
        
        d = status.to_dict()
        
        assert "browsers" in d
        assert "Chrome" in d["browsers"]
        assert d["any_connected"] is True

    def test_empty_status(self):
        """Empty status should have correct defaults."""
        status = InstallationStatus()
        
        assert status.all_connected is False
        assert status.any_connected is False
        assert status.pending_user_action is False


class TestDetectBrowsers:
    """Tests for detect_browsers function."""

    def test_returns_list(self):
        """Should return a list."""
        browsers = detect_browsers()
        assert isinstance(browsers, list)

    def test_browser_info_structure(self):
        """Detected browsers should have correct structure."""
        browsers = detect_browsers()
        
        for browser in browsers:
            assert isinstance(browser, BrowserInfo)
            assert browser.name is not None
            assert browser.family in ("chrome", "edge", "firefox", "safari")
