# Feature Requests Parking Lot

## Purpose
Capture ideas, feature requests, and tangents during MVP execution without interrupting sprint focus.

## Rules
- Do not execute items in this file during the active MVP day unless explicitly re-prioritized.
- Add concise entries only (1-3 lines each).
- Revisit during end-of-day review or sprint planning.

## Prioritization Legend
- `P0` Critical for MVP completion
- `P1` High value after MVP
- `P2` Nice to have
- `P3` Long-term / exploratory

## Template

```md
### [FR-000]
- Date:
- Requested by:
- Title:
- Priority: P1
- Area: (blocking/classification/admin_ui/install/reporting/other)
- Problem:
- Proposed idea:
- Why not now:
- Earliest revisit day:
- Owner:
- Status: parked
```

## Parked Items

### [FR-001]
- Date:
- Requested by:
- Title:
- Priority: P2
- Area:
- Problem:
- Proposed idea:
- Why not now:
- Earliest revisit day:
- Owner:
- Status: parked

### [FR-002]
- Date:
- Requested by:
- Title:
- Priority: P2
- Area:
- Problem:
- Proposed idea:
- Why not now:
- Earliest revisit day:
- Owner:
- Status: parked

### [FR-003]
- Date: 2026-05-03
- Requested by: MVP Day 5 verification
- Title: Fix or audit `created_at_utc` on blocking feedback (and similar logs)
- Priority: P2
- Area: blocking / data integrity
- Problem: Feedback rows showed `created_at_utc` as a far-future Unix timestamp (e.g. during live `GET /api/feedback/blocking` checks), suggesting wrong host clock, mixed time bases, or a bug in how timestamps are written.
- Proposed idea: Audit all SQLite logs that use `time.time()` for `*_utc` columns; document expected semantics (UTC vs local); optionally use `datetime.now(timezone.utc)` and validate monotonic ordering; add a startup warning if system clock is wildly off.
- Why not now: MVP Day 5 scope was auth + feedback plumbing; not a blocker for linkage behavior.
- Earliest revisit day: post-MVP smoke / data hardening pass
- Owner:
- Status: parked

## Brainstorm intake (2026-05-03) — dog walk list

**How to read this:** Items below are merged from a single unordered brainstorm, then **sorted by suggested revisit priority** (P1 first). Each `[FR-xxx]` is the unit to pull into sprint planning.

### Categories (for filtering)

| Category | Themes you raised |
|----------|-------------------|
| **Remote admin & architecture** | Dashboard from other devices / iPhone; need hosted service or not; LAN vs tunnel vs cloud |
| **Multi-device & sync** | Manage several machines from one console; avoid races when two admins change rules quickly; “seamless” fleet view |
| **Classification & rules** | Rules-first vs LLM-first; hosted service for LLM/rules; easier blacklist/whitelist and blackout windows |
| **Install & OS** | Install as admin but track all users (multi-user Windows); MacBook compatibility |
| **Enforcement & product modes** | Track-only vs block vs disable blocking entirely (granularity beyond current modes) |
| **Reporting & analytics** | Reporting rule config; screen time; daily/weekly/monthly summaries; detect distraction-heavy time windows |
| **Real-time control** | Change app behavior from admin console with minimal delay |
| **UX & engineering hygiene** | Admin console UX pass; better debug logging; remove redundant code |

### Suggested priority stack (highest first)

1. **P1** — Fleet + remote admin architecture (answers “other devices”, “hosted?”, “multiple devices seamlessly”)  
2. **P1** — Real-time updates + multi-admin concurrency (versioning, conflict rules, event ordering)  
3. **P2** — Windows admin install + track all logged-in users  
4. **P2** — Enforcement / “off switch” product clarity (track / don’t block / disable blocking)  
5. **P2** — Rules vs LLM strategy + optional hosted classification/rule service  
6. **P2** — Reporting depth (config, screen time, periods, distraction windows)  
7. **P2** — Domain UX (blackout + whitelist)  
8. **P2** — Mobile-friendly / iPhone access to guardian UI  
9. **P3** — macOS client  
10. **P3** — Dedupe code, structured logging, admin UX polish

---

### [FR-004]
- Date: 2026-05-03
- Requested by: dog walk brainstorm
- Title: Fleet management + remote admin architecture (other devices, hosted or not)
- Priority: P1
- Area: admin_ui / deployment / architecture
- Problem: Guardian needs dashboard and rule changes from phones and other PCs; unclear whether a hosted relay is required vs secure LAN exposure or VPN.
- Proposed idea: Write a short target architecture doc (threat model + options: localhost-only, tailscale/VPN, self-hosted relay, full SaaS); define device identity, enrollment, and minimum viable “view all kids’ PCs” story.
- Why not now: Post-MVP; depends on security and compliance choices.
- Earliest revisit day: sprint planning after MVP freeze candidate
- Owner:
- Status: parked

### [FR-005]
- Date: 2026-05-03
- Requested by: dog walk brainstorm
- Title: Near-real-time admin changes + multi-admin concurrency (no races on quick updates)
- Priority: P1
- Area: admin_gateway / tab_server / sync
- Problem: Two admins or rapid successive updates could conflict; “almost real time” behavior changes need a clear consistency model.
- Proposed idea: Config versioning (etag / monotonic revision), last-write-wins vs merge rules, outbound event stream or poll cursor for clients; tab_server applies highest-approved revision only.
- Why not now: Requires protocol design and tests beyond MVP slice.
- Earliest revisit day: with FR-004 architecture choice
- Owner:
- Status: parked

### [FR-006]
- Date: 2026-05-03
- Requested by: dog walk brainstorm
- Title: Windows — install elevated (admin) but track activity for all users / sessions
- Priority: P2
- Area: install / Windows / activity
- Problem: Service or tray may run in a context that does not see other users’ desktops without explicit design.
- Proposed idea: Document supported deployment (per-user vs per-machine); if multi-user required, specify session 0 vs user-session components and data separation.
- Why not now: MVP assumes single primary user machine in many flows.
- Earliest revisit day: enterprise / family multi-account milestone
- Owner:
- Status: parked

### [FR-007]
- Date: 2026-05-03
- Requested by: dog walk brainstorm
- Title: Clearer enforcement modes — track, block, or disable blocking entirely
- Priority: P2
- Area: blocking / product
- Problem: Users want explicit “do not block at all” vs “track only” vs “enforce”; wording and guarantees must match implementation.
- Proposed idea: Product matrix doc + map to existing `enforcing` / `advisory` / `tracking` and any new global kill-switch; extension + tab_server behavior table.
- Why not now: Partially exists; needs UX copy and edge-case audit only if scope grows.
- Earliest revisit day: post-MVP settings pass
- Owner:
- Status: parked

### [FR-008]
- Date: 2026-05-03
- Requested by: dog walk brainstorm
- Title: Rules-first vs LLM-first classification + optional hosted rule/LLM service
- Priority: P2
- Area: classification / remote service
- Problem: Cost, latency, and explainability tension between deterministic rules and LLM escalation.
- Proposed idea: Feature flags per tier (rules-only, rules+LLM on demand, hosted classifier API); keep audit trail from decision log as contract.
- Why not now: MVP pipeline exists; hosted service is a larger product surface.
- Earliest revisit day: after remote config service milestone
- Owner:
- Status: parked

### [FR-009]
- Date: 2026-05-03
- Requested by: dog walk brainstorm
- Title: Reporting — configurable rules, screen time, and weekly/monthly summaries + distraction windows
- Priority: P2
- Area: reporting / analytics
- Problem: Parents want richer periods (weekly/monthly), screen-time style totals, and “when are they most distracted?” not just hourly/daily email.
- Proposed idea: Reporting profile schema (cadence, metrics, comparisons); aggregate from existing activity/decision logs; optional “distraction heatmap” time-of-day.
- Why not now: Reporting MVP baseline first; this expands scope.
- Earliest revisit day: reporting v2 milestone
- Owner:
- Status: parked

### [FR-010]
- Date: 2026-05-03
- Requested by: dog walk brainstorm
- Title: Domain UX — easy blackout windows and whitelist flows from admin console
- Priority: P2
- Area: admin_ui / domain rules
- Problem: Power users need fast allow/deny and time-based exceptions without editing JSON or many clicks.
- Proposed idea: Presets + bulk edit + “quiet hours” profile tied to domain lists; pipeline step for blackout when schedules land (see design doc 4.7).
- Why not now: Depends on schedule step and admin UX bandwidth.
- Earliest revisit day: after schedule / domain manager milestone
- Owner:
- Status: parked

### [FR-011]
- Date: 2026-05-03
- Requested by: dog walk brainstorm
- Title: Guardian dashboard usable on iPhone / small screens (responsive or PWA)
- Priority: P2
- Area: admin_ui
- Problem: “Accessible from other platforms” often means mobile web first, not a second native app immediately.
- Proposed idea: Responsive layout audit, touch targets, optional PWA manifest for “add to home screen”.
- Why not now: Desktop guardian MVP first.
- Earliest revisit day: after FR-004 narrows hosting path
- Owner:
- Status: parked

### [FR-012]
- Date: 2026-05-03
- Requested by: dog walk brainstorm
- Title: macOS application parity (tray, tab_server, extension integration)
- Priority: P3
- Area: install / macOS / cross-platform
- Problem: README claims cross-platform; Windows is the MVP path; Mac needs packaging and permission model (Screen Recording, network local server, etc.).
- Proposed idea: Mac MVP spike checklist (not full parity): build, sign/notarize story, extension messaging, paths for data dir.
- Why not now: Windows MVP delivery first.
- Earliest revisit day: post-Windows MVP stabilization
- Owner:
- Status: parked

### [FR-013]
- Date: 2026-05-03
- Requested by: dog walk brainstorm
- Title: Engineering hygiene — redundant code removal, structured debug logging, admin UX review
- Priority: P3
- Area: engineering / admin_ui
- Problem: Velocity and supportability suffer when dead paths and noisy logs accumulate.
- Proposed idea: Scheduled “debt day”: static analysis for unused modules, log level policy, admin console heuristic UX review with 2–3 guardian personas.
- Why not now: Continuous background work; not a single shippable feature.
- Earliest revisit day: any maintenance sprint
- Owner:
- Status: parked

### [FR-014]
- Date: 2026-05-03
- Requested by: MVP test matrix / Day 6 baseline consolidation
- Title: Admin gateway tests — single canonical directory + optional `mvp` pytest markers
- Priority: P2
- Area: admin_gateway / testing / CI
- Problem: Gateway tests live in **two** trees, which confuses “where do I add a test?” and risks duplicate or diverging assertions. Tier A of `MVP_TEST_MATRIX.md` currently runs both on purpose until this is fixed. Optional: no `mvp` marker yet, so “run only MVP slice” is path-based, not `-m mvp`.
- **Current layout (resume context):**
  - **Package-local (preferred long-term):** `focus_guard/core/admin_gateway/tests/` — contains at least `test_dashboard_service.py`, `test_devices_service.py`, `test_settings_service.py` (settings tests exist **only** here today).
  - **Legacy / broader suite:** `focus_guard/tests/core/admin_gateway/` — **13** modules including overlapping `test_dashboard_service.py` and `test_devices_service.py`, plus auth, API contract, origin safeguards, performance, fault injection, real tab server, etc.
  - **Automation today:** `scripts/run_mvp_test_baseline.ps1` runs A3 = entire package-local dir; A5 = only the two legacy files that overlap names (dashboard + devices). Reporting is separate (A4).
- **Dedupe work plan (no behavior change — preserve or merge assertions, then delete duplicates):**
  1. Pick **one canonical root:** recommend `focus_guard/core/admin_gateway/tests/` for all gateway-focused tests (next to implementation).
  2. For **each overlapping pair** (`test_dashboard_service.py`, `test_devices_service.py`): open both files; merge any unique test cases / mocks into the canonical file; run `pytest` on both paths until green; **delete** the duplicate file from the non-canonical tree (or leave a one-line shim file that re-exports tests only if tooling requires — avoid if possible).
  3. **Migrate remaining** modules from `focus_guard/tests/core/admin_gateway/` into `focus_guard/core/admin_gateway/tests/` in **small PRs** (e.g. auth, then exceptions, then contract) to keep reviewable diffs; after each batch, `grep` for old imports and update any `conftest.py` / path references.
  4. Update **docs only:** `MVP_TEST_MATRIX.md` Tier A table, `run_mvp_test_baseline.ps1` (drop A5 once redundant), `MVP_SPRINT_MASTER_PLAN.md` if it references paths; search repo for `tests/core/admin_gateway` string literals.
  5. Confirm CI / local habit: `python -m pytest focus_guard/core/admin_gateway/tests -q` covers everything that used to live under the legacy tree.
- **Optional: pytest markers (finer filtering):**
  1. In `pytest.ini`, register markers under `[pytest]` → `markers =` (e.g. `mvp: Tier A regression slice`, `slow: integration / long`, `requires_network: external calls`) to avoid `PytestUnknownMarkWarning`.
  2. Add `@pytest.mark.mvp` only to tests that **must** gate PRs (subset of tab_server + gateway service tests); document `pytest -m mvp` in `MVP_TEST_MATRIX.md` and optionally add `run_mvp_test_baseline.ps1 -PytestMark mvp` later.
  3. Do **not** mark the entire legacy admin_gateway tree `mvp` until moved or triaged — otherwise `-m mvp` stays as wide as today’s path list.
- Why not now: MVP Day 6 closure prioritizes smoke + checklist; dedupe is mechanical and review-heavy without user-visible benefit in one day.
- Earliest revisit day: first “test hygiene” sprint after MVP freeze, or when adding a third duplicate service test file triggers pain.
- Owner:
- Status: parked

### [FR-015]
- Date: 2026-05-10
- Requested by: Week 2 architecture review
- Title: Browser store release automation (Chrome + Edge extension packaging/version checks)
- Priority: P2
- Area: extension / release / CI
- Problem: Extension distribution is currently link/manual oriented; no repeatable pre-publish checks for version parity and package integrity.
- Proposed idea: Add CI scripts for extension manifest version bump validation, deterministic package output checks, and release checklist artifacts for Chrome + Edge stores.
- Why not now: Not required to run current MVP in local-first mode.
- Earliest revisit day: Week 2+ release-hardening sprint
- Owner:
- Status: parked

### [FR-016]
- Date: 2026-05-10
- Requested by: Week 2 architecture review
- Title: Remote admin access policy bundle (tunnel + firewall + session hardening playbook)
- Priority: P2
- Area: deployment / security / admin_gateway
- Problem: Even after choosing a remote-access path, operators need a safe and repeatable runbook to avoid opening raw ports insecurely.
- Proposed idea: Provide scripts/docs for low-cost secure access (e.g., Tailscale/Cloudflare Tunnel), firewall defaults, allowed-origins guidance, and admin session timeout policy.
- Why not now: Depends on final remote-hosting architecture decision and threat model acceptance.
- Earliest revisit day: after Week 2 required remote architecture tasks
- Owner:
- Status: parked

### [FR-017]
- Date: 2026-05-10
- Requested by: Week 2 architecture review
- Title: Long-term metrics export pipeline (SQLite -> low-cost analytics store)
- Priority: P2
- Area: analytics / data platform
- Problem: Current metrics are queryable locally but difficult to aggregate historically across devices or long retention windows.
- Proposed idea: Add scheduled export from local SQLite metrics to a low-cost central store (managed Postgres, object storage + Parquet, or similar) with basic backfill support.
- Why not now: MVP dashboards can operate from local data; this is a scale/ops enhancement.
- Earliest revisit day: after Week 2 required metrics API + schema tasks
- Owner:
- Status: parked


### [FR-018]
- Date: 2026-05-10
- Requested by: Week 2 architecture review
- Title: Calendar integration with google calendar etc
- Priority: P3
- Area: monitoring and blocking
- Problem: Current approach is not aware of what the person has going on and blocking decisions cannot be contextualized.
- Proposed idea: Add ability to synch with the calendar and use that to guide what tools/apps/websites should be available.
- Why not now: Not needed for MVP but an additional nice to have feature
- Owner:
- Status: parked

## Daily Review Checklist
- [ ] Any new tangent captured here instead of being implemented immediately
- [ ] Any parked item upgraded to P0 (explicit decision only)
- [ ] Next day scope remains unchanged unless P0 blocker

