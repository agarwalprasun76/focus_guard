# Blocking & Classification: Plan Review, Priorities, and Modular Design

**Context:** Review of [mvp_session_plan_736eaac4.plan.md](mvp_session_plan_736eaac4.plan.md) Phase 4 (Classification & Blocking Pipeline), with emphasis on **modularity** (complicated workflow) and **auditability** (clear decision trail).

---

## 1. Plan Summary (Blocking & Classification)

The plan correctly identifies:

- **Current flow:** URL → Pre-check (DomainConfig) → Domain-specific or Generic classifier → Rules → optional LLM escalation → **ClassificationBlocker** → Always-allowed → Budget → Override → Block/Allow/Warn.
- **Weaknesses:** No feedback loop, in-memory cache only, no cost/latency tracking, no confidence calibration, no persistent decision history, and a **complex decision tree that is hard to debug**.

The proposed Phase 4 items are:

| Id   | Item                          | Est.    |
|------|-------------------------------|---------|
| 4.1  | Classification feedback loop  | 3–5 d   |
| 4.2  | Persistent classification cache | 1–2 d |
| 4.3  | Classification decision log   | 1 d     |
| 4.4  | LLM cost/latency tracking     | 0.5 d   |
| 4.5  | User-configurable rules       | 1–2 d   |
| 4.6  | Additional domain classifiers | 3–5 d (future) |
| 4.7  | Time-based access schedules   | 3–5 d   |

---

## 2. Prioritized Improvements (Blocking & Classification)

Priorities are ordered for **auditability first**, then **modularity**, then **learning and scale**.

### Tier 1 — Auditability & Debugging (Do First)

| Priority | Item | Rationale |
|----------|------|-----------|
| **1** | **4.3 Classification decision log** | Single source of truth for “why was this URL blocked/allowed?”. Required for support, tuning, and any future calibration. Enables 4.1 (feedback) and 4.4 (cost) to attach to a concrete decision record. |
| **2** | **Modular blocking pipeline (see Section 3)** | Refactor `ClassificationBlocker.check_blocking()` into discrete, ordered steps (checks) that each emit a **step result**. The final decision is the first “terminal” step (allow/block). This makes the workflow auditable by construction: each decision is a list of step outcomes. |

Do 4.3 and the pipeline refactor together: the decision log should record the **step trace**, not just the final outcome.

### Tier 2 — Correctness & Persistence

| Priority | Item | Rationale |
|----------|------|-----------|
| **3** | **4.1 Layer 1: Feedback collection** | Endpoint + blocked-page button + SQLite table. Enables “this was wrong” without changing behavior yet. Pairs with 4.3 (log) so feedback can reference a decision_id. |
| **4** | **4.2 Persistent classification cache** | Survives restarts, supports more entries, stable keys. Reduces duplicate LLM calls and makes behavior more predictable. Invalidate on config change. |
| **5** | **4.7 Time-based schedules (design + integration)** | Schedule check is a **new step** in the pipeline (after always-allowed, before or in parallel with classification). Designing it as a step keeps the pipeline modular and auditable. |

### Tier 3 — Observability & Tuning

| Priority | Item | Rationale |
|----------|------|-----------|
| **6** | **4.4 LLM cost/latency tracking** | Attach to the same decision log (e.g. `classification_log` or linked table). Enables “how much did we spend / how slow” per decision and per day. |
| **7** | **4.1 Layer 2: Ingestion** | Use feedback to update domain_config / always_allowed. Improves accuracy over time. |
| **8** | **4.5 User-configurable rules** | Parents can add allow/block rules. Store as explicit rules and treat them as early pipeline steps so the decision trail shows “allowed by user rule X”. |

### Tier 4 — Later

| Priority | Item | Rationale |
|----------|------|-----------|
| **9** | **4.1 Layer 3: Adaptive confidence** | Use feedback + decision log to tune thresholds per classifier. Depends on 4.1 Layer 2 and 4.3. |
| **10** | **4.6 Additional domain classifiers** | Improves coverage; add as new pipeline branches, not as one big blob. |
| **11** | **4.7 Full schedule UI** | Visual calendar, drag-to-paint, etc. Can follow after backend schedule step and MVP schedule (predefined profiles) are done. |

---

## 3. Modular Blocking Pipeline Design

Goal: **one complicated workflow implemented as a small pipeline of steps**. Each step is testable in isolation and the overall decision is auditable.

### 3.1 Concepts

- **BlockingRequest:** Immutable input for one check: `url`, `domain`, `title`, `tab_id`, optional `context` (e.g. search_context).
- **BlockingStepResult:** Result of one pipeline step:
  - `terminal: bool` — if True, pipeline stops and this step’s outcome is the final decision.
  - `should_block: bool`
  - `reason: Optional[str]`
  - `step_name: str` (e.g. `always_allowed_domain`, `search_context_block`, `schedule_block`, `classification`, `override`).
  - `details: Dict[str, Any]` (step-specific: category, confidence, rule_id, schedule_profile, etc.)
- **BlockingPipeline:** Ordered list of **steps**. Each step is a function `(request, context) -> Optional[BlockingStepResult]`. First step that returns a **terminal** result wins; if no step returns terminal, a default (e.g. allow) is used.
- **Context:** Mutable bag used across steps (e.g. classification result, budget_status, schedule_profile) so later steps don’t re-do work.

This keeps **decision making** (should we block?) separate from **side effects** (logging, cache write, activity log). The pipeline runner can:
1. Run steps in order until a terminal result.
2. Build an **audit trace**: list of `(step_name, result)` for every step that ran (and optionally the winning step).
3. Write one **decision log** row: request + trace + final outcome.
4. Return the final `BlockingDecision` to the server.

### 3.2 Suggested Step Order (and Audit Names)

| Order | Step name (for audit) | Description | Terminal when |
|-------|------------------------|-------------|----------------|
| 1 | `active_override` | Domain has an active (non-expired) override; user was granted temporary access | Always (allow) when override present |
| 2 | `always_allowed_domain` | Domain in ALWAYS_ALLOWED_DOMAINS (subdomain match) | Always (allow) |
| 3 | `search_context_block` | File-sharing / search context block (e.g. entertainment on Drive) | When should_block |
| 4 | `immediate_domain_block` | Adult or pure entertainment domain (no content-aware classifier) | When should_block |
| 5 | `schedule_check` | Time-based schedule (4.7): profile + domain override; block if profile disallows | When profile says block or allow by schedule |
| 6 | `classification` | Run classification service (cache → classifier → LLM escalation). Writes to context only; does not decide block/allow by itself. | Never (next steps use context) |
| 7 | `fallback_domain_rule` | If classification failed or low-confidence UNKNOWN, apply domain rule | When domain rule matches |
| 8 | `policy_from_classification` | Apply policy: blocked_categories, is_distracting, always_allowed_categories, uncertain_policy, budget_exhausted | Always (block or allow) |

**Override belongs in the pipeline** so that **all** decisions live in one place. The server calls the pipeline for every request; the first step checks for an active override. If present → terminal allow, and that outcome is recorded in the same decision log with `step_trace` showing `active_override`. That way:

- One log answers "why was this URL allowed or blocked?" for every request (override, always-allowed, classification, schedule, etc.).
- No need to correlate override log with a separate "blocking" log.
- Same audit shape for every decision; override is just another step name in the trace.

### 3.3 What Gets Auditable

- **Per request:** One row in `classification_log` (or `blocking_decision_log`) with: `url`, `domain`, `timestamp`, `final_decision` (block/allow), `reason`, `step_trace` (JSON array of `{step_name, terminal, should_block, reason, details}`).
- **In UI/API:** “Why was this blocked?” → show step_trace; the last terminal step’s `reason` and `details` are the human-facing explanation.
- **Feedback (4.1):** Feedback can store `decision_id` (or url+timestamp) so ingestion can tie corrections to the exact decision and step.

### 3.4 Implementation Sketch

- **New module:** e.g. `focus_guard/core/browser_v2/tab_server/blocking_pipeline.py`
  - Types: `BlockingRequest`, `BlockingStepResult`, `BlockingContext`.
  - `BlockingPipeline` class: register steps by name and order; `run(request) -> (BlockingDecision, trace)`.
  - Each current “check” in `ClassificationBlocker` becomes a small function returning `BlockingStepResult` (or None to continue). Classification step runs the service and stores result in context; `policy_from_classification` step reads context and returns the only terminal result for the classification path.
- **ClassificationBlocker:** Becomes a thin wrapper: build `BlockingRequest`, call `pipeline.run(request)`, log activity, write decision log row, return `BlockingDecision`. No change to `BlockingDecision` or server API.
- **Decision log (4.3):** Table or append-only store with at least: `id`, `url`, `domain`, `timestamp`, `final_decision`, `reason`, `step_trace` (JSON), optional `classification_snapshot`, `latency_ms`. Optional link to `classification_cache` or feedback by `(url_hash, timestamp)`.

This keeps the workflow **modular** (add schedule = add one step; add user rules = add one step before or after classification) and **auditable** (every decision = step trace + final outcome).

---

## 4. Recommended Order of Work

1. **Design the step types and pipeline runner** (BlockingRequest, BlockingStepResult, BlockingContext, BlockingPipeline.run) and add unit tests for the runner.
2. **Extract current logic into steps** (without changing behavior): move each “return BlockingDecision(...)” in `classification_blocker.py` into a step; pipeline order as in 3.2. Keep ClassificationBlocker as the single entrypoint that runs the pipeline.
3. **Add decision log (4.3)** with `step_trace` and optional classification/budget snapshot; write one row per pipeline run.
4. **Add feedback endpoint + storage (4.1 Layer 1)** and link feedback to decision (e.g. decision_id or url+timestamp).
5. **Persistent cache (4.2)** and optionally **schedule step (4.7)** as a new step (no-op until schedule config exists).
6. **LLM tracking (4.4)** and **user rules (4.5)** as additional steps or data in context.

This order gives you an auditable, modular pipeline first, then adds logging and feedback, then improves performance and features without breaking the single decision trail.

---

## 5. Doc References

- Plan: [mvp_session_plan_736eaac4.plan.md](mvp_session_plan_736eaac4.plan.md) — Phase 4 (§4.1–4.8).
- Current entrypoint: `ClassificationBlocker.check_blocking()` in `focus_guard/core/browser_v2/tab_server/classification_blocker.py`.
- Override handling: include as first pipeline step (`active_override`) so every decision is logged in one place; move override check from server into pipeline when refactoring.

---

## 6. Implementation Status (Completed Work)

*Updated so a new session can resume from the remaining items.*

### Done (Tier 1 + Tier 2 partial)

| Item | Status | Location / Notes |
|------|--------|------------------|
| **Pipeline types and runner** | ✅ | `focus_guard/core/browser_v2/tab_server/blocking_pipeline.py` — `BlockingRequest`, `BlockingStepResult`, `BlockingContext`, `BlockingPipeline` with `add_step`, `run(request, context_initializer=...)` → `(BlockingDecision, List[StepTraceEntry])`. |
| **Pipeline unit tests** | ✅ | `tab_server/tests/test_blocking_pipeline.py` — runner and context_initializer tests. |
| **All 8 steps extracted** | ✅ | `focus_guard/core/browser_v2/tab_server/blocking_steps.py` — `STEP_ORDER`: `active_override`, `always_allowed_domain`, `search_context_block`, `immediate_domain_block`, `schedule_check`, `classification`, `fallback_domain_rule`, `policy_from_classification`. |
| **ClassificationBlocker → pipeline** | ✅ | `classification_blocker.py`: `check_blocking()` builds `BlockingRequest`, runs pipeline with `context_initializer` setting `_blocker`, returns decision. Override check **removed from server**; pipeline step 1 handles it. |
| **4.3 Decision log** | ✅ | `blocking_decision_log.py` — table `blocking_decision_log` (id, url, domain, timestamp_utc, final_decision, reason, step_trace_json, classification_snapshot_json, latency_ms). One row written per `check_blocking()` after pipeline run. `step_trace_to_json_safe()` for serialization. |
| **4.2 Persistent classification cache** | ✅ | `classification_cache_persistent.py` — SQLite cache (cache_key → result_json, stored_at), TTL and max_entries. `ClassificationService.classify_async()` checks memory then persistent cache; writes to both. `ClassificationResult.from_dict()` for replay. `invalidate_all()` for future config-change hook. |
| **LLM classification persistence** | ✅ | `llm_classification_log.py` — every LLM classification (and escalation) written to `llm_classification_log.db` for audit. Called from `step_classification` when `decision_source == "llm"`. |
| **4.7 schedule_check step** | ✅ (structure only) | Step exists in pipeline as no-op; doc/comment describe future 4.7 (profile + time-based block/allow). Implement schedule config and step logic when ready. |

### Key files

- **Pipeline:** `blocking_pipeline.py`, `blocking_steps.py`
- **Blocker entrypoint:** `classification_blocker.py` (`_get_pipeline()`, `check_blocking()`)
- **Logs / cache:** `blocking_decision_log.py`, `llm_classification_log.py`, `classification_cache_persistent.py`
- **Server:** `server.py` — override pre-check removed; single call to blocking checker (pipeline handles override in step 1)

### Next (resume here)

1. **4.1 Layer 1: Feedback collection** — Endpoint + blocked-page button + SQLite table; link to `decision_id` from blocking_decision_log.
2. **4.4 LLM cost/latency tracking** — Attach to decision log or linked table (e.g. per-decision LLM cost/latency).
3. **4.5 User-configurable rules** — Store allow/block rules; add pipeline step(s) (e.g. before or after classification) so trail shows “allowed by user rule X”.
4. **4.7 Time-based schedules** — Implement schedule config and `step_schedule_check` logic (profile + current time → terminal allow/block).
5. **4.1 Layer 2+3** and **4.6** as in Section 2.
