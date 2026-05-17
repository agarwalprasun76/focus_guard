# Post-MVP user stories (executable backlog)

**Source:** Parking-lot comments (2026-05-11) + activity-monitor / admin-settings code review.  
**Related:** `FEATURE_REQUESTS_PARKING_LOT.md` **[FR-031]**–**[FR-036]**; activity module `focus_guard/core/activity/`; screenshots `focus_guard/core/browser_v2/tab_server/screenshot_service.py`.

**How to use:** Pull stories into a sprint by ID. Each story has acceptance criteria (AC), technical notes, and dependencies. Order within an epic is suggested.

---

## Epic A — Admin settings bugs (guardian console)

### US-A1 · Fix master Daily Distraction Budget not persisting

| Field | Value |
|-------|--------|
| **FR** | [FR-031] |
| **Priority** | P0 |
| **Estimate** | 0.5–1 day |

**User story:** As a guardian, when I change the Daily Distraction Budget on Settings and see “Budget saved,” the new limit is used for blocking and shown on refresh.

**Problem (confirmed):** Admin UI posts `{ daily_seconds }` via `settingsApi.updateMasterBudget` → gateway → tab server `POST /api/domains/budgets/master`. Tab server only applies `max_total_distraction_seconds`, `warning_threshold_percent`, and `categories_to_track` — so **`daily_seconds` is ignored** while the handler still returns `success: true`.

**Acceptance criteria:**
- [x] Changing budget via slider/presets + Save updates `domain_config.json` `master_budget.max_total_distraction_seconds` and live `MasterDistractionBudget` singleton.
- [x] After save, Settings page shows the new value without manual refresh (query invalidation).
- [x] `GET /api/distraction/budget` and admin `GET /settings/budgets` reflect the new cap.
- [x] Regression test: gateway or tab_server test that `daily_seconds` / `max_total_distraction_seconds` mapping is consistent end-to-end.

**Technical notes:**
- Fix in `settings_service.update_master_budget` (map `daily_seconds` → `max_total_distraction_seconds`) and/or tab server handler accept both keys.
- Clear misleading success when no field changed (optional hardening).

**Dependencies:** None.

---

### US-A2 · “Remove Allow” works for category-allowed domains (e.g. Education)

| Field | Value |
|-------|--------|
| **FR** | [FR-032] |
| **Priority** | P1 |
| **Estimate** | 1–2 days |

**User story:** As a guardian, when a domain shows as Allowed, I can revoke that allowance in a way that actually changes enforcement — including sites allowed because of **category** (e.g. EDUCATION), not only the explicit always-allowed domain list.

**Problem (confirmed):** `deriveStatus()` treats `status === "allowed"` like whitelist. `get_domain_status()` returns `"allowed"` for domains in `always_allowed_categories` (default includes **EDUCATION**, **PRODUCTIVITY**). **Remove Allow** only calls `remove_always_allowed_domain()`; category allowance is unchanged, so UI appears broken.

**Acceptance criteria:**
- [x] Education (or other category-allowed) domain: guardian can move to blocked, budgeted, or tracked via clear action (not a no-op).
- [x] UI distinguishes **“Allowed (category)”** vs **“Allowed (explicit whitelist)”** (label or badge).
- [x] Per-domain **deny override** or category change is persisted in `domain_config` and reflected in extension/tab_server policy.
- [x] Explicit whitelist add/remove still works for domains not category-allowed.
- [ ] Document default `always_allowed_categories` in operator docs.

**Technical notes:**
- Likely need `per_domain_rules` deny/override, or remove domain from category + add to blocked list, or `blocked_domains` entry — align with `DomainConfigManager.get_domain_status()`.
- Admin: `Settings.tsx` `DomainRow` / `onToggleWhitelist` behavior.

**Dependencies:** None (can ship before US-A3).

---

### US-A3 · Protection level (Warn → Block) applies without surprise delay

| Field | Value |
|-------|--------|
| **FR** | [FR-033] |
| **Priority** | P1 |
| **Estimate** | 1–2 days |

**User story:** As a guardian, when I set protection to **Block** (`enforcing`), distracting sites are blocked on the next navigation within a documented short window (target: &lt; 30s), and I see confirmation if the browser extension did not sync.

**Problem (reported):** Mode change reported success but pages were not blocked; unclear propagation path.

**Current behavior (code):** `POST /api/enforcement_mode` updates `DeploymentConfig`, queues `sync_dnr` for **Google Chrome** and **Microsoft Edge** only (~2s poll). **Advisory** warns; **enforcing** blocks when rules/budgets say so — not instant for all sites.

**Acceptance criteria:**
- [ ] Smoke: Warn → Block → open known distracting URL → block or budget behavior matches mode.
- [x] Admin Settings shows current mode after save; mismatch with tab server surfaced as error.
- [x] If extension not connected, UI shows “Extension not synced” (or last sync time), not silent failure.
- [ ] Operator doc: expected delay, need for extension installed, Chrome/Edge vs other browsers.
- [x] Optional: broaden `sync_dnr` to other registered browsers if supported.

**Technical notes:**
- Trace: `settings_service.set_enforcement_mode` → tab server → `queue_command` → extension `background.js`.
- Verify DNR + classification path in **enforcing** vs **advisory**.

**Dependencies:** Extension installed and paired.

---

## Epic B — Activity monitor + accountability capture

### US-B1 · Wire screenshot capture to activity monitor (pathway first)

| Field | Value |
|-------|--------|
| **FR** | [FR-034] |
| **Priority** | P2 |
| **Estimate** | 2–3 days |

**User story:** As a product owner, when the system detects **sustained distracting activity** (browser or foreground app), it can trigger the existing screenshot pipeline so we can later use images for training and accountability — without re-implementing capture.

**Context (activity module review):**
- **`ActivityMonitor` / `ActivityMonitorComponent`:** foreground window + idle events; no screenshot hook today.
- **`ScreenshotService`:** PIL `ImageGrab`, disk under `~/.focus_guard/screenshots`, daily cap — today invoked from **`OverrideManager._capture_screenshot`** on override flows only.
- **`EnhancedActivityLogger`:** SQLite sessions (`usage_sessions`, `blocking_events`); good attach point for metadata rows linking to `screenshot_id`.

**Acceptance criteria (phase 1 — pathway):**
- [ ] Design doc section: event source (tab_server classification event vs coordinator activity event), privacy/retention, opt-in flag.
- [ ] Config flag (e.g. `FOCUS_GUARD_ACTIVITY_SCREENSHOTS=0|1`) default **off**.
- [ ] When enabled and distraction signal fires, `ScreenshotService.capture()` runs with domain/url/window metadata; `AuditLogger.log_screenshot` or activity DB row stores `screenshot_id` + path.
- [ ] Rate limits reuse `max_screenshots_per_day`; failures do not crash monitor loop.
- [ ] No change to override-only behavior when flag off.

**Acceptance criteria (phase 2 — deferred):**
- [ ] Batch export / labeling UI; image classification model hook (see FR-034 parking lot).

**Dependencies:** US-A3 helpful for consistent “distraction” signal; not blocking phase 1.

---

## Epic C — Beyond the browser

### US-C1 · Detect non-browser distraction (PDFs, ebooks, local readers)

| Field | Value |
|-------|--------|
| **FR** | [FR-035] |
| **Priority** | P2 |
| **Estimate** | 3–5 days (spike + MVP rules) |

**User story:** As a guardian, I want Focus Guard to flag time spent in **non-browser** reading (downloaded fiction PDFs, image folders, Google Docs desktop, Kindle/Apple Books) when it would have been blocked if it were a distracting website.

**Context:** Browser extension cannot see offline files. **`ActivityMonitor`** (Windows) already exposes **app name + window title** — sufficient for a **rules-first** MVP (process allowlists, title keywords, known reader apps).

**Acceptance criteria (MVP):**
- [ ] Spike doc: threat/FP tradeoffs (homework PDF vs novel), data stored (app, title hash, duration — not file contents by default).
- [ ] Configurable **non-browser distraction rules**: app executables + title regexes; default off.
- [ ] Activity sessions tagged `is_browser=false` contribute to guardian report / daily summary when matched.
- [ ] Optional: link to US-B1 screenshot on sustained match (if enabled).

**Acceptance criteria (later):**
- [ ] OCR / image classification on captures; Google Docs in-browser already covered by extension.

**Dependencies:** Activity monitor running on device (coordinator or `ActivityMonitorService`); US-B1 optional.

---

## Epic D — Platform expansion

### US-D1 · macOS + Safari support (tray, activity, extension)

| Field | Value |
|-------|--------|
| **FR** | [FR-036] (extends [FR-012]) |
| **Priority** | P3 |
| **Estimate** | Multi-sprint (spike 2–3 days + implementation) |

**User story:** As a guardian on a Mac, I can run Focus Guard with **Safari** (and Chrome) for monitoring/blocking comparable to the Windows MVP.

**Context (activity module review):** `MacOSActivityMonitor` is a **stub** (`get_active_window` returns None). Extension is **MV3 Chrome/Edge**-oriented; Safari uses **Safari Web Extension** (separate target, Xcode, notarization).

**Acceptance criteria (spike):**
- [ ] Checklist: macOS tray/tab_server paths, permissions (Screen Recording, Accessibility), data dir, Safari Web Extension feasibility vs “Chrome only on Mac.”
- [ ] Decision recorded: Safari in v1 Mac vs Chrome-only Mac.

**Acceptance criteria (delivery — post-spike):**
- [ ] `MacOSActivityMonitor` returns real foreground window metadata.
- [ ] Install doc for Mac; smoke test for local admin + one browser.
- [ ] If Safari in scope: extension package + tab_server messaging parity for core block/classify loop.

**Dependencies:** [FR-012]; significant packaging work.

---

## Suggested execution order

| Order | Story | Rationale |
|-------|--------|-----------|
| 1 | US-A1 | Small fix; unblocks real budget testing |
| 2 | US-A2 | High confusion in Settings domain table |
| 3 | US-A3 | Trust in Block mode |
| 4 | US-B1 | Enables future ML; builds on stable enforcement |
| 5 | US-C1 | Uses activity monitor for gap browser cannot fill |
| 6 | US-D1 | Platform bet; parallel only if resourced |

---

## Test / smoke hooks

| Story | Suggested verification |
|-------|-------------------------|
| US-A1 | Admin UI save 15m → reload → `max_total_distraction_seconds === 900` |
| US-A2 | Education domain → Remove Allow → status not allowed → navigation blocked or budgeted |
| US-A3 | `MVP_SMOKE_TEST.md` add enforcement mode step; extension connected |
| US-B1 | Enable flag → trigger test hook → file on disk + audit row |
| US-C1 | Open PDF in Edge/Acrobat 5m → appears in activity summary |
| US-D1 | Mac spike checklist signed off |
