"""Run deterministic packaged-lane workflow commands for admin runtime validation."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Step:
    name: str
    command: list[str]
    cwd: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run packaged lane workflow")
    parser.add_argument("--project-root", default=".", help="Project root path")
    parser.add_argument("--skip-build", action="store_true", help="Skip build steps")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument(
        "--runtime-base-url",
        default="http://127.0.0.1:58393",
        help="Base URL for packaged runtime verification",
    )
    return parser.parse_args()


def _run_step(step: Step, dry_run: bool) -> None:
    pretty = " ".join(shlex.quote(p) for p in step.command)
    print(f"\n[{step.name}]\n  cwd: {step.cwd}\n  cmd: {pretty}")
    if dry_run:
        return
    subprocess.run(step.command, cwd=str(step.cwd), check=True)


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()
    admin_ui = root / "admin_ui"

    steps: list[Step] = []
    if not args.skip_build:
        steps.extend(
            [
                Step("Build admin UI", ["npm.cmd", "run", "build"], admin_ui),
                Step(
                    "Export admin gateway OpenAPI",
                    ["python", "scripts/dev/export_admin_gateway_openapi.py"],
                    root,
                ),
                Step(
                    "Build executable",
                    ["python", "-m", "focus_guard.deployment.build_exe", "--name", "FocusGuardService"],
                    root,
                ),
            ]
        )

    steps.extend(
        [
            Step(
                "Verify packaged runtime HTTP endpoints",
                [
                    "python",
                    "scripts/dev/verify_packaged_admin_runtime.py",
                    "--base-url",
                    args.runtime_base_url,
                ],
                root,
            ),
            Step(
                "Run packaged Playwright smoke",
                ["npm.cmd", "run", "test:e2e:packaged:smoke"],
                admin_ui,
            ),
        ]
    )

    try:
        for step in steps:
            _run_step(step, dry_run=args.dry_run)
    except subprocess.CalledProcessError as exc:
        print(f"\nFAILED: {exc}")
        return 1

    print("\nPackaged lane workflow completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
