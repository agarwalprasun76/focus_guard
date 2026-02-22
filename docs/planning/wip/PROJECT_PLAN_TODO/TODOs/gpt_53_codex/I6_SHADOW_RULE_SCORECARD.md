# I6-03 Shadow-Mode Rule Scorecard

## Purpose
Evaluate candidate AI/rule suggestions in shadow mode before any active enforcement promotion.

## Run Metadata
- Date:
- Build/runtime:
- Scenario sources (manual + automated):
- Evaluator:

## Candidate Rule
- Rule ID:
- Rule description:
- Category (bypass/state-sync/UX/perf/recovery):
- Intended outcome:

## Metrics
| Metric | Definition | Value | Notes |
|---|---|---:|---|
| Precision | True positives / (true positives + false positives) |  |  |
| False Positive Rate | False positives / all negatives |  |  |
| Recall (optional) | True positives / all actual positives |  |  |
| Coverage | % sessions/scenarios where rule produced signal |  |  |

## Evidence Links
- Loophole IDs impacted:
- Simulation reports:
- Test/spec links:

## Promotion Gate
- [ ] Precision meets threshold
- [ ] FP rate acceptable for operator trust
- [ ] No critical regressions introduced
- [ ] Owner sign-off

Decision:
- [ ] Keep in shadow mode
- [ ] Promote to active policy
- [ ] Reject candidate

Rationale:
