# I6-04 Shadow-Mode Cycle 001 Review

## Run Metadata
- Date: 2026-02-15
- Build/runtime: Post-P4 source lane + dry-run nightly simulation reports
- Scenario sources: I4 pilot sessions + I5 nightly reports (`nightly_deterministic_20260215.json`, `nightly_chaos_20260215.json`)
- Evaluator: Core/QA

## Candidate Rule
- Rule ID: `shadow.recurring_chaos_signature_v1`
- Rule description: Surface loophole candidates only when chaos failure signature repeats across nightly lookback threshold.
- Category: recovery/resilience + loophole noise reduction
- Intended outcome: reduce false-positive loophole churn from one-off chaos noise while preserving actionable patterns.

## Metrics (sampled cycle)
| Metric | Definition | Value | Notes |
|---|---|---:|---|
| Precision | True positives / (true positives + false positives) | N/A | No promoted candidates this run, so precision is undefined for this sample. |
| False Positive Rate | False positives / all negatives | 0.00 | No recurring signatures crossed threshold. |
| Recall (optional) | True positives / all actual positives | N/A | No promoted shadow candidates to score in this sample. |
| Coverage | % sessions/scenarios where rule produced signal | 0.00 | Candidate rule produced no recurring chaos signal in this seed. |

## Evidence Links
- Loophole IDs impacted: `L-002`, `L-003` (triage context only)
- Simulation reports: `data/simulation_reports/nightly_deterministic_20260215.json`, `data/simulation_reports/nightly_chaos_20260215.json`
- Candidate output: `I5_SIMULATION_LOPHOLE_CANDIDATES.md`
- Runner implementation: `scripts/integration_tests/run_distraction_simulation_nightly.py`

## Promotion Gate
- [ ] Sufficient evaluable signal exists (promoted candidates > 0)
- [x] FP rate acceptable for operator trust
- [x] No critical regressions introduced
- [x] Owner sign-off

Decision:
- [x] Keep in shadow mode
- [ ] Promote to active policy
- [ ] Reject candidate

Rationale:
- Continue collecting additional nightly data before any stricter promotion behavior.
- Current balanced policy provides stable, low-noise candidate generation without suppressing deterministic regressions.
