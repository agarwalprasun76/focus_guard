# Focus Guard MVP — Day 8 Part B (follow-on execution plan)

Continuation after the core Day 8 deliverables in `MVP_DAY8_EXECUTION_PLAN.md`. Part B focuses on **runtime behavior correctness** once setup and extension onboarding are in place.

## Objective

Close gaps where **deployment enforcement mode** (e.g. Advisory) and **actual blocking / logging** diverge across the tab server, extension, and domain-classification paths—so behavior is predictable and auditable for every navigated origin.

## Priority (P0) — Harden enforcement / advisory / blocking decision flow

**Problem observed:** With enforcement set to **Advisory**, [YouTube](https://www.youtube.com/) was blocked while [Archive of Our Own](https://archiveofourown.org/) was not, suggesting **multiple decision points** (category defaults, per-domain rules, budget enforcement, extension vs server policy, or stale mode propagation) are not aligned with a single **effective policy** derived from `deployment_config` + domain config.

**Goal:** One coherent pipeline:

1. **Source of truth:** Resolve `enforcement_mode` (and any derived flags) once per request or on a clear refresh boundary; no silent overrides from unrelated subsystems.
2. **Advisory semantics:** In advisory mode, **no network or navigation block** that is reserved for enforcing mode unless explicitly documented (e.g. parental “hard block” lists); logging and UI nudges only, unless product spec says otherwise.
3. **Traceability:** Structured log (or debug channel) for “would block / did block / advisory only” with **hostname**, **category**, **rule id** (budget, blocked category, always-allowed, etc.), and **effective mode** at decision time.
4. **Regression coverage:** Add automated or scripted checks for at least two origins in the same category bucket and for mode flip (advisory ↔ enforcing) so divergence like YouTube vs AO3 cannot regress unnoticed.

### Task checklist

- [x] Map the full path: `DeploymentConfig.enforcement_mode` → tab server / coordinator → extension messaging → any hosts or MV3 declarative rules. *(DNR sync now gates on `GET /api/enforcement_mode`; tab server logs `blocking_decision …` for traces.)*
- [x] Identify and remove or gate **duplicate block decisions** (e.g. budget enforcement firing when mode is advisory, or extension applying block lists independent of server mode). *(Fixed: MV3 `syncBlockedDomainsToRules` cleared DNR rules when mode ≠ `enforcing`, which caused advisory/tracking hard redirects despite `/api/should_block`.)*
- [ ] Add integration or smoke steps: Advisory = no hard block on representative distraction URLs; Enforcing = consistent block for same set.
- [x] Document expected behavior in `MVP_SMOKE_TEST.md` or enforcement-mode section of install/smoke docs.

### OpenAI / LLM classification (operational)

- **Symptom:** Logs show `401 Unauthorized` from `api.openai.com` and `LLM classification failed … 'NoneType' object is not subscriptable` when classifying (e.g. Google search URLs). The subscriptable error was a **secondary bug** in error logging when the LLM client returned `None` after 401; fixed in `LLMBasedDomainClassifier` and Google/URL LLM parsers so failures fall back cleanly to rule-based classifiers.
- **Root cause of 401:** Invalid, expired, or rotated API key. Keys are read from `OPENAI_API_KEY` or `openai_api_key` / `open_ai_api_key` in `%ProgramData%\FocusGuard\api_token.json` (see `read_openai_api_key_from_api_token_file`). Re-validate the key in the OpenAI dashboard; ensure no stale key in env or JSON.
- **Follow-up:** Optionally add a startup health log line when LLM is enabled but the first completion returns 401, so operators see it without tailing classification traffic.

### Files likely involved (discovery during execution)

- `focus_guard/main.py`, deployment config load path
- `focus_guard/core/browser_v2/tab_server/` (classification, blocking, enforcement handlers)
- `focus_guard/core/browser/extension/` and MV3 blocking scripts
- `focus_guard/core/domain/domain_config_manager.py` and category / budget application

## Priority (P0) — Cross-browser blocking parity (Chrome vs Edge)

**Problem observed:** The same origin (e.g. [YouTube](https://www.youtube.com/)) was **blocked in Google Chrome** but **not blocked in Microsoft Edge**, with the same Focus Guard runtime and deployment config. That implies **browser-specific divergence** in how the extension talks to the tab server, applies declarative/net rules, or receives tab/navigation events—not acceptable for MVP “one product, two supported browsers.”

**Goal:** For a fixed machine + config + enforcement mode, **Chrome and Edge behave the same** on the same test URLs (block / advisory / allow), within documented MV3 limitations.

1. **Single runtime contract:** Both store builds use the same tab-server base URL, messaging, and policy payloads; no Edge-only or Chrome-only code paths unless explicitly documented with a fallback.
2. **Verification:** Repeatable smoke: open the same distraction URL in both browsers (same profile assumptions) and compare server logs + extension-side signals.
3. **Root-cause checklist:** Extension install/pin state, service worker wake, `declarativeNetRequest` / webRequest differences, tab ID / frame handling, duplicate instances pointing at different ports, or one browser still on an old packed extension.

### Task checklist

- [x] Reproduce with a **minimal matrix**: same OS user, same `deployment_config`, same Focus Guard process; disable **duplicate** extensions (e.g. store + unpacked in one browser) so only one MV3 instance enforces per browser.
- [ ] Correlate **tab server logs** (grep `blocking_decision`) and extension debug logs (`declarativeNetRequest`) with **browser + extension instance** so mismatches are visible in one timeline.
- [x] Audit MV3 manifests and background scripts for **Chrome vs Edge** conditionals or missing `host_permissions` / DNR rule scopes on one target. *(Same `background.js`; root cause for divergent blocks was DNR sync ignoring enforcement mode — addressed above.)*
- [x] Add **MVP_SMOKE_TEST.md** (or equivalent) steps: “same URL, both browsers, expect same enforcement outcome.”
- [ ] If a gap is unavoidable (platform limitation), document it in `INSTALL_WINDOWS.md` with a workaround—not silent drift.

### Files likely involved (discovery during execution)

- `focus_guard/core/browser/extension/webextension_mv3/` (manifest, background, blocking, native messaging if any)
- `focus_guard/core/browser_v2/tab_server/` (endpoints consumed by the extension; port discovery)
- Store/build packaging if Chrome vs Edge artifacts diverge

## Automated tests and release gate

**Shipped (baseline):**

- `focus_guard/tests/integration/tab_server/test_enforcement_modes_tab_server.py` — parametrized checks that `TabServerContext.check_blocking` applies **enforcing / advisory / tracking** consistently when the underlying pipeline would block or allow (pins server-layer contract; extend with real `ClassificationBlocker` + temp configs as the pipeline hardens).
- **Run with pytest** (running the `.py` file directly does nothing useful):

  ```powershell
  python scripts/run_release_integration_tests.py
  # or
  python -m pytest focus_guard/tests/integration/tab_server/test_enforcement_modes_tab_server.py -q
  ```

- `scripts/run_release_integration_tests.py` — pytest-only bundle for tab-server / enforcement regression (**does not** include Playwright). Use before backend-heavy releases.
- `scripts/run_all_tests.py` — full MVP gate: backend pytest slices + **release integration gate** + admin UI Vitest + **Playwright E2E** (when not `--quick`). This is the script to green before MVP demos.

**Admin UI E2E (Playwright) — aligned with current UI (Jan 2026 pass):**

- Dashboard assertions use **hero titles** (`Today's Focus` / `Yesterday's Focus` / `Focus Summary`), not a literal `Dashboard` heading (`admin_ui/e2e/helpers.ts`).
- **Packaged runtime** tests (`e2e/packaged-runtime-smoke.spec.ts`) **skip** when `GET /admin/health` is not JSON (normal Vite-only dev: gateway not proxied). Run against a real admin gateway + packaged lane in CI, or wire dev proxy.
- **Mobile Safari** project is **off by default** (`PLAYWRIGHT_MOBILE=1` enables iPhone 13); desktop Chromium is the MVP gate. Re-enable mobile after fixing modal vs bottom-nav overlap on the overrides flow.

**Day 8 Part B follow-ups (make the gate harder):**

- [ ] Add HTTP-level tests against a live tab-server handler for `/api/enforcement_mode` and a blocking check endpoint (same three modes).
- [ ] Add matrix tests for two canonical hostnames (same category) so “one blocks, one doesn’t” regressions fail in CI.
- [ ] Optional: headless or Playwright step for **Chrome vs Edge** extension parity (behind a flag if flaky).
- [ ] Fix **mobile Safari** critical-smoke (`Exceptions` modal vs bottom nav) and turn `PLAYWRIGHT_MOBILE` on in CI.

### Clarifying failing suites

- Failures in **`Frontend: E2E (Playwright)`** come from `admin_ui` (`npm run test:e2e`), **not** from `scripts/run_release_integration_tests.py` (pytest only). If release pytest is green but full runner fails, inspect Playwright output first.

## Work unit (separate ~1 day) — Classification: metadata fidelity + LLM path (Google / YouTube)

**Not a new code module:** this is a **planning slice** you can schedule as its own exercise (e.g. “Day N — classification pipeline QA”). It overlaps Part B **observability** goals but deserves focused time because the failure modes are orthogonal to enforcement/DNR.

**Problem (observed):**

- Extensive logic exists for **page/source metadata** and LLM-assisted classification; in practice outcomes feel binary — e.g. **YouTube always blocked vs never blocked**, or **Google searches** not reaching the LLM path as expected (title/query/referrer/context empty, wrong classifier order, API key env vs ProgramData — see OpenAI subsection above).

**Goals for the day:**

1. **Trace:** Document the path extension → `/api/should_block` → `ClassificationService.classify*` → composite classifiers (**google_composite**, **youtube_composite**) and what **context** keys are passed (`url`, `title`, `query`, `referrer`, `tab_id`).
2. **Instrumentation:** Confirm logs or temporary debug counters show whether **Google LLM** ran vs fell back to **google_rules**, and whether **metadata** arrives (grep `classified` / `google_llm` / `google_rules`).
3. **Regression tests (pytest work unit, not a new package):** Add **focused unit/integration tests** with **mocked `OpenAIClient`** (existing pattern in `focus_guard/tests/`) asserting:
   - Given rich `context` (title + URL with `q=`), classifier selection and **parsed category** behave as documented.
   - Given **minimal** context (URL only), behavior matches expectations (fallback rules or UNKNOWN).
   - YouTube classifier: same matrix with mocked LLM + rule path so blocking is not “all or nothing” from silent mis-routing.

**Artifacts:** Short section in `MVP_SMOKE_TEST.md` or this file — “classification probe URLs” — for manual QA after the day.

**Relation to existing plan:** Does **not** replace Part B enforcement items; ship Part B parity first if still in flight.

## Lower priority (after P0)

- [ ] Extend post-setup validation to assert **effective enforcement mode** against a probe URL or mock classification response (optional).

## Exit criteria (Part B)

Part B is meaningfully advanced when:

1. Advisory vs enforcing behavior is **defined in one place**, **observable in logs**, and **covered by at least one repeatable test or smoke procedure** so inconsistent blocking (e.g. one entertainment-classified site blocked, another not under the same mode) is treated as a release blocker.
2. **Chrome and Edge** show **the same blocking/advisory outcome** for the same test URLs under the same runtime config, or any intentional difference is **documented** with mitigation steps—not silent browser drift.




Also I am getting these emails so wanted to verify that changes you are making are not getting undone due to built in safety.

The FocusGuard domain configuration file was modified outside of the application.

File: C:\Users\PRASUN~2\AppData\Local\Temp\tmpv7geovak\domain_config.json
Expected hash: 21bc002142070d03...
Actual hash:   65a423c8f2bd970e...
Tamper count:  1
Machine: NucBox_K8Plus
User:
Time: 2026-05-10 19:36:14

The previous known-good configuration has been restored.