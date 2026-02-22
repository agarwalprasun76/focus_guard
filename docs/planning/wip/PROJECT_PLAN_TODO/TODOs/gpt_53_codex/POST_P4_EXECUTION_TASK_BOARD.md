# FocusGuard UX — Post-P4 Integration Concrete Task Board

**Created:** 2026-02-14  
**Scope:** Frontend/Backend seamless integration, packaged-runtime validation, loophole-driven hardening  
**Primary References:**
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/POST_P4_INTEGRATION_AND_TEST_STRATEGY.md`
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/LOOPHOLE_TRACKER.md`
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/PROGRESS_TRACKER.md`

---

## 0) Objective and Boundaries

### Objective
Ship a robust post-P4 integration system where:
1. Frontend and backend contracts remain synchronized.
2. Source and packaged (`.exe`) runtime behavior are both validated.
3. Automated tests catch the majority of regressions.
4. Manual testing focuses on novel edge cases.
5. Loopholes are tracked, prioritized, and closed systematically.

### Out of Scope (for this board)
- Full production MLOps platform for policy models.
- Real-time websocket streaming rewrite (polling remains acceptable unless required by a task).
- Cross-platform installer redesign beyond Windows-first path.

---

## 1) Phase Overview

| Phase | Name | Goal | Exit Gate |
|---|---|---|---|
| I0 | Contract + Runtime Foundations | Lock FE/BE compatibility and observability primitives | Typed contracts + compatibility matrix + correlation IDs live |
| I1 | Automated FE/BE Integration Expansion | Raise automated confidence on critical paths and consistency checks | PR/nightly gate packs stable |
| I2 | Packaged Lane Automation (`.exe`) | Validate real packaged runtime as release truth lane | Packaged smoke stage reproducible |
| I3 | Resilience + Fault Injection | Verify graceful behavior under upstream instability | Fault-injection suite + degraded UX assertions pass |
| I4 | Manual Frontend + Live Distraction Validation | Structured human sessions to discover unknown unknowns | Manual charters executed and findings triaged |
| I5 | Automated Working/Distraction Simulation | Scripted behavior simulations for enforcement confidence | Scenario harness in nightly runs |
| I6 | Loophole Closure + AI Shadow Rules | Risk-based hardening with controlled AI/rule evolution | Top loopholes closed; shadow-mode metrics reviewed |

---

## 2) Task Board by Phase

## I0 — Contract + Runtime Foundations (3-4 days)

### Deliverables
- Generated or synchronized FE API types from backend schema.
- FE/BE compatibility matrix and capability handshake.
- Correlation ID propagation in FE->BE request path.
- UI readiness/degraded state model.

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| I0-01 | Define backend API schema export and generation workflow | Backend/FE | None | 4h | Scripted schema->TS generation path |
| I0-02 | Add CI guard for API contract drift | QA/FE | I0-01 | 3h | CI check failing on stale generated client/types |
| I0-03 | Add capabilities/meta endpoint for FE negotiation | Backend | I0-01 | 3h | `/admin/api/v1/meta` (or equivalent) contract |
| I0-04 | Implement FE capability gating for optional features | Frontend | I0-03 | 4h | Capability-aware UI toggles/guards |
| I0-05 | Add `X-Request-ID` propagation and structured logging fields | FE/BE | I0-01 | 4h | Traceable FE/BE request chain |
| I0-06 | Add gateway/tab-server/enforcement readiness states in UI | Frontend | I0-04 | 5h | Visible status + recovery actions |

### Acceptance Criteria
- [x] FE build consumes current backend contract types without manual shape edits
- [x] Contract drift is detected automatically in CI
- [x] Errors can be traced end-to-end via request ID
- [x] User can distinguish gateway-up vs tab-server-down conditions from UI

---

## I1 — Automated FE/BE Integration Expansion (3-4 days)

### Deliverables
- Expanded contract + integration tests for critical workflows.
- Cross-endpoint consistency checks (state coherence).
- Stable PR gate and nightly pack.

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| I1-01 | Expand MSW integration coverage for auth/session expiry and degraded flows | FE/QA | I0-01 | 4h | `admin_ui/src/integration/*.integration.test.ts` additions |
| I1-02 | Expand admin gateway integration tests for consistency checks | Backend/QA | I0-03 | 5h | pytest coverage for action->state coherence |
| I1-03 | Add Playwright assertions for degraded/readiness UI states | FE/QA | I0-06 | 4h | e2e checks for actionable status messaging |
| I1-04 | Define and enforce PR gate command pack | Core/QA | I1-01..I1-03 | 2h | Documented + scriptable gate pack |
| I1-05 | Define nightly broad integration pack | Core/QA | I1-04 | 2h | Scheduled test suite definition |

### Acceptance Criteria
- [x] Critical mutation and dashboard flows covered in contract/integration/e2e layers
- [x] Post-action state consistency checks pass
- [x] PR gate is reproducible locally and in CI

---

## I2 — Packaged Lane Automation (`.exe`) (3-4 days)

### Deliverables
- Rebuildable packaged lane test workflow.
- Packaged smoke script + Playwright packaged profile.
- Release rule enforcing source lane + packaged lane pass.

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| I2-01 | Standardize `.exe` rebuild workflow for test runs | Backend | I1-04 | 4h | Build steps + invocation doc/script |
| I2-02 | Add packaged-runtime startup verification script | Backend/QA | I2-01 | 3h | Health/admin route + asset path checks |
| I2-03 | Add packaged Playwright smoke profile | FE/QA | I2-02 | 5h | Playwright config/spec for packaged runtime URL |
| I2-04 | Add packaged lane stage to release pipeline checklist | Core/QA | I2-03 | 2h | Promotion checklist update |

### Acceptance Criteria
- [x] Packaged runtime can be rebuilt and started deterministically
- [x] Packaged smoke suite validates `/admin` UX and `/admin/api/*` behavior
- [x] Candidate release is blocked when packaged lane fails

---

## I3 — Resilience + Fault Injection (3-5 days)

### Deliverables
- Fault-injection suite between gateway and tab server.
- UI degraded/recovery behavior assertions.
- Long-session stability checks.

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| I3-01 | Add upstream fault injector scenarios (latency/timeout/reset) | Backend/QA | I1-02 | 5h | Injectable test harness hooks |
| I3-02 | Add FE retry/backoff and stale-state assertions in e2e | FE/QA | I3-01 | 4h | e2e degraded/recovery validation |
| I3-03 | Add long-session drift test (multi-hour or accelerated sim) | QA/Backend | I3-01 | 4h | Stability metrics + pass/fail thresholds |

### Acceptance Criteria
- [x] System shows correct degraded messaging during upstream faults
- [x] Recovery path clears stale state without manual page reload
- [x] Long-session checks do not reveal state drift regressions

---

## I4 — Manual Frontend + Live Distraction Validation (ongoing per RC)

### Deliverables
- Repeatable manual frontend charter.
- Repeatable live distraction session protocol.
- Findings logged in loophole tracker with risk scoring.

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| I4-01 | Finalize manual frontend checklist (auth/dashboard/exceptions/mobile) | FE/QA | I1-03 | 2h | RC manual checklist |
| I4-02 | Finalize live distraction session sheet (timeline+expected vs actual) | QA | I3-02 | 2h | Observer template |
| I4-03 | Run 2 pilot manual sessions and triage findings | QA/Core | I4-01,I4-02 | 4h | Initial loopholes + triage outcomes |

### Acceptance Criteria
- [x] Manual charters are concise and repeatable
- [x] Manual findings enter loophole tracker same day
- [x] Manual reports primarily surface edge cases, not baseline breakage

---

## I5 — Automated Working/Distraction Simulation (4-6 days)

### Deliverables
- Simulation harness for behavior-driven enforcement tests.
- Deterministic scenario suite + bounded chaos mode.
- Nightly simulation execution.

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| I5-01 | Build simulation harness v1 for visit/override/offline patterns | Backend/QA | I3-01 | 6h | Scenario runner module |
| I5-02 | Implement deterministic scenario pack (5 core scenarios) | Backend/QA | I5-01 | 5h | Scenario definitions + expected assertions |
| I5-03 | Add bounded chaos mode and reporting summary | QA | I5-02 | 4h | Nightly stress variant |
| I5-04 | Wire harness into nightly pipeline/runbook | Core/QA | I5-03 | 3h | Nightly job + docs |

### Acceptance Criteria
- [x] Deterministic scenarios are reproducible locally and in nightly runs
- [x] Chaos mode reveals issues without overwhelming false positives
- [x] Scenario failures map to actionable loophole entries

---

## I6 — Loophole Closure + AI Shadow Rules (ongoing)

### Deliverables
- Active loophole triage cadence with top-5 focus.
- Risk-score-driven closure workflow.
- Shadow-mode AI/rule experiment with precision metrics.

### Tasks

| ID | Task | Owner | Depends On | Est. | Output |
|---|---|---|---|---:|---|
| I6-01 | Enforce loophole scoring and top-5 triage ritual | Core/QA | I4-03 | 2h setup + ongoing | Prioritized closure queue |
| I6-02 | Backfill loopholes from recent sessions/tests | Core | I6-01 | 3h | Seeded tracker quality baseline |
| I6-03 | Define shadow-mode rule evaluation metrics (precision/FP rate) | Core/Backend | I5-02 | 3h | AI/rule scorecard |
| I6-04 | Run first shadow-mode cycle and review promotion readiness | Core | I6-03 | 4h | Go/no-go on rule promotion |

### Acceptance Criteria
- [x] Top loopholes are closed or explicitly deferred with rationale
- [x] Loophole tracker links each closure to tests/commits
- [x] Shadow-mode metrics are reported before any active enforcement promotion

---

## 3) Requested Test Categories Mapped to Tasks

| Requested Category | Primary Phases | Core Tasks |
|---|---|---|
| 1) Automated UI + backend integration tests | I1, I2, I3 | I1-01..I1-05, I2-02..I2-04, I3-01..I3-02 |
| 2) Manual frontend user tests | I4 | I4-01, I4-03 |
| 3) Manual working/distraction tests | I4 | I4-02, I4-03 |
| 4) Automated working/distraction tests | I5 | I5-01..I5-04 |

---

## 4) Risks and Mitigations (Post-P4)

| Risk | Impact | Mitigation | Trigger |
|---|---|---|---|
| Contract drift FE vs BE | Runtime bugs/rework | I0-01 + I0-02 CI drift guard | API change without generated type update |
| Packaged lane differs from source lane | Release regressions in real installs | I2 packaged lane gate | `.exe` smoke fails while source tests pass |
| False confidence from shallow tests | Production loopholes | I1 cross-endpoint checks + I5 simulation | Repeated bugs escaping PR gate |
| Loophole overload/noise | Team thrash, slow fixes | I6 risk scoring + top-5 discipline | >20 open issues without prioritization |
| Overfitting exception handlers | Fragile behavior | I6 shadow-mode policy approach | Repeated one-off fixes for similar patterns |

---

## 5) Suggested File Targets (Initial)

### Planning/Tracking
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/POST_P4_INTEGRATION_AND_TEST_STRATEGY.md`
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/POST_P4_EXECUTION_TASK_BOARD.md`
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/LOOPHOLE_TRACKER.md`
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/PROGRESS_TRACKER.md`

### Backend/Gateway
- `focus_guard/core/admin_gateway/app.py`
- `focus_guard/core/admin_gateway/dependencies.py`
- `focus_guard/core/admin_gateway/services/*.py`
- `focus_guard/tests/core/admin_gateway/*.py`

### Frontend/Admin UI
- `admin_ui/src/api/*.ts`
- `admin_ui/src/integration/*.integration.test.ts`
- `admin_ui/e2e/*.spec.ts`
- `admin_ui/src/views/*.tsx`

### Packaging
- `focus_guard/deployment/build_exe.py`
- `deployment/application/windows/specs/*.spec`
- `docs/planning/wip/PROJECT_PLAN_TODO/TODOs/gpt_53_codex/P4_07_PACKAGING_INTEGRATION_RUNBOOK.md`

---

## 6) Execution Checklist (Quick Start)

### Week 1
- [ ] Complete I0-01..I0-06
- [ ] Complete I1-01..I1-03
- [ ] Start I2-01..I2-02

### Week 2
- [ ] Complete I1-04..I1-05
- [ ] Complete I2-03..I2-04
- [ ] Complete I3-01..I3-03
- [ ] Complete I4-01..I4-03

### Week 3
- [ ] Complete I5-01..I5-04
- [ ] Complete I6-01..I6-04
- [ ] Consolidate loophole closure report + next-cycle priorities

---

## 7) Definition of Done — Post-P4 Integration Cycle

This cycle is done when all are true:
- [ ] FE/BE contract drift is automatically detected in CI
- [ ] Source lane + packaged lane both gate candidate releases
- [ ] Fault/degraded behavior is tested and user-visible states are actionable
- [ ] Manual sessions mainly surface edge cases, not baseline regressions
- [ ] Loophole tracker is active, prioritized, and linked to mitigation tests/fixes
- [ ] At least one shadow-mode AI/rule experiment reports precision metrics
