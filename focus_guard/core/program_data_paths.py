"""Shared paths under Windows ``ProgramData\\FocusGuard`` (and equivalents).

Keeps tab-server token storage and optional LLM secrets in one admin-protected file.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_API_TOKEN_FILENAME = "api_token.json"
# Canonical field name; ``open_ai_api_key`` is accepted as a common typo / alternate spelling.
_OPENAI_KEY_FIELDS = ("openai_api_key", "open_ai_api_key")


def default_program_data_focusguard_dir() -> Path:
    return Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "FocusGuard"


def default_api_token_json_path() -> Path:
    return default_program_data_focusguard_dir() / _API_TOKEN_FILENAME


def read_openai_api_key_from_api_token_file(path: Optional[Path] = None) -> Optional[str]:
    """Return ``openai_api_key`` from ``api_token.json`` if present and non-empty.

    Intended resolution order (enforced in :class:`OpenAIClient`): explicit argument,
    ``OPENAI_API_KEY`` environment variable, then this file.

    The OpenAI key is stored in the same JSON document as the tab-server bearer token
    so deployers can keep machine-local secrets in one ProgramData file. The field is
    optional; if missing, LLM features fall back to env-only configuration.
    """
    token_path = path or default_api_token_json_path()
    if not token_path.is_file():
        return None
    try:
        with open(token_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = None
        for field in _OPENAI_KEY_FIELDS:
            raw = data.get(field)
            if isinstance(raw, str) and raw.strip():
                key = raw.strip()
                break
        if key:
            return key
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Could not read %s for OpenAI key: %s", token_path, e)
    return None
