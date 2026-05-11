"""Environment-driven admin gateway config (Day 11)."""

from __future__ import annotations

from focus_guard.core.admin_gateway.config import (
    DEFAULT_ADMIN_GATEWAY_PORT,
    load_admin_gateway_config,
)


def test_load_config_default_port_matches_builtin_origins() -> None:
    cfg = load_admin_gateway_config(environ={})
    assert cfg.port == DEFAULT_ADMIN_GATEWAY_PORT
    assert f"http://127.0.0.1:{DEFAULT_ADMIN_GATEWAY_PORT}" in cfg.allowed_origins


def test_load_config_custom_port_updates_allowed_origins(monkeypatch) -> None:
    monkeypatch.setenv("FOCUS_GUARD_ADMIN_GATEWAY_PORT", "60001")
    cfg = load_admin_gateway_config()
    assert cfg.port == 60001
    assert "http://127.0.0.1:60001" in cfg.allowed_origins


def test_load_config_additional_origins_parsed(monkeypatch) -> None:
    monkeypatch.setenv(
        "FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS",
        "https://guardian.example.com, https://other.example.org/path",
    )
    cfg = load_admin_gateway_config()
    assert "https://guardian.example.com" in cfg.additional_allowed_origins
    assert "https://other.example.org/path" in cfg.additional_allowed_origins


def test_load_config_strict_origin_env(monkeypatch) -> None:
    monkeypatch.setenv("FOCUS_GUARD_ADMIN_ALLOW_REQUESTS_WITHOUT_ORIGIN", "false")
    cfg = load_admin_gateway_config()
    assert cfg.allow_requests_without_origin is False
