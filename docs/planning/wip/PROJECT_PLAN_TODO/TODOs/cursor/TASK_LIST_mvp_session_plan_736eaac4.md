# Task List — MVP Session Plan (736eaac4)

**Source**: [mvp_session_plan_736eaac4.plan.md](mvp_session_plan_736eaac4.plan.md)

---

## Phase 0: Verify & Stabilize (Do First)

| # | Task | Est. | Status |
|---|------|------|--------|
| 0.1 | Audit Windsurf session changes (server.py, settings_service.py, Settings.tsx, AppActivity.tsx) | — | Completed (plan) |
| 0.2 | Build admin UI (`npm run build`) + rebuild exe (PyInstaller) | — | Completed (plan) |
| 0.3 | Runtime verification — domains page, activity tab, dashboard hero, enforcement toggle | — | In progress |

---

## Phase 1: Email Report Enhancements (MVP-Critical)

| # | Task | Est. | Status |
|---|------|------|--------|
| 1.1 | Add admin console link to email (W-01) | 30 min | Pending |
| 1.2 | Add health check link + zero-activity warning (W-04) | 30 min | Pending |
| 1.3 | Richer email content — top apps, domains, blocked sites, overrides (W-06) | 2–3 h | Pending |
| 1.4 | Verify/fix multiple email recipients support (W-05) | 1–2 h | Pending |

---

## Phase 2: Admin Console UX (MVP-Critical)

| # | Task | Est. | Status |
|---|------|------|--------|
| 2.1 | Fix BUG-012: Devices page runtime error | 1 h | Pending |
| 2.2 | Fix BUG-015: Friction/override readability (Problem Sites, human-readable durations) | 1 h | Pending |
| 2.3 | Activity timeline (Phase A3) — GET /api/activity/timeline, bar chart in Dashboard | 3–4 h | Pending |
| 2.4 | Date/time range selector on dashboard (Phase A5) | 2 h | Pending |

---

## Phase 3: Blocked Page & Extension (MVP-Critical)

| # | Task | Est. | Status |
|---|------|------|--------|
| 3.1 | Budget context on blocked page (W-60 / BUG-018) — verify at runtime | 2 h | Pending |
| **3.2** | **Extension polling optimization (W-42)** — event-driven + 30 s heartbeat | **1–2 h** | **Done** |
| 3.3 | Classification feedback from blocked page (W-40) — “This is actually educational” button | 2 h | Pending |

---

## Phase 4: Classification & Blocking Pipeline

| # | Task | Est. | Status |
|---|------|------|--------|
| 4.1 Layer 1 | Classification feedback: POST /api/classification/feedback + blocked page button | 2 h | Pending |
| 4.1 Layer 2 | Ingestion: domain_config rules, auto always_allowed after N corrections | 1 day | Pending |
| 4.1 Layer 3 | Adaptive confidence per classifier (future) | 2 days | Pending |
| 4.2 | Persistent classification cache (SQLite-backed) | 1–2 days | Pending |
| 4.3 | Classification decision log | 1 day | Pending |
| 4.4 | LLM cost and latency tracking | 0.5 day | Pending |
| 4.5 | User-configurable classification rules from admin | 1–2 days | Pending |
| 4.6 | Additional domain classifiers (Netflix, Wikipedia, etc.) — future | 3–5 days | Pending |
| 4.7 | Time-based access schedules (W-70) — data model, ScheduleManager, API, UI | 3–5 days | Pending |
| 4.8 | School/Work calendar integration (W-71) — post-MVP | 1–2 weeks | Deferred |

---

## Phase 5: Doc Updates

| # | Task | Status |
|---|------|--------|
| 5 | Update 03_CURRENT_STATUS_AND_BUGS, 09_NEXT_SESSION, 11_WISHLIST, 00_INDEX | Pending |

---

## Session scope (from plan)

- **Minimum (4 h):** Phase 0 + 1.1–1.2 + Phase 5  
- **Target (6–8 h):** Minimum + 1.3–1.4 + 2.1–2.2 + 4.1 Layer 1  
- **Stretch (10 h+):** Target + 2.3–2.4 + 3.2 + 4.2  

---

## Notes

- 3.2 (W-42) completed: 5 s polling removed; tab snapshot sent on `onCreated`, `onUpdated`, `onRemoved`, `onActivated` (debounced 800 ms); 30 s heartbeat does lightweight connection check only. Extension store re-submission required after this change.
