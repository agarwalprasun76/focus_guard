"""Integration tests for browser_v2 tab server HTTP endpoints."""

from __future__ import annotations

import json
import socket
import threading
from http.client import HTTPConnection

import pytest

from focus_guard.core.browser_v2.tab_server.api_models import (
    BrowserFamily,
    TabInfo,
    BrowserStatus,
    TabsSnapshot,
    CommandRequest,
    CommandResult,
)
from focus_guard.core.browser_v2.tab_server.server import TabServer, TabServerContext


@pytest.fixture
def tab_server_instance():
    def health_provider():
        return {"status": "healthy"}

    def tabs_provider():
        return TabsSnapshot(
            tabs=[TabInfo(id="1", url="https://example.com", title="Example", browser=BrowserFamily.CHROME)],
            browsers=[BrowserStatus(browser=BrowserFamily.CHROME, connected=True)],
            generated_at=123.456,
        )

    def command_handler(request: CommandRequest) -> CommandResult:
        return CommandResult(success=True, action=request.action or "noop")

    context = TabServerContext(
        health_provider=health_provider,
        tabs_provider=tabs_provider,
        command_handler=command_handler,
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        host, port = sock.getsockname()

    server = TabServer((host, port), context)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield host, port
    finally:
        server.shutdown()
        thread.join(timeout=1)


def test_health_endpoint(tab_server_instance):
    host, port = tab_server_instance
    conn = HTTPConnection(host, port)
    conn.request("GET", "/api/health")
    response = conn.getresponse()
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    assert data["status"] == "healthy"


def test_tabs_endpoint(tab_server_instance):
    host, port = tab_server_instance
    conn = HTTPConnection(host, port)
    conn.request("GET", "/api/tabs")
    response = conn.getresponse()
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    assert len(data["tabs"]) == 1
    assert data["tabs"][0]["url"] == "https://example.com"


def test_command_endpoint(tab_server_instance):
    host, port = tab_server_instance
    conn = HTTPConnection(host, port)
    payload = json.dumps({"action": "close_tab", "tab_id": "1"}).encode("utf-8")
    conn.request("POST", "/api/command", body=payload, headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    assert data["success"] is True
    assert data["action"] == "close_tab"
