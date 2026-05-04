"""Tests for ProgramData path helpers and api_token.json sidecar fields."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from focus_guard.core.browser_v2.tab_server.api_auth import APIAuthManager
from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
from focus_guard.core.program_data_paths import (
    default_api_token_json_path,
    read_openai_api_key_from_api_token_file,
)


def test_read_openai_api_key_from_file(tmp_path: Path) -> None:
    p = tmp_path / "api_token.json"
    p.write_text(json.dumps({"token": "x", "openai_api_key": "  sk-from-file  "}), encoding="utf-8")
    assert read_openai_api_key_from_api_token_file(p) == "sk-from-file"


def test_read_open_ai_api_key_alternate_field_name(tmp_path: Path) -> None:
    p = tmp_path / "api_token.json"
    p.write_text(json.dumps({"token": "x", "open_ai_api_key": "sk-alt-field"}), encoding="utf-8")
    assert read_openai_api_key_from_api_token_file(p) == "sk-alt-field"


def test_openai_api_key_preferred_over_open_ai_api_key(tmp_path: Path) -> None:
    p = tmp_path / "api_token.json"
    p.write_text(
        json.dumps(
            {"token": "x", "openai_api_key": "first", "open_ai_api_key": "second"},
        ),
        encoding="utf-8",
    )
    assert read_openai_api_key_from_api_token_file(p) == "first"


def test_read_openai_api_key_missing_file(tmp_path: Path) -> None:
    assert read_openai_api_key_from_api_token_file(tmp_path / "nope.json") is None


def test_openai_client_prefers_env_over_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fg = tmp_path / "FocusGuard"
    fg.mkdir()
    p = fg / "api_token.json"
    p.write_text(json.dumps({"token": "t", "openai_api_key": "from-file"}), encoding="utf-8")
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    with patch.object(OpenAIClient, "_validate_api_key", return_value=True):
        c = OpenAIClient()
    assert c.api_key == "from-env"


def test_openai_client_uses_file_when_env_unset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fg = tmp_path / "FocusGuard"
    fg.mkdir()
    p = fg / "api_token.json"
    p.write_text(json.dumps({"token": "t", "openai_api_key": "from-file-only"}), encoding="utf-8")
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with patch.object(OpenAIClient, "_validate_api_key", return_value=True):
        c = OpenAIClient()
    assert c.api_key == "from-file-only"


def test_token_regeneration_preserves_openai_key(tmp_path: Path) -> None:
    token_dir = tmp_path / "FocusGuard"
    token_dir.mkdir()
    token_path = token_dir / "api_token.json"
    token_path.write_text(
        json.dumps({"openai_api_key": "preserve-me"}),
        encoding="utf-8",
    )
    mgr = APIAuthManager(token_dir=token_dir)
    mgr._generate_and_save()
    data = json.loads(token_path.read_text(encoding="utf-8"))
    assert data.get("openai_api_key") == "preserve-me"
    assert data.get("token")
    assert len(data["token"]) >= 32


def test_default_api_token_json_path_uses_programdata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    assert default_api_token_json_path() == tmp_path / "FocusGuard" / "api_token.json"
