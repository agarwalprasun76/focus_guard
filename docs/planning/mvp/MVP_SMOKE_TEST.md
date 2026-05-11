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

### Enforcement modes (advisory / tracking vs enforcing)
- [ ] With deployment mode **Enforcing**: distraction URLs can show the blocked page / blocking behavior per policy (including declarativeNetRequest redirects synced from the tab server).
- [ ] With deployment mode **Advisory** or **Tracking**: the extension must **not** apply **network-layer** hard redirects for policy blocks alone — MV3 clears declarativeNetRequest rules unless mode is enforcing; `/api/should_block` reflects advisory semantics. Spot-check the same URL in **Chrome and Edge** with one Focus Guard process (parity).

## G) Feedback (Day 5 plumbing)
- [ ] Submit feedback linked to a real `decision_id` (or extension/blocked page path when wired).
- [ ] With bearer token from `%ProgramData%\FocusGuard\api_token.json`: `GET /api/feedback/blocking?limit=5` returns rows.

## H) Reporting
- [ ] From deployment entry or docs: send test email or trigger report path; confirm email or log shows non-empty normalized content (no crash on sparse stats).

## I) Install / onboarding sanity
- [ ] Fresh developer path still documented: `INSTALL_WINDOWS.md` matches actual command you use to start the app.

## J) Week 2 — Remote guardian access (Day 12)

Run only when you intentionally deploy **remote** access per `INSTALL_WINDOWS.md` § **Day 12 — Practical remote login runbook** and `ADR_001_REMOTE_ADMIN_ACCESS.md`.

- [ ] **Tunnel hostname:** From a **different network** (e.g. phone on cellular), open the HTTPS admin URL (e.g. `https://guardian.example.com/admin`); SPA loads and login works.
- [ ] **Origin allow-list:** If you had to set `FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS`, confirm edits persist after **restarting** Focus Guard (env read at process start).
- [ ] **No accidental naked forward:** Confirm you are **not** relying on a raw router port-forward to `58393` as the primary remote path (tunnel or screen-share path is OK).
- [ ] **API smoke (optional):** From a machine that can reach the tunnel URL:

  `python scripts/admin_gateway_smoke.py --password "<ADMIN_PASSWORD>" --base-url https://guardian.example.com`

  Expect exit code **0** and successful login + dashboard keys in output.

- [ ] **Multi-guardian caveat:** If two people edit rules remotely, refresh-before-save until **[FR-029]** ships (`FEATURE_REQUESTS_PARKING_LOT.md`).

## K) Week 2 — Metrics date range (Day 10) — quick spot check

- [ ] With app running: dashboard or tab-server stats accept a **date range** as documented in `MVP_TEST_MATRIX.md` (activity query contract); no SQL or empty-body hard failures when changing range in UI if exposed.

## Outcome
- **Pass:** all checked boxes for your target MVP profile (note any waived rows under “Waivers”).
- **Fail:** open a blocker issue / fix P0 only; park everything else in `FEATURE_REQUESTS_PARKING_LOT.md`.
