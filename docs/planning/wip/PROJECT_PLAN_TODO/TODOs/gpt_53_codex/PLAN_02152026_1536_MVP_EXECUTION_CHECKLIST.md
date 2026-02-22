# MVP Execution Checklist (Prioritized)

**Date:** 2026-02-15 15:36 (UTC-05:00)  
**Scope:** FocusGuard post-P4 execution priorities  
**Primary tracker to update as work completes:** `PROGRESS_TRACKER.md`

---

## How to use this plan

1. Work top-to-bottom by priority tier (P0 -> P1 -> P2).
2. For each completed item, add evidence (command + result + file/test links) to `PROGRESS_TRACKER.md`.
3. If an item reveals a defect, log/update it in `LOOPHOLE_TRACKER.md` before moving on.
4. Keep statuses synchronized across this file and the tracker.

---

## P0 - Required for a working MVP (Do now)

## P0-1 Packaged mutation confidence gap (L-003)
- [x] Extend packaged smoke coverage to include create/revoke mutation path assertions.
- [x] Run packaged verifier and packaged smoke.
- [x] Update L-003 status from `deferred` to evidence-backed state (`in_progress`/`fixed`/`verified`/`closed`).

**Current status (2026-02-15)**
- Mutation assertions were added in `admin_ui/e2e/packaged-runtime-smoke.spec.ts` (create/list/revoke flow).
- First packaged smoke run executed and failed in current environment:
  - `/admin/api/v1/meta` returned `404` on configured base URL.
  - `/admin/api/v1/auth/login` returned `401` with current packaged credentials.
- Runbook updated with packaged credential env vars and mutation-smoke prerequisites.

**Latest status (2026-02-16)**
- Packaged smoke is now green (`4 passed`) with valid `PACKAGED_ADMIN_*` env vars.
- Local runtime topology used for this validation:
  - admin gateway: `http://127.0.0.1:58393`
  - tab server upstream: `http://127.0.0.1:58392`
- L-003 moved to `verified` in `LOOPHOLE_TRACKER.md`.

**Exit evidence**
- Packaged commands and pass output added to `PROGRESS_TRACKER.md`.
- `LOOPHOLE_TRACKER.md` entry for L-003 updated with test links.

---

## P0-2 Runtime contract verification (source + packaged)
- [ ] Verify these endpoints in both lanes:
  - `/admin/health`
  - `/admin/api/v1/meta`
  - `/admin/api/v1/dashboard`
  - `/admin/api/v1/devices`
  - tab-server health from active deployment config host/port
- [ ] Confirm `/admin` SPA route + auth + dashboard/devices refresh behavior from clean launch.
- [ ] Capture evidence in `PROGRESS_TRACKER.md`.

**Exit evidence**
- Single evidence block with command list and pass/fail for source + packaged.
- Any mismatch logged as loophole with severity/repro/risk.

---

## P0-3 Clean Windows VM packaged validation
- [ ] Validate `FocusGuard.exe` on a clean Windows VM (no Python).
- [ ] Run minimum smoke: launch/tray, admin routes, blocking, override lifecycle, reporting.
- [ ] Record final VM results and close/open follow-up action accordingly.

**Exit evidence**
- Explicit pass/fail notes in `PROGRESS_TRACKER.md` for clean-VM lane.

---

## P0-4 Enforcement password activation check
- [ ] Set `config_password_hash` in deployment config.
- [ ] Verify mode-change API behavior:
  - no password -> denied
  - valid password -> success
- [ ] Re-run targeted packaged checks once with password active.

**Exit evidence**
- Security behavior and commands captured in tracker.

---

## P1 - Stabilization immediately after MVP

## P1-1 L-002 revisit decision
- [ ] Reproduce stale recovery message timing in controlled outage/recovery session.
- [ ] Decide and document one outcome: `close` / `tune` / `re-defer` (with date + rationale).
- [ ] Sync `LOOPHOLE_TRACKER.md` + `I6_BACKFILL_BASELINE.md` references.

## P1-2 Shadow Cycle 002
- [ ] Run next nightly cycle.
- [ ] Publish `I6_SHADOW_RULE_CYCLE_002.md`.
- [ ] Refresh top-5 queue in `LOOPHOLE_TRACKER.md`.

## P1-3 Tracker/governance consistency pass
- [ ] Add short runtime-contract source-of-truth note to tracker.
- [ ] Add cross-track note clarifying:
  - `opus_45` = historical deployment baseline + long-range roadmap
  - `gpt_53_codex` = active execution lane
- [ ] Ensure status/date headers are aligned in active docs.

## P1-4 Deferred hardening: non-admin startup warnings (hosts/incognito)
- [ ] Document expected non-admin warning behavior observed during `scripts/dev/start_tab_server.py` runs.
- [ ] Add operator guidance for when admin privileges are required:
  - hosts-file sync (`hosts_blocker`) writes
  - incognito/inprivate policy registry writes
- [ ] Decide one path and track closure:
  - keep as accepted non-admin warning (document-only), or
  - require elevated startup mode and verify warnings clear.

---

## P2 - Good to have / Later roadmap

- [ ] 6.1 Classification API Server
- [ ] 6.2 Frontend Configuration & Control App
- [ ] 6.3 Multi-device support
- [ ] 6.6 Analytics and insight engine expansion

> These are valuable but non-blocking for current MVP closure.

---

## Tracker update template (copy/paste)

Use this block in `PROGRESS_TRACKER.md` when closing an item:

```md
- Session <N> — <DATE> (<ITEM ID> completion):
  - Scope:
  - Commands run:
    - `<command>` -> `<result>`
  - Evidence files/tests:
    - `<path>`
  - Outcome:
    - `<status change + rationale>`
  - Follow-ups:
    - `<if any>`
```

---

## Suggested execution order

1. P0-1 (L-003)
2. P0-2 (runtime contract verification)
3. P0-3 (clean VM validation)
4. P0-4 (password activation check)
5. P1-1 (L-002 revisit)
6. P1-2 (Shadow Cycle 002)
7. P1-3 (tracker/governance cleanup)
8. P1-4 (non-admin warning hardening decision)
9. P2 items as capacity permits
