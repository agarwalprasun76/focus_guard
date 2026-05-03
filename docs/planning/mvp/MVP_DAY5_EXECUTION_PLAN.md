# Focus Guard MVP Day 5 Execution Plan

## Day 5 Objective
Advance classification improvements with auditability-first changes that are safe for MVP: feedback capture + LLM observability, without widening scope into adaptive ML loops.

## Scope Guard (Day 5)
- In scope: feedback collection plumbing, LLM cost/latency tracking, targeted tests, no-op-safe wiring.
- Out of scope: full adaptive retraining, large classifier refactors, deep UI redesign.

## Tasks
- [x] Add/confirm feedback API path from blocked-page flow to `blocking_feedback_log` with strict payload validation and `decision_id` linking.
- [x] Add/confirm decision-to-feedback retrieval utility (or lightweight endpoint) so audit investigations can correlate decision + feedback.
- [x] Add LLM cost/latency fields to persisted LLM audit records and/or decision log linkage.
- [x] Ensure feature-flag style gating for any non-essential LLM enhancements (default conservative behavior).
- [x] Add regression tests for feedback write path and LLM tracking persistence.
- [x] Run focused backend tests for tab server classification/feedback flows.
- [x] Update Day 5 notes and handoff with validation output.
- [x] Complete authenticated runtime retrieval check for `GET /api/feedback/blocking` using valid bearer token.

## Primary Files
- `focus_guard/core/browser_v2/tab_server/server.py`
- `focus_guard/core/browser_v2/tab_server/blocking_feedback_log.py`
- `focus_guard/core/browser_v2/tab_server/llm_classification_log.py`
- `focus_guard/core/browser_v2/tab_server/blocking_decision_log.py`
- `focus_guard/core/browser_v2/tab_server/blocking_steps.py`
- `focus_guard/core/browser_v2/tab_server/classification_service.py`
- `focus_guard/core/browser_v2/tab_server/tests/test_blocking_feedback_log.py`
- `focus_guard/core/browser_v2/tab_server/tests/test_llm_classification_log.py`
- `focus_guard/core/browser_v2/tab_server/tests/test_blocking_decision_log.py`

## Test Files (expected)
- `focus_guard/core/browser_v2/tab_server/tests/test_blocking_decision_log.py`
- `focus_guard/core/browser_v2/tab_server/tests/test_classification_cache_persistent.py`
- `focus_guard/core/browser_v2/tab_server/tests/test_server_feedback*.py` (create if missing)
- `focus_guard/core/browser_v2/tab_server/tests/test_llm_classification_log*.py` (create if missing)

## Validation Plan
- `pytest focus_guard/core/browser_v2/tab_server/tests/test_blocking_decision_log.py -q`
- `pytest focus_guard/core/browser_v2/tab_server/tests/test_classification_cache_persistent.py -q`
- `pytest focus_guard/core/browser_v2/tab_server/tests -k "feedback or llm_classification_log" -q`

## Validation Log (so far)
- [x] `pytest focus_guard/core/browser_v2/tab_server/tests/test_blocking_feedback_log.py focus_guard/core/browser_v2/tab_server/tests/test_llm_classification_log.py focus_guard/core/browser_v2/tab_server/tests/test_blocking_decision_log.py -q` (8 passed)
- [x] `pytest focus_guard/core/browser_v2/tab_server/tests -k "feedback or llm_classification_log" -q` (5 passed, 66 deselected)
- [x] Live PowerShell: `Invoke-RestMethod` to `GET /api/feedback/blocking` with `Authorization: Bearer` from `%ProgramData%\FocusGuard\api_token.json` — returns feedback row for `decision_id=12`; `decision_id=2` returns empty list and `count=0` (expected).

## Expected Outcome
- Guardian/admin can capture wrong-block/wrong-allow feedback tied to decision records.
- LLM-heavy decisions become easier to audit by latency/cost and decision linkage.
- Classification pipeline remains stable, with no behavior-breaking changes.

