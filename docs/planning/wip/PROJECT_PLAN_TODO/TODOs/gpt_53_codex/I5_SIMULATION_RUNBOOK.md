# I5 Simulation Runbook (Working/Distraction Automation)

## Purpose
Run deterministic and bounded-chaos simulations to validate enforcement behavior without requiring manual sessions each cycle.

## Artifacts
- Harness: `scripts/integration_tests/distraction_simulation_harness.py`
- Nightly runner: `scripts/integration_tests/run_distraction_simulation_nightly.py`
- Output reports: `data/simulation_reports/*.json`
- Loophole candidate mapping output: `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/I5_SIMULATION_LOPHOLE_CANDIDATES.md`

## Scenario Pack (Deterministic)
1. `scenario_focus_stable`
2. `scenario_repeated_distraction`
3. `scenario_override_lifecycle`
4. `scenario_offline_recovery`
5. `scenario_long_session_stability`

## Local deterministic run
```bash
python scripts/integration_tests/distraction_simulation_harness.py --dry-run --scenario all --output data/simulation_reports/local_deterministic.json
```

Expected:
- `total_errors = 0`
- All scenarios produce timeline records.

## Local bounded chaos run
```bash
python scripts/integration_tests/distraction_simulation_harness.py --dry-run --scenario all --chaos --chaos-probability 0.2 --output data/simulation_reports/local_chaos.json
```

Expected:
- Some controlled chaos injections may appear.
- Fail only if error rate exceeds harness threshold.

## Live runtime run (optional)
```bash
python scripts/integration_tests/distraction_simulation_harness.py --base-url http://127.0.0.1:3000 --token <admin-bearer-token> --scenario all --output data/simulation_reports/live_run.json
```

## Nightly runner
```bash
python scripts/integration_tests/run_distraction_simulation_nightly.py --project-root . --base-url http://127.0.0.1:3000 --dry-run
```

This emits two reports per nightly seed:
- deterministic report
- chaos report

And generates balanced-policy loophole mapping candidates:
- `I5_SIMULATION_LOPHOLE_CANDIDATES.md`

## Balanced mapping policy (approved)
- Deterministic scenario failure: create/update actionable loophole candidate immediately.
- Chaos scenario failure: create/update actionable candidate only when the same failure signature repeats across >=2 nightly runs (configurable threshold).

## Triage policy
- Deterministic failures are treated as regressions and triaged immediately.
- Chaos failures are triaged by frequency and mapped into `LOOPHOLE_TRACKER.md` if recurring.
- Include report path in loophole links for reproducibility.
