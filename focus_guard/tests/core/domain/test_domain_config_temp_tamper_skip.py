"""Confirm domain config under OS temp is treated as non-production for tamper SMTP."""

from __future__ import annotations

import tempfile
from pathlib import Path

from focus_guard.core.domain.domain_config_manager import DomainConfigManager


def test_config_under_tempdir_is_system_temp() -> None:
    root = tempfile.mkdtemp()
    cfg = Path(root) / "nested" / "domain_config.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    mgr = DomainConfigManager(config_path=cfg)
    assert mgr._config_is_under_system_temp() is True
