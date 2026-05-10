# MVP Smoke Test (manual checklist)

**Automated inventory:** see `docs/planning/mvp/MVP_TEST_MATRIX.md` for all MVP-tier pytest, Vitest, Playwright, and smoke scripts. **One-shot baseline:** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mvp_test_baseline.ps1` (pytest + `mvp_smoke.ps1`; run while app is up for A1, or add `-SkipHttpSmoke` if services are down).

Run this when the Focus Guard app is **running** (tray + tab server + admin gateway). Goal: confirm Definition of Done for the MVP sprint without widening scope.

Reference: `docs/planning/mvp/INSTALL_WINDOWS.md` for ports and first-run context.

## Preconditions
- [ ] Windows 10/11; correct system date/time (avoids bogus log timestamps).
- [ ] `python -m focus_guard.main` (or packaged tray) running; tray icon present if applicable.
- [ ] Browser extension installed and connected (optional for some steps; required for full blocking smoke).
- [ ] If you used first-run onboarding: **Finish setup** (post-tray) **Run connection check** succeeded or only shows acceptable notices (dashboard reachable, tab server/admin health OK enough for smoke).

## A) Tab server (58392)
- [ ] Open `http://127.0.0.1:58392/api/health` — JSON shows healthy (or equivalent success).
- [ ] `GET /api/auth/status` — `token_exists: true` and `token_path` points under `%ProgramData%\FocusGuard\` when auth is enabled.

## B) Admin gateway + guardian UI (58393)
- [ ] Open `http://127.0.0.1:58393/admin` — SPA loads without console errors.
- [ ] If applicable: `http://127.0.0.1:58393/admin/health` and/or meta endpoint responds (per your deployment).

## C) Settings (remote management)
- [ ] From admin UI: view settings; change a **non-critical** setting and confirm persistence (reload page).
- [ ] If enforcement changes are tested: confirm password flow behaves as expected.

## D) Devices
- [ ] Devices list loads.
- [ ] Changing enforcement mode for a device succeeds or shows the expected password / error path.

## E) Dashboard
- [ ] Dashboard loads KPIs / charts without empty hard errors.
- [ ] `generated_at_utc` or equivalent freshness field present if exposed.

## F) Blocking + overrides (extension path)
- [ ] Visit a URL that should be blocked — block page or blocked behavior appears per policy.
- [ ] Request override (if enabled) — grant and usage behave as expected (no double-count on reopen).

## G) Feedback (Day 5 plumbing)
- [ ] Submit feedback linked to a real `decision_id` (or extension/blocked page path when wired).
- [ ] With bearer token from `%ProgramData%\FocusGuard\api_token.json`: `GET /api/feedback/blocking?limit=5` returns rows.

## H) Reporting
- [ ] From deployment entry or docs: send test email or trigger report path; confirm email or log shows non-empty normalized content (no crash on sparse stats).

## I) Install / onboarding sanity
- [ ] Fresh developer path still documented: `INSTALL_WINDOWS.md` matches actual command you use to start the app.

## Outcome
- **Pass:** all checked boxes for your target MVP profile (note any waived rows under “Waivers”).
- **Fail:** open a blocker issue / fix P0 only; park everything else in `FEATURE_REQUESTS_PARKING_LOT.md`.
