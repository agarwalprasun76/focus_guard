#!/usr/bin/env python3
"""
Release / pre-ship integration gate for Focus Guard backend.

Runs pytest targets that should pass before tagging or publishing a build.
Intentionally stricter than ``--quick`` unit slices: includes tab-server
enforcement-mode contracts and core blocking tests. Expand this list as
Day 8 Part B adds coverage (Chrome vs Edge harness, full pipeline, etc.).

Usage:
    python scripts/run_release_integration_tests.py
    python scripts/run_release_integration_tests.py --verbose
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Keep paths explicit so new slow tests are opt-in for this gate.
RELEASE_TARGETS = [
    "focus_guard/tests/integration/tab_server/",
    "focus_guard/core/browser_v2/tab_server/tests/test_blocking_pipeline.py",
    "focus_guard/core/browser_v2/tab_server/tests/test_blocking_decision_log.py",
    "focus_guard/core/browser_v2/tab_server/tests/test_override_flow.py",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Release integration pytest gate")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Pass -v to pytest",
    )
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "pytest", *RELEASE_TARGETS, "--tb=short"]
    if args.verbose:
        cmd.append("-v")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
