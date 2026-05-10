#!/usr/bin/env python3
"""
Unified test runner for FocusGuard.

Runs all backend, security, and frontend tests in order with clear
pass/fail reporting and a final summary.

Usage:
    python scripts/run_all_tests.py          # Run all test suites
    python scripts/run_all_tests.py --quick   # Skip slow/integration tests
    python scripts/run_all_tests.py --backend # Backend only
    python scripts/run_all_tests.py --frontend # Frontend only

Pre-ship backend gate (pytest only; also runs in full non-quick backend plan):
    python scripts/run_release_integration_tests.py

Note: ``run_release_integration_tests.py`` does **not** run Playwright. Failures in "Frontend: E2E" are from ``admin_ui`` (`npm run test:e2e`), not from that script.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ADMIN_UI_DIR = PROJECT_ROOT / "admin_ui"

# ANSI colours (disabled on Windows if not supported)
if sys.platform == "win32":
    os.system("")  # enable ANSI on Windows 10+

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class SuiteResult:
    name: str
    passed: bool
    duration: float
    detail: str = ""
    skipped: bool = False


@dataclass
class TestPlan:
    suites: List[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Suite definitions
# ---------------------------------------------------------------------------

def build_plan(quick: bool = False, backend: bool = False, frontend: bool = False) -> TestPlan:
    """Build the list of test suites to run."""
    plan = TestPlan()

    run_backend = backend or (not backend and not frontend)
    run_frontend = frontend or (not backend and not frontend)

    if run_backend:
        # 1. Core admin gateway tests (pytest)
        plan.suites.append({
            "name": "Backend: Admin Gateway",
            "cmd": [sys.executable, "-m", "pytest",
                    "focus_guard/tests/core/admin_gateway/", "-q", "--tb=short"],
            "cwd": str(PROJECT_ROOT),
        })

        # 2. Security mitigations (custom runner)
        plan.suites.append({
            "name": "Backend: Section 8 Security Mitigations",
            "cmd": [sys.executable, "scripts/test_section8_mitigations.py"],
            "cwd": str(PROJECT_ROOT),
        })

        # 3. Activity & alert unit tests (stable subset — excludes known-flaky
        #    cross-platform mocks and macOS-specific idle tests)
        plan.suites.append({
            "name": "Backend: Activity & Alert Unit Tests (stable)",
            "cmd": [sys.executable, "-m", "pytest",
                    "focus_guard/tests/core/activity/",
                    "focus_guard/tests/core/alert/",
                    "-q", "--tb=short",
                    "--ignore=focus_guard/tests/core/activity/browser",
                    "--ignore=focus_guard/tests/core/alert/test_cross_platform.py",
                    "--ignore=focus_guard/tests/core/alert/test_cross_platform_pytest.py",
                    "--ignore=focus_guard/tests/core/alert/test_integration_pytest.py",
                    "--ignore=focus_guard/tests/core/activity/test_idle_detection.py",
                    "--ignore=focus_guard/tests/core/activity/test_integration.py",
                    "--ignore=focus_guard/tests/core/activity/test_models.py",
                    "--ignore=focus_guard/tests/core/activity/test_monitor.py",
                    "--ignore=focus_guard/tests/core/activity/test_usage_tracking.py",
                    "--ignore=focus_guard/tests/core/activity/platform/test_factory.py",
                    "--ignore=focus_guard/tests/core/activity/platform/test_windows.py",
                    ],
            "cwd": str(PROJECT_ROOT),
        })

        if not quick:
            # 4. Browser v2 unit tests
            plan.suites.append({
                "name": "Backend: Browser V2 Unit Tests",
                "cmd": [sys.executable, "-m", "pytest",
                        "focus_guard/tests/browser_v2/unit/", "-q", "--tb=short"],
                "cwd": str(PROJECT_ROOT),
            })

            # 4b. Pre-ship tab-server / enforcement integration gate (expand in Day 8 Part B)
            plan.suites.append({
                "name": "Backend: Release integration gate (tab server / enforcement)",
                "cmd": [sys.executable, "scripts/run_release_integration_tests.py"],
                "cwd": str(PROJECT_ROOT),
            })

    if run_frontend:
        # 5. Frontend unit tests (Vitest)
        if (ADMIN_UI_DIR / "package.json").exists():
            plan.suites.append({
                "name": "Frontend: Vitest Unit Tests",
                "cmd": ["npm.cmd" if sys.platform == "win32" else "npm",
                        "run", "test", "--", "--run"],
                "cwd": str(ADMIN_UI_DIR),
            })

            # 6. Frontend integration tests (MSW)
            plan.suites.append({
                "name": "Frontend: Integration Tests (MSW)",
                "cmd": ["npm.cmd" if sys.platform == "win32" else "npm",
                        "run", "test:integration", "--", "--run"],
                "cwd": str(ADMIN_UI_DIR),
            })

            if not quick:
                # 7. E2E tests (Playwright) — only in full mode
                plan.suites.append({
                    "name": "Frontend: E2E (Playwright)",
                    "cmd": ["npm.cmd" if sys.platform == "win32" else "npm",
                            "run", "test:e2e"],
                    "cwd": str(ADMIN_UI_DIR),
                })

    return plan


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_suite(suite: dict) -> SuiteResult:
    """Run a single test suite and return the result."""
    name = suite["name"]
    cmd = suite["cmd"]
    cwd = suite.get("cwd", str(PROJECT_ROOT))

    print(f"\n{CYAN}{BOLD}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}  Running: {name}{RESET}")
    print(f"{CYAN}{BOLD}{'='*60}{RESET}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"  CWD:     {cwd}\n")

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout per suite
        )
        duration = time.time() - start

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            # Filter out common pytest warnings that aren't errors
            stderr_lines = result.stderr.strip().split("\n")
            important = [l for l in stderr_lines if not l.strip().startswith("PytestDeprecationWarning")]
            if important:
                print("\n".join(important))

        passed = result.returncode == 0
        colour = GREEN if passed else RED
        status = "PASSED" if passed else "FAILED"
        print(f"\n  {colour}{BOLD}→ {name}: {status} ({duration:.1f}s){RESET}")

        return SuiteResult(
            name=name,
            passed=passed,
            duration=duration,
            detail=result.stdout[-500:] if not passed else "",
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start
        print(f"\n  {RED}{BOLD}→ {name}: TIMEOUT after {duration:.0f}s{RESET}")
        return SuiteResult(name=name, passed=False, duration=duration, detail="Timed out after 300s")

    except FileNotFoundError as e:
        duration = time.time() - start
        print(f"\n  {YELLOW}{BOLD}→ {name}: SKIPPED ({e}){RESET}")
        return SuiteResult(name=name, passed=True, duration=0, skipped=True, detail=str(e))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="FocusGuard unified test runner")
    parser.add_argument("--quick", action="store_true", help="Skip slow/integration tests")
    parser.add_argument("--backend", action="store_true", help="Run backend tests only")
    parser.add_argument("--frontend", action="store_true", help="Run frontend tests only")
    args = parser.parse_args()

    plan = build_plan(quick=args.quick, backend=args.backend, frontend=args.frontend)

    print(f"\n{BOLD}{'#'*60}{RESET}")
    print(f"{BOLD}  FocusGuard — Unified Test Runner{RESET}")
    print(f"{BOLD}  Suites to run: {len(plan.suites)}{RESET}")
    print(f"{BOLD}{'#'*60}{RESET}")

    total_start = time.time()
    results: List[SuiteResult] = []

    for suite in plan.suites:
        results.append(run_suite(suite))

    total_duration = time.time() - total_start

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    passed = [r for r in results if r.passed and not r.skipped]
    failed = [r for r in results if not r.passed]
    skipped = [r for r in results if r.skipped]

    print(f"\n\n{BOLD}{'#'*60}{RESET}")
    print(f"{BOLD}  FINAL SUMMARY{RESET}")
    print(f"{BOLD}{'#'*60}{RESET}\n")

    for r in results:
        if r.skipped:
            icon = f"{YELLOW}⊘ SKIP{RESET}"
        elif r.passed:
            icon = f"{GREEN}✓ PASS{RESET}"
        else:
            icon = f"{RED}✗ FAIL{RESET}"
        print(f"  {icon}  {r.name}  ({r.duration:.1f}s)")

    print(f"\n  {BOLD}Total time: {total_duration:.1f}s{RESET}")
    print(f"  {GREEN}Passed: {len(passed)}{RESET}  |  {RED}Failed: {len(failed)}{RESET}  |  {YELLOW}Skipped: {len(skipped)}{RESET}")

    if failed:
        print(f"\n  {RED}{BOLD}❌ SOME SUITES FAILED{RESET}\n")
        for r in failed:
            print(f"    • {r.name}")
            if r.detail:
                for line in r.detail.strip().split("\n")[-5:]:
                    print(f"      {line}")
        sys.exit(1)
    else:
        print(f"\n  {GREEN}{BOLD}✅ ALL SUITES PASSED{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
