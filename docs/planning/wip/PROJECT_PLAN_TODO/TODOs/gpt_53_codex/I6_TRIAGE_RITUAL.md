# I6-01 Loophole Triage Ritual

## Objective
Maintain a risk-score-driven Top-5 closure queue and avoid loophole noise overload.

## Cadence
- Daily async triage pass (10-15 min)
- Twice-weekly sync review (Core + QA + FE/BE owners)

## Inputs
- `LOOPHOLE_TRACKER.md`
- `I5_SIMULATION_LOPHOLE_CANDIDATES.md`
- Recent e2e/integration regressions

## Ritual Steps
1. Ingest new loopholes and simulation candidates.
2. Score each item using tracker rule:
   - `SeverityWeight x ReproWeight x ImpactWeight`
3. Update status (`new -> triaged -> in_progress -> fixed -> verified -> closed`, or `deferred` with rationale).
4. Refresh Top-5 queue ordered by risk score and release risk.
5. Link each active item to owner + target sprint.

## Balanced automation policy link
- Deterministic simulation failures map to immediate candidates.
- Chaos failures map only when signature repeats above threshold.

## Exit condition per cycle
- Top-5 has explicit owner + next action.
- Any deferred item has rationale and revisit date.
