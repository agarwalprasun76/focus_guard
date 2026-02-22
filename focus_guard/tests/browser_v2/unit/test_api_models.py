"""Unit tests for browser_v2 tab server API models."""

from __future__ import annotations

from focus_guard.core.browser_v2.tab_server.api_models import (
    BrowserFamily,
    TabInfo,
    BrowserStatus,
    TabsSnapshot,
    CommandRequest,
    CommandResult,
)


def test_tab_info_defaults():
    tab = TabInfo(id="1", url="https://example.com", title="Example", browser=BrowserFamily.CHROME)
    assert tab.active is False
    assert tab.extras == {}


def test_browser_status_defaults():
    status = BrowserStatus(browser=BrowserFamily.EDGE, connected=True)
    assert status.errors == []
    assert status.extension_version is None


def test_tabs_snapshot_contains_tabs_and_status():
    tab = TabInfo(id="1", url="https://example.com", title="Example", browser=BrowserFamily.CHROME)
    status = BrowserStatus(browser=BrowserFamily.CHROME, connected=True)
    snapshot = TabsSnapshot(tabs=[tab], browsers=[status], generated_at=123.456)
    assert snapshot.tabs[0].browser is BrowserFamily.CHROME
    assert snapshot.browsers[0].connected is True


def test_command_request_optional_fields():
    request = CommandRequest(action="close_tab")
    assert request.tab_id is None
    assert request.metadata == {}


def test_command_result_success():
    result = CommandResult(success=True, action="close_tab", tab_id="1", browser=BrowserFamily.CHROME)
    assert result.success is True
    assert result.browser is BrowserFamily.CHROME
