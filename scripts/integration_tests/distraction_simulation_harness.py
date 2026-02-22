"""I5 simulation harness for working/distraction behavior validation."""

from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError


@dataclass
class ScenarioEvent:
    action: str
    domain: str | None = None
    duration_seconds: int | None = None
    note: str | None = None


class DistractionSimulationHarness:
    def __init__(
        self,
        base_url: str,
        auth_token: str | None,
        dry_run: bool,
        seed: int,
        chaos_probability: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth_token = auth_token
        self._dry_run = dry_run
        self._rng = random.Random(seed)
        self._chaos_probability = max(0.0, min(1.0, chaos_probability))

    @staticmethod
    def deterministic_scenarios() -> dict[str, list[ScenarioEvent]]:
        return {
            "scenario_focus_stable": [
                ScenarioEvent("visit", "wikipedia.org"),
                ScenarioEvent("visit", "docs.python.org"),
                ScenarioEvent("check_state", note="stable-focus-state"),
            ],
            "scenario_repeated_distraction": [
                ScenarioEvent("visit", "youtube.com"),
                ScenarioEvent("visit", "reddit.com"),
                ScenarioEvent("visit", "youtube.com"),
                ScenarioEvent("check_state", note="repeated-distraction"),
            ],
            "scenario_override_lifecycle": [
                ScenarioEvent("create_override", "youtube.com", 180),
                ScenarioEvent("visit", "youtube.com"),
                ScenarioEvent("revoke_last_override", "youtube.com"),
                ScenarioEvent("check_state", note="override-lifecycle"),
            ],
            "scenario_offline_recovery": [
                ScenarioEvent("inject_offline", note="simulate-upstream-offline"),
                ScenarioEvent("check_state", note="expect-degraded"),
                ScenarioEvent("clear_offline", note="recover-upstream"),
                ScenarioEvent("check_state", note="expect-recovered"),
            ],
            "scenario_long_session_stability": [
                ScenarioEvent("visit", "wikipedia.org"),
                ScenarioEvent("visit", "youtube.com"),
                ScenarioEvent("create_override", "youtube.com", 120),
                ScenarioEvent("visit", "youtube.com"),
                ScenarioEvent("revoke_last_override", "youtube.com"),
                ScenarioEvent("visit", "docs.python.org"),
                ScenarioEvent("check_state", note="long-session-drift-check"),
            ],
        }

    def run_scenario(self, name: str, events: list[ScenarioEvent], chaos_mode: bool) -> dict[str, Any]:
        started = time.perf_counter()
        last_override_id: str | None = None

        stats = {
            "scenario": name,
            "events_total": len(events),
            "events_processed": 0,
            "overrides_created": 0,
            "overrides_revoked": 0,
            "errors": 0,
            "chaos_injections": 0,
            "timeline": [],
        }

        for idx, event in enumerate(events):
            chaos_applied = False
            if chaos_mode and event.action in {"visit", "create_override", "check_state"}:
                if self._rng.random() < self._chaos_probability:
                    chaos_applied = True
                    stats["chaos_injections"] += 1

            ok = True
            detail: dict[str, Any] = {"action": event.action, "domain": event.domain, "note": event.note}
            try:
                if chaos_applied:
                    raise TimeoutError("bounded chaos: simulated timeout")

                if event.action == "visit":
                    self._visit_domain(event.domain)
                elif event.action == "create_override":
                    created = self._create_override(event.domain, event.duration_seconds or 180)
                    last_override_id = created.get("id")
                    stats["overrides_created"] += 1
                    detail["override_id"] = last_override_id
                elif event.action == "revoke_last_override":
                    if last_override_id:
                        self._revoke_override(last_override_id)
                        stats["overrides_revoked"] += 1
                elif event.action == "check_state":
                    state = self._check_state()
                    detail["state"] = {
                        "has_device": "device" in state.get("dashboard", {}),
                        "exceptions_count": int(state.get("exceptions", {}).get("total", 0)),
                    }
                elif event.action in {"inject_offline", "clear_offline"}:
                    # In dry-run, represented as timeline markers. In live mode this is a no-op hook.
                    pass
                else:
                    raise ValueError(f"Unsupported action: {event.action}")
            except Exception as exc:  # noqa: BLE001
                ok = False
                stats["errors"] += 1
                detail["error"] = str(exc)

            stats["events_processed"] = idx + 1
            stats["timeline"].append({"step": idx + 1, "ok": ok, **detail})

        stats["duration_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
        return stats

    def _request_json(self, path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._dry_run:
            if path.endswith("/dashboard"):
                return {
                    "device": {"status": "online"},
                    "budget": {"percent": 45},
                }
            if path.endswith("/exceptions") and method == "GET":
                return {"exceptions": [], "total": 0, "limit": 50, "offset": 0}
            if path.endswith("/exceptions") and method == "POST":
                return {"id": f"sim_{int(self._rng.random() * 10000)}", "status": "active"}
            if "/exceptions/" in path and method == "DELETE":
                return {"revoked": True}
            return {}

        url = f"{self._base_url}{path}"
        headers = {"Content-Type": "application/json", "X-Request-ID": f"sim-{int(self._rng.random() * 1_000_000)}"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = request.Request(url=url, method=method, headers=headers, data=data)
        try:
            with request.urlopen(req, timeout=5.0) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} for {path}: {raw}") from exc
        except URLError as exc:
            raise RuntimeError(f"Network failure for {path}: {exc.reason}") from exc

    def _visit_domain(self, domain: str | None) -> None:
        _ = domain
        self._request_json("/admin/api/v1/dashboard?device_id=sim-device", method="GET")

    def _create_override(self, domain: str | None, duration: int) -> dict[str, Any]:
        return self._request_json(
            "/admin/api/v1/exceptions",
            method="POST",
            payload={"domain": domain or "youtube.com", "type": "temporary", "duration_seconds": duration},
        )

    def _revoke_override(self, override_id: str) -> dict[str, Any]:
        return self._request_json(f"/admin/api/v1/exceptions/{override_id}", method="DELETE")

    def _check_state(self) -> dict[str, Any]:
        return {
            "dashboard": self._request_json("/admin/api/v1/dashboard?device_id=sim-device", method="GET"),
            "exceptions": self._request_json("/admin/api/v1/exceptions?status=all&limit=50&offset=0", method="GET"),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run working/distraction simulation harness")
    parser.add_argument("--base-url", default="http://127.0.0.1:58393")
    parser.add_argument("--token", default=None, help="Optional admin bearer token for live mode")
    parser.add_argument("--scenario", default="all", help="Scenario name or 'all'")
    parser.add_argument("--chaos", action="store_true", help="Enable bounded chaos mode")
    parser.add_argument("--chaos-probability", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=20260214)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default="data/simulation_reports/latest_simulation_report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    harness = DistractionSimulationHarness(
        base_url=args.base_url,
        auth_token=args.token,
        dry_run=args.dry_run,
        seed=args.seed,
        chaos_probability=args.chaos_probability,
    )

    scenarios = harness.deterministic_scenarios()
    selected = scenarios if args.scenario == "all" else {args.scenario: scenarios[args.scenario]}

    results: list[dict[str, Any]] = []
    total_errors = 0
    total_chaos = 0
    for name, events in selected.items():
        result = harness.run_scenario(name=name, events=events, chaos_mode=args.chaos)
        total_errors += int(result["errors"])
        total_chaos += int(result["chaos_injections"])
        results.append(result)

    summary = {
        "seed": args.seed,
        "dry_run": args.dry_run,
        "chaos": args.chaos,
        "chaos_probability": args.chaos_probability,
        "scenarios": list(selected.keys()),
        "total_errors": total_errors,
        "total_chaos_injections": total_chaos,
        "results": results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))

    if not args.chaos and total_errors > 0:
        return 1
    if args.chaos and total_errors > max(1, int(sum(len(s) for s in selected.values()) * 0.4)):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
