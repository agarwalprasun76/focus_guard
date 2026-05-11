"""Filesystem paths for bundled browser extension sources (MV3)."""

from __future__ import annotations

from pathlib import Path


def get_mv3_extension_source_dir() -> Path:
    """Directory containing ``manifest.json`` for Chrome/Edge **Load unpacked**.

    Resolved relative to the installed ``focus_guard`` package (repo checkout or pip install).
    """
    import focus_guard  # local package

    root = Path(focus_guard.__file__).resolve().parent
    return root / "core" / "browser" / "extension" / "webextension_mv3"


def mv3_extension_is_present() -> bool:
    d = get_mv3_extension_source_dir()
    return (d / "manifest.json").is_file()
