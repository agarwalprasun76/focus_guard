#!/usr/bin/env python3
"""Verify OpenAI credentials using the same resolution order as the runtime.

Checks, in order:
  1. ``OPENAI_API_KEY`` environment variable
  2. ``openai_api_key`` / ``open_ai_api_key`` in ``%ProgramData%\\FocusGuard\\api_token.json``

Exits 0 on success, 1 on API failure, 2 if no key is configured.

Usage (from repo root)::

    python scripts/verify_openai_key.py
    python scripts/verify_openai_key.py --file-only   # ignore OPENAI_API_KEY; test api_token.json only
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from focus_guard.core.program_data_paths import (  # noqa: E402
    default_api_token_json_path,
    read_openai_api_key_from_api_token_file,
)


def _resolve_key(*, file_only: bool) -> tuple[str | None, str]:
    if file_only:
        k = read_openai_api_key_from_api_token_file()
        return k, "api_token.json"
    env = os.getenv("OPENAI_API_KEY")
    if env and env.strip():
        return env.strip(), "env"
    k = read_openai_api_key_from_api_token_file()
    return k, "api_token.json"


def main() -> int:
    p = argparse.ArgumentParser(description="Verify OpenAI key (env + ProgramData api_token.json).")
    p.add_argument(
        "--file-only",
        action="store_true",
        help="Ignore OPENAI_API_KEY; read only from %%ProgramData%%\\FocusGuard\\api_token.json",
    )
    args = p.parse_args()

    token_path = default_api_token_json_path()
    key, source = _resolve_key(file_only=args.file_only)
    if not key:
        print("No OpenAI API key found.")
        if args.file_only:
            print(f"  Expected openai_api_key in:\n  {token_path}")
        else:
            print(f"  Set OPENAI_API_KEY, or add openai_api_key to:\n  {token_path}")
        return 2

    prefix = key[:7] if len(key) >= 7 else key[: len(key)]
    suffix = key[-4:] if len(key) >= 4 else ""
    print(f"Using key: {prefix}...{suffix} (source: {source})")

    file_key = read_openai_api_key_from_api_token_file()
    if source == "env":
        print(
            "Note: OPENAI_API_KEY is set, so it wins over api_token.json (same order as the app). "
            "Remove or update that user/system env var if you intend to use only ProgramData."
        )
        if file_key and file_key != key:
            print(
                "Note: api_token.json contains a *different* key than OPENAI_API_KEY — "
                "you may be testing the wrong credential."
            )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Reply with exactly: ok"}],
            max_tokens=8,
        )
        text = (r.choices[0].message.content or "").strip()
        print(f"OpenAI gpt-4o-mini response: {text!r}")
        print("OK — key is valid and API reachable.")
        return 0
    except Exception as e:
        print(f"OpenAI request failed: {e}")
        err = str(e).lower()
        auth_like = "401" in str(e) or "invalid_api_key" in err or "incorrect api key" in err
        if not args.file_only and file_key and file_key != key and auth_like:
            print(
                "Hint: api_token.json has a different key than OPENAI_API_KEY. "
                "Retry with: py scripts\\verify_openai_key.py --file-only"
            )
        elif auth_like:
            print(
                "Hint: Confirm the key at https://platform.openai.com/account/api-keys "
                "and remove stale OPENAI_API_KEY if you rely on api_token.json."
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
