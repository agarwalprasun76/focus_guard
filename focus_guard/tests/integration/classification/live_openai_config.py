"""Shared opt-in configuration for live OpenAI integration tests."""

from __future__ import annotations

import asyncio
import os

import pytest

from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
from focus_guard.core.program_data_paths import read_openai_api_key_from_api_token_file


def truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def has_openai_credentials() -> bool:
    if os.getenv("OPENAI_API_KEY", "").strip():
        return True
    return bool(read_openai_api_key_from_api_token_file())


def openai_live_configured() -> bool:
    """True when opt-in env is set and credentials exist (no API call)."""
    return truthy_env("FOCUS_GUARD_RUN_OPENAI_INTEGRATION") and has_openai_credentials()


SKIP_OPENAI_LIVE = (
    "Set FOCUS_GUARD_RUN_OPENAI_INTEGRATION=1 and "
    "OPENAI_API_KEY or ProgramData api_token.json openai_api_key"
)

SKIP_OPENAI_UNREACHABLE = (
    "OpenAI preflight failed (empty response). Often: 401 invalid/revoked key, or billing. "
    "Unset a bad OPENAI_API_KEY, update openai_api_key in "
    "%ProgramData%\\FocusGuard\\api_token.json, or check account credits. "
    "See ERROR logs from openai_client for detail."
)


def assert_openai_api_reachable() -> None:
    """Skip current test module/session if OpenAI is not configured or ping fails."""
    if not openai_live_configured():
        pytest.skip(SKIP_OPENAI_LIVE)
    try:

        async def ping() -> str | None:
            client = OpenAIClient(model="gpt-4o-mini")
            return await client.generate(
                prompt='Reply with JSON only: {"ok": true}',
                system_prompt="JSON only, no other text.",
            )

        out = asyncio.run(ping())
    except ValueError as e:
        pytest.skip(f"OpenAI client unavailable: {e}")
    if not (out and str(out).strip()):
        pytest.skip(SKIP_OPENAI_UNREACHABLE)
