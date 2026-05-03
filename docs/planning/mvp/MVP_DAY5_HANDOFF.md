# MVP Day 5 Handoff

## Date
Sunday, May 3, 2026

## Progress
Day 5 classification-improvements slice is complete for feedback + LLM observability plumbing, including live authenticated retrieval verification.

## Completed
- Hardened `POST /api/feedback/blocking` validation in `server.py`:
  - strict `feedback_type` and `source` allowlists
  - strict `decision_id` validation (`int`, `> 0`)
  - verifies `decision_id` exists in `blocking_decision_log`
- Added authenticated retrieval endpoint in `server.py`:
  - `GET /api/feedback/blocking?decision_id=<id>&limit=<n>`
  - auth required; returns recent feedback rows for audit workflows
- Added feedback query utility to `blocking_feedback_log.py`:
  - `list_recent(decision_id=None, limit=50)`
- Added decision existence helper to `blocking_decision_log.py`:
  - `exists(decision_id)`
- Extended LLM observability persistence in `llm_classification_log.py`:
  - `llm_cost_usd`, `prompt_tokens`, `completion_tokens`, `total_tokens`
  - backward-compatible DB migration (`ALTER TABLE ... ADD COLUMN` best-effort)
  - metadata extraction in `log_llm_classification(...)`
- Added feature-flag gate for non-essential LLM observability writes:
  - `FOCUS_GUARD_ENABLE_LLM_OBSERVABILITY` (default enabled)
  - implemented in `blocking_steps.py`

## Tests Added/Updated
- Added: `focus_guard/core/browser_v2/tab_server/tests/test_blocking_feedback_log.py`
- Updated: `focus_guard/core/browser_v2/tab_server/tests/test_llm_classification_log.py`
- Updated: `focus_guard/core/browser_v2/tab_server/tests/test_blocking_decision_log.py`

## Validation
- `pytest focus_guard/core/browser_v2/tab_server/tests/test_blocking_feedback_log.py focus_guard/core/browser_v2/tab_server/tests/test_llm_classification_log.py focus_guard/core/browser_v2/tab_server/tests/test_blocking_decision_log.py -q`
  - Result: `8 passed`
- `pytest focus_guard/core/browser_v2/tab_server/tests -k "feedback or llm_classification_log" -q`
  - Result: `5 passed, 66 deselected`
- Live runtime check (app running locally):
  - `POST /api/feedback/blocking` succeeded with `{"status":"ok","feedback_id":...}`
  - `GET /api/feedback/blocking?...` returns `401` without bearer token (expected for auth-gated audit endpoint)
- Authenticated retrieval (PowerShell, token from `%ProgramData%\FocusGuard\api_token.json`):
  - `GET .../api/feedback/blocking?limit=10` returns feedback row `id=1`, `decision_id=12`, YouTube URL, etc.
  - `GET .../api/feedback/blocking?decision_id=12` returns the same row.
  - `GET .../api/feedback/blocking?decision_id=2` returns empty `feedback`, `count=0` (no feedback for that decision).

## Remaining (optional follow-ups)
- Add lightweight HTTP-level tests for `TabServerRequestHandler` feedback routes if you want CI coverage without a running server.

## Next step (MVP sprint)
Day 6 automated work is documented in **`MVP_DAY6_HANDOFF.md`**. Remaining: complete the **manual** checklist in `MVP_SMOKE_TEST.md`, then proceed to **Day 7 — MVP freeze** per `MVP_SPRINT_MASTER_PLAN.md` § Execution tracker.

