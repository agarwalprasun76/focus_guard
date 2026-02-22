"""Nightly runner for deterministic + bounded-chaos distraction simulations."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run nightly distraction simulations")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--base-url", default="http://127.0.0.1:58393")
    parser.add_argument("--token", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--chaos-probability", type=float, default=0.2)
    parser.add_argument("--chaos-repeat-threshold", type=int, default=2)
    parser.add_argument("--lookback-runs", type=int, default=7)
    parser.add_argument(
        "--loophole-candidates-output",
        default="docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/I5_SIMULATION_LOPHOLE_CANDIDATES.md",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _run(cmd: list[str], cwd: Path) -> int:
    print(" ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(cwd), check=False)
    return int(completed.returncode)


def _load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _failure_records(report: dict[str, Any]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for scenario in report.get("results", []):
        scenario_name = str(scenario.get("scenario", "unknown"))
        for step in scenario.get("timeline", []):
            if bool(step.get("ok", True)):
                continue
            action = str(step.get("action", "unknown"))
            error = str(step.get("error", "unknown-error"))
            signature = f"{scenario_name}|{action}|{error}"
            records.append(
                {
                    "scenario": scenario_name,
                    "action": action,
                    "error": error,
                    "signature": signature,
                }
            )
    return records


def _recurring_chaos_failures(reports: list[Path], threshold: int) -> list[dict[str, Any]]:
    by_signature: Counter[str] = Counter()
    exemplar: dict[str, dict[str, Any]] = {}

    for report_path in reports:
        report = _load_report(report_path)
        seen: set[str] = set()
        for rec in _failure_records(report):
            signature = rec["signature"]
            if signature in seen:
                continue
            seen.add(signature)
            by_signature[signature] += 1
            exemplar.setdefault(signature, rec)

    recurring: list[dict[str, Any]] = []
    for signature, count in by_signature.items():
        if count >= threshold:
            item = dict(exemplar[signature])
            item["count"] = count
            recurring.append(item)
    recurring.sort(key=lambda item: int(item["count"]), reverse=True)
    return recurring


def _write_loophole_candidates(
    output_path: Path,
    seed: int,
    deterministic: list[dict[str, str]],
    recurring_chaos: list[dict[str, Any]],
    repeat_threshold: int,
    lookback_runs: int,
    deterministic_report: Path,
    chaos_report: Path,
) -> None:
    lines: list[str] = [
        "# I5 Simulation Loophole Candidates",
        "",
        f"Run seed: {seed}",
        "",
        "Balanced policy:",
        "- Deterministic failures -> actionable candidate immediately",
        f"- Chaos failures -> actionable only when signature repeats in >= {repeat_threshold} nightly runs",
        "",
        "## Reports",
        f"- Deterministic: `{deterministic_report}`",
        f"- Chaos: `{chaos_report}`",
        "",
        "## Deterministic candidates (immediate)",
    ]

    if deterministic:
        lines.extend(
            [
                "",
                "| Scenario | Action | Error | Suggested Severity | Suggested Repro | Next Action |",
                "|---|---|---|---|---|---|",
            ]
        )
        for rec in deterministic:
            lines.append(
                f"| {rec['scenario']} | {rec['action']} | {rec['error']} | S2 | R3 | Create/update LOOPHOLE_TRACKER entry with report links |"
            )
    else:
        lines.extend(["", "- None in this run."])

    lines.extend([
        "",
        f"## Recurring chaos candidates (lookback={lookback_runs}, threshold={repeat_threshold})",
    ])
    if recurring_chaos:
        lines.extend(
            [
                "",
                "| Signature | Scenario | Action | Error | Repeat Count | Suggested Severity | Suggested Repro | Next Action |",
                "|---|---|---|---|---:|---|---|---|",
            ]
        )
        for rec in recurring_chaos:
            lines.append(
                f"| `{rec['signature']}` | {rec['scenario']} | {rec['action']} | {rec['error']} | {rec['count']} | S3 | R2 | Create/update LOOPHOLE_TRACKER if customer-relevant pattern |"
            )
    else:
        lines.extend(["", "- No recurring chaos signatures above threshold."])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()
    seed = args.seed or int(dt.datetime.now().strftime("%Y%m%d"))

    deterministic_report = root / "data" / "simulation_reports" / f"nightly_deterministic_{seed}.json"
    chaos_report = root / "data" / "simulation_reports" / f"nightly_chaos_{seed}.json"

    common = [
        "python",
        "scripts/integration_tests/distraction_simulation_harness.py",
        "--base-url",
        args.base_url,
        "--seed",
        str(seed),
    ]
    if args.token:
        common.extend(["--token", args.token])
    if args.dry_run:
        common.append("--dry-run")

    deterministic_rc = _run(common + ["--scenario", "all", "--output", str(deterministic_report)], cwd=root)
    chaos_rc = _run(
        common
        + [
            "--scenario",
            "all",
            "--chaos",
            "--chaos-probability",
            str(args.chaos_probability),
            "--output",
            str(chaos_report),
        ],
        cwd=root,
    )

    deterministic_failures = _failure_records(_load_report(deterministic_report))

    chaos_reports = sorted((root / "data" / "simulation_reports").glob("nightly_chaos_*.json"))
    if args.lookback_runs > 0:
        chaos_reports = chaos_reports[-args.lookback_runs :]
    recurring_chaos = _recurring_chaos_failures(chaos_reports, threshold=max(1, args.chaos_repeat_threshold))

    candidates_path = root / args.loophole_candidates_output
    _write_loophole_candidates(
        output_path=candidates_path,
        seed=seed,
        deterministic=deterministic_failures,
        recurring_chaos=recurring_chaos,
        repeat_threshold=max(1, args.chaos_repeat_threshold),
        lookback_runs=max(1, args.lookback_runs),
        deterministic_report=deterministic_report,
        chaos_report=chaos_report,
    )

    print("Nightly simulation reports:")
    print(f"- {deterministic_report}")
    print(f"- {chaos_report}")
    print(f"Loophole candidates: {candidates_path}")

    # Deterministic failures remain release-critical.
    if deterministic_rc != 0:
        return deterministic_rc

    # Chaos failures are tolerated if under harness threshold (non-zero means harness deemed too noisy/unstable).
    if chaos_rc != 0:
        return chaos_rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
