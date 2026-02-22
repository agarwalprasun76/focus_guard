# FocusGuard Admin Web Interface — UX Master Plan

> **Version:** 1.0 | **Date:** 2026-02-09  
> **Scope:** Admin/parent web UI for controlling and observing the FocusGuard local enforcement agent  
> **Platforms:** Desktop browsers (Chrome/Edge/Firefox), Mobile browsers (Safari/Chrome)

---

# Section A — System Primitives & Current Capability Map

## A.1 Core Entities

| Entity | Description | Storage | ID Format |
|---|---|---|---|
| **Device** | Windows/Mac machine running agent | `deployment_config.json` on agent | `machine_name` (hostname) |
| **User** | Monitored user on device | `config/users/{id}.json` | `user_id` string |
| **Admin** | Parent/partner accessing web UI | **NOT YET MODELED** | N/A |
| **Context** | Focus mode / schedule | **NOT YET MODELED** — only enforcement mode exists | N/A |
| **BlockingRule** | Domain-level block | `BlockingManager` + `domain_config.json` | `domain` string |
| **DomainRuleConfig** | Per-domain budget/limits | `DomainUsageTracker` + `domain_config.json` | `domain` string |
| **ClassificationBudget** | Budget by category+usefulness | `domain_config.json` | `"CAT:USE"` key |
| **MasterBudget** | Global daily distraction budget | `domain_config.json` | Singleton |
| **DomainCategory** | Category for a domain | `domain_config.json` domain_categories | `category` → `[domains]` |
| **Override** | Temporary allow for blocked domain | `OverrideManager` in-memory + `override_log.json` | `override_id` (UUID) |
| **AuditEvent** | Accountability log entry | `~/.focus_guard/audit/audit_YYYY-MM-DD.json` | `id` (UUID) |
| **DomainUsageSession** | Active browsing session | `DomainUsageTracker` in-memory | `session_id` (UUID) |
| **DomainDailyStats** | Daily usage per domain | In-memory + `domain_usage_history.json` | `domain+date` |
| **TabInfo** | Browser tab snapshot | `TabStorage` in-memory | Browser tab ID |
| **BrowserStatus** | Connected browser health | `TabStorage` in-memory | `BrowserFamily` enum |
| **PolicyVersion** | **NOT YET MODELED** | N/A | N/A |
| **SearchLog** | Search queries with classification | `SearchLogger` on disk | Timestamp |
| **ActivityLog** | Browsing activity events | `ActivityLogger` on disk | Timestamp |
| **DeploymentConfig** | Top-level agent config | `C:\ProgramData\FocusGuard\deployment_config.json` | Singleton |

## A.2 Current Backend Endpoints (Tab Server — `server.py`)

Tab server on `127.0.0.1:8765`. All HTTP REST, local only.

### GET Endpoints (No Auth)

| Endpoint | Returns |
|---|---|
| `/api/health` | `{status, uptime, connected_browsers}` |
| `/api/tabs` | `TabsSnapshot` |
| `/api/status` | Extension connection status |
| `/api/should_block?url=&domain=&title=&tabId=` | `BlockingDecision` |
| `/api/should_block/rules` | All blocking rules |
| `/api/override?domain=` | Active override check |
| `/api/override/active` | All active overrides |
| `/api/override/log?limit=&domain=` | Override history |
| `/api/override/stats` | Daily override stats |
| `/api/audit?date=&event_type=&domain=&limit=` | Audit events |
| `/api/audit/summary?date=` | Daily audit summary |
| `/api/domain/rules?domain=` | Domain rule configs |
| `/api/domain/usage?domain=` | Domain usage stats |
| `/api/domain/summary` | Summary for email |
| `/api/search/logs`, `/api/search/stats`, `/api/search/patterns` | Search data |
| `/api/activity/logs`, `/api/activity/stats` | Activity data |
| `/api/distraction/budget` | Master budget status |
| `/api/distraction/sites` | Distraction sites today |
| `/api/enforcement_mode` | Current mode |
| `/api/popup_context?domain=` | Blocking page context |
| `/api/domains/overview?category=&status=` | All domains + metadata |
| `/api/domains/budgets` | All budget configs |
| `/api/auth/status` | Token validity |

### POST Endpoints (Auth required on sensitive mutations)

| Endpoint | Auth? | Purpose |
|---|---|---|
| `/api/should_block/rules` | **Yes** | Add blocking rule `{domain, reason}` |
| `/api/override` | No | Request override `{domain, duration, request_reason}` |
| `/api/override/smart` | No | Override with classification |
| `/api/override/revoke` | **Yes** | Revoke override `{domain}` |
| `/api/domain/rules` | **Yes** | Set domain rule |
| `/api/domain/rules/delete` | **Yes** | Delete domain rule |
| `/api/enforcement_mode` | **Yes** | Change mode `{mode, password}` |
| `/api/domains/category` | **Yes** | Move domains `{domains, category}` |
| `/api/domains/whitelist` | **Yes** | Add/remove always-allowed |
| `/api/domains/budgets/domain` | **Yes** | Set per-domain budget |
| `/api/domains/budgets/classification` | **Yes** | Set classification budget |
| `/api/domains/budgets/master` | **Yes** | Set master budget |
| `/api/classification/reload` | **Yes** | Reload classification |
| `/api/blocking/enable_classification` | **Yes** | Enable classification blocking |

### DELETE (Auth Required)

| Endpoint | Purpose |
|---|---|
| `DELETE /api/should_block/rules?domain=` | Remove blocking rule |

### Coordinator API (`core/api/server.py`)

Secondary aiohttp server on port 58392: `GET /` (info), `GET /status`, `POST /api/{endpoint}` (generic).

## A.3 Agent Capabilities Summary

| Capability | Status |
|---|---|
| Domain blocking (rules + classification + budgets) | ✅ |
| Overrides (time-limited, daily limits, wall-clock cap) | ✅ |
| Classification-aware budgets | ✅ |
| Audit logging (daily JSON) | ✅ |
| Activity/search logging | ✅ |
| Domain usage tracking (sessions, 90-day history) | ✅ |
| Email alerts (tamper, mode change, parent notify) | ✅ |
| Screenshot capture | ✅ |
| Config integrity (SHA-256 + tamper revert) | ✅ |
| API auth (bearer token) | ✅ |
| Enforcement modes (tracking/advisory/enforcing) | ✅ |
| Password protection for mode changes | ✅ |
| Security monitors (hosts, heartbeat, incognito, VPN, clock, accounts) | ✅ |
| Browser extension (Chrome/Edge) | ✅ |
| **Remote admin web UI** | ❌ Missing |
| **Multi-device management** | ❌ Missing |
| **Admin authentication (user/password/JWT)** | ❌ Missing |
| **Named contexts/schedules** | ❌ Missing |
| **Request/approval flow** | ❌ Missing |
| **Policy versioning/rollback** | ❌ Missing |
| **WebSocket/SSE live updates** | ❌ Missing |

## A.4 Capability Gap Table — Top 10

| # | Desired Capability | Gap | Severity |
|---|---|---|---|
| **G1** | Admin authenticates remotely | No admin user model, no JWT, no sessions | Critical |
| **G2** | Remote access from mobile/desktop | Tab server binds `127.0.0.1` only | Critical |
| **G3** | Multi-device management | Each agent standalone, no device registry | High |
| **G4** | Named contexts with schedules | Only enforcement mode toggle | High |
| **G5** | Request/approval flow | Overrides are self-service only | High |
| **G6** | Promote exceptions to rules | No promotion workflow/API | Medium |
| **G7** | Policy versioning/rollback | No version history | Medium |
| **G8** | Real-time updates (WebSocket/SSE) | HTTP polling only | Medium |
| **G9** | Admin UI always accessible under blocking | No auto-whitelist for admin domain | Medium |
| **G10** | Cross-day aggregated reporting | Daily files, no aggregation API | Medium |

---

# Section B — UX Workflows (Prioritized)

## B.1 — Blocked But Shouldn't Be (Allow Temporarily / Permanently / By Context)

- **Trigger:** Admin sees in dashboard or receives notification that a site is blocked that should be allowed.
- **Admin Goal:** Unblock the site — temporarily (exception), permanently (whitelist), or with a budget.
- **User-Visible Success:** Site loads within seconds of admin action.
- **Backend/Agent State Changes:**
  - Temporary: `POST /api/override` → `ActiveOverride` in `OverrideManager`
  - Permanent: `POST /api/domains/whitelist {domain, action: "add"}` → `domain_config.json`
  - Budgeted: `POST /api/domains/budgets/domain` → per-domain rule in `domain_config.json`
  - By context: **REQUIRES G4** — not yet supported
- **Required Telemetry:** `AuditEvent` with `event_type: "admin_allow"`, admin_id, reason, scope, duration
- **Edge Cases:**
  - Device offline → queue action, apply on reconnect (REQUIRES G3)
  - Conflicting rules → always-allowed overrides category blocks; explicit block overrides budget
  - Override expiry → agent auto-reverts after duration
- **Security:** Admin must be authenticated (G1). All actions audit-logged. Password required if `config_password_hash` set.

### Gaps
- G1 (admin auth), G4 (contexts), G3 (offline queuing)

---

## B.2 — Not Blocked But Should Be (Block Now / Permanently / Categorize)

- **Trigger:** Admin sees a distracting site in activity logs that isn't blocked.
- **Admin Goal:** Block immediately and/or categorize for future blocking.
- **User-Visible Success:** Site blocked on next navigation attempt.
- **Backend/Agent State Changes:**
  - Block now: `POST /api/should_block/rules {domain, reason}`
  - Categorize: `POST /api/domains/category {domains, category}`
  - Zero budget: `POST /api/domains/budgets/domain {domain, max_cumulative_time_seconds: 0}`
- **Required Telemetry:** `AuditEvent` with `event_type: "admin_block"`, domain, category
- **Edge Cases:**
  - Domain has active override → revoke first (`POST /api/override/revoke`)
  - Subdomain matching → `facebook.com` covers `www.facebook.com`, `m.facebook.com`
  - Classification disagrees → admin override takes precedence
- **Security:** Auth required. Audit logged.

### Gaps
- G1 (admin auth for remote access)

---

## B.3 — Emergency Access Override (Time-Limited; Audit)

- **Trigger:** User needs immediate access to a blocked site for a legitimate emergency.
- **Admin Goal:** Grant time-limited access with full audit trail and explicit confirmation.
- **User-Visible Success:** Site unblocks within seconds; countdown timer visible.
- **Backend/Agent State Changes:**
  - `POST /api/override {domain, duration, request_reason: "EMERGENCY: ..."}` — existing system
  - Auto-expires after duration; wall-clock hard cap (2x duration) in `OverrideManager`
  - `AuditEvent` created; screenshot if `require_screenshot`; parent email sent
- **Required Telemetry:** Emergency flag in audit, parent notification, screenshot
- **Edge Cases:**
  - Budget exhausted → emergency should bypass limits (REQUIRES new `emergency` flag)
  - Admin unavailable → self-service with mandatory screenshot + email (current behavior)
  - Duration abuse → wall-clock hard cap already implemented
- **Security:** Emergency overrides prominently visible in reporting. Double-confirmation in UI.

### Gaps
- Emergency flag not distinct from normal override in data model
- No admin-initiated remote override (G1, G3)

---

## B.4 — Review "What's Happening" (Weekly Summary; Top Friction Points)

- **Trigger:** Admin opens dashboard or receives weekly email.
- **Admin Goal:** Understand patterns — what's blocked, overridden, where friction is highest.
- **User-Visible Success:** Dashboard shows actionable insights, not raw data.
- **Backend/Agent State Changes:** Read-only.
- **Required Telemetry:**
  - `GET /api/audit/summary` — daily summary by category/domain
  - `GET /api/distraction/budget` — budget utilization
  - `GET /api/distraction/sites` — top distraction sites
  - `GET /api/override/stats` — override frequency
  - `GET /api/search/patterns` — distracting search patterns
  - `GET /api/activity/stats` — activity statistics
- **Edge Cases:**
  - No data (new install) → onboarding guidance
  - Device offline → last-known data with staleness indicator
  - Multiple devices → aggregate (REQUIRES G3)
- **Security:** Read-only but requires admin auth.

### Gaps
- G10 (cross-day aggregation), G3 (multi-device), G8 (real-time)

---

## B.5 — Promote Exceptions to Rules (Guided)

- **Trigger:** Domain overridden repeatedly (e.g., 5+ times this week).
- **Admin Goal:** Convert pattern into permanent rule with minimal friction.
- **User-Visible Success:** Domain permanently allowed/budgeted; override prompts stop.
- **Backend/Agent State Changes:**
  - Read: `GET /api/override/log?domain=X`
  - Always allow: `POST /api/domains/whitelist {domain, action: "add"}`
  - Budget: `POST /api/domains/budgets/domain {domain, max_cumulative_time_seconds: N}`
  - Recategorize: `POST /api/domains/category {domains, category}`
- **Required Telemetry:** `AuditEvent` with `event_type: "rule_promoted"`, source overrides, new rule type
- **Edge Cases:**
  - Overridden for different reasons (educational vs entertainment)
  - Classification changed over time
  - Promotion must not bypass safety (adult content)
- **Security:** Auth required. Audit logged.

### Gaps
- G6 (no promotion workflow API — composed from existing endpoints)
- No "frequently overridden" aggregation endpoint

---

## B.6 — Device Management (Online/Offline; Trust; Revoke)

- **Trigger:** Admin checks device status or manages trust.
- **Admin Goal:** See which devices are online, enforcement status; change mode remotely.
- **User-Visible Success:** Device list with status indicators; mode change takes effect.
- **Backend/Agent State Changes:**
  - `GET /api/health` — device health
  - `GET /api/status` — browser connection
  - `POST /api/enforcement_mode {mode, password}` — change mode
- **Required Telemetry:** Device heartbeat, last-seen, mode changes
- **Edge Cases:**
  - Device offline → show last-known with timestamp
  - Multiple devices → need registry (G3)
  - Token rotation → `APIAuthManager.regenerate_token()` exists, no remote trigger
- **Security:** Mode changes require password. Token regeneration invalidates sessions.

### Gaps
- G1 (remote auth), G3 (multi-device), G8 (live status)

---

## B.7 — Rule Editing (Contexts; Allowed/Blocked; Schedules)

- **Trigger:** Admin configures blocking rules, categories, budgets, or schedules.
- **Admin Goal:** Edit rules with immediate effect and clear feedback.
- **User-Visible Success:** Rules take effect within seconds; confirmation shown.
- **Backend/Agent State Changes:**
  - Categories: `POST /api/domains/category`
  - Whitelist: `POST /api/domains/whitelist`
  - Per-domain budgets: `POST /api/domains/budgets/domain`
  - Classification budgets: `POST /api/domains/budgets/classification`
  - Master budget: `POST /api/domains/budgets/master`
  - Blocking rules: `POST /api/should_block/rules`
- **Required Telemetry:** Config change audit events, before/after snapshots
- **Edge Cases:**
  - Conflicting rules (domain in both allowed and blocked)
  - Budget 0 = hard block
  - Schedule-based rules (G4 — not supported)
  - Race condition: two admins editing simultaneously
- **Security:** All mutations require auth. Password for enforcement mode.

### Gaps
- G4 (named contexts/schedules), G7 (policy versioning/rollback)

---

## B.8 — Request/Approval Flow

- **Trigger:** User requests access to blocked site; admin receives notification.
- **Admin Goal:** Review request with context, approve/deny quickly (especially mobile).
- **User-Visible Success:** Site unblocks after approval; user sees "pending" state.
- **Backend/Agent State Changes:** **REQUIRES G5** — no request queue exists.
- **Required Telemetry:** Request event, approval/denial, response time
- **Edge Cases:**
  - Admin unavailable → fallback to self-service budget
  - Request expires → auto-deny after timeout
  - Duplicate requests → deduplicate by domain + time window
- **Security:** Requests must not leak browsing context beyond what's needed.

### Gaps
- G5 (entire flow missing), push notification infrastructure needed

---

# Section C — Wireframes

## C.1 — Dashboard / "What's Happening" (Workflow B.4)

### Variant A: Card-Based Summary

```
+-------------------------------------------------------------+
|  FocusGuard Admin                    [Devices v] [Settings]  |
+-------------------------------------------------------------+
|                                                              |
|  +--------------+  +--------------+  +--------------+        |
|  | Device       |  | Focus Score  |  | Budget Used  |        |
|  | [G] Online   |  |    82/100    |  |  12m / 45m   |        |
|  | Enforcing    |  | ========--   |  | ======----   |        |
|  +--------------+  +--------------+  +--------------+        |
|                                                              |
|  +-------------------------------------------------------+   |
|  | Top Friction Points Today                              |   |
|  | youtube.com    | 3 overrides | 8m used  | [Edit]       |   |
|  | reddit.com     | 2 overrides | 5m used  | [Edit]       |   |
|  | instagram.com  | 1 override  | 3m used  | [Edit]       |   |
|  |                                   [View All Activity]  |   |
|  +-------------------------------------------------------+   |
|                                                              |
|  +-------------------------------------------------------+   |
|  | Recent Overrides                                       |   |
|  | 2:15 PM  youtube.com  "homework video"  5m  [ok]       |   |
|  | 1:30 PM  reddit.com   (no reason)       5m  [ok]       |   |
|  | 12:45 PM discord.com  DENIED (budget)       [denied]   |   |
|  |                                   [View Override Log]  |   |
|  +-------------------------------------------------------+   |
|                                                              |
|  +----------------------+  +--------------------------+      |
|  | [+ Allow a Site]     |  | [+ Block a Site]         |      |
|  +----------------------+  +--------------------------+      |
+-------------------------------------------------------------+
```

- **Click path:** Login → Dashboard (auto)
- **Data needed:** health, distraction/budget, distraction/sites, override/stats, override/log
- **Backend calls:** `GET /api/health`, `GET /api/distraction/budget`, `GET /api/distraction/sites`, `GET /api/override/stats`, `GET /api/override/log?limit=5`
- **Agent actions:** None (read-only)
- **Audit:** None

### Variant B: Timeline-Based

```
+-------------------------------------------------------------+
|  FocusGuard Admin                    [Devices v] [Settings]  |
+-------------------------------------------------------------+
|  Device: Prasun-PC  [G] Online  |  Mode: Enforcing          |
|  Budget: 12m / 45m (27%)        |  Score: 82                |
+-------------------------------------------------------------+
|                                                              |
|  Timeline -- Today                                           |
|  3:00 PM -------------------------------------------- now   |
|  ==== productive  .... idle  #### distraction  ++ override   |
|                                                              |
|  +-- Needs Attention --------------------------------+       |
|  | (!) youtube.com overridden 3x today (pattern)     |       |
|  |     [Promote to Rule] [Adjust Budget] [Ignore]    |       |
|  | (!) reddit.com -- new site, not categorized       |       |
|  |     [Categorize] [Block] [Allow]                  |       |
|  +---------------------------------------------------+       |
|                                                              |
|  Quick Actions: [Allow Site] [Block Site] [Emergency Allow]  |
+-------------------------------------------------------------+
```

- **Click path:** Login → Dashboard (auto)
- **Data needed:** Same as Variant A + activity/logs for timeline
- **Backend calls:** Same + `GET /api/activity/logs?since=<today>&limit=200`
- **Agent actions:** None
- **Audit:** None

### Variant C: Minimal Status (Mobile-First)

```
+---------------------------------+
|  FocusGuard          [= Menu]   |
+---------------------------------+
|  [G] Prasun-PC -- Enforcing     |
|  Focus: 82  Budget: 12m/45m    |
+---------------------------------+
|  (!) 2 items need attention     |
|  +-----------------------------+|
|  | youtube.com -- 3 overrides  ||
|  | [Allow] [Budget] [Block]    ||
|  +-----------------------------+|
|  | reddit.com -- uncategorized ||
|  | [Categorize] [Block]        ||
|  +-----------------------------+|
+---------------------------------+
|  [+ Allow]  [+ Block]  [Log]   |
+---------------------------------+
```

- **Click path:** Login → Dashboard (auto, mobile layout)
- **Data needed:** health, budget, override/stats (minimal)
- **Backend calls:** `GET /api/health`, `GET /api/distraction/budget`, `GET /api/override/stats`
- **Agent actions:** None
- **Audit:** None

**Recommended: Variant B** — Timeline provides temporal context. "Needs Attention" surfaces actionable items. Variant C for mobile.

**Missing backend:** G10 (cross-day aggregation for timeline), G8 (real-time). "Needs attention" heuristic computable client-side from existing endpoints.

---

## C.2 — Allow a Site (Workflow B.1)

### Variant A: Modal Dialog

```
+-----------------------------------------+
|  Allow a Site                     [X]   |
+-----------------------------------------+
|                                         |
|  Domain: [_________________________]    |
|                                         |
|  Scope:                                 |
|  (*) Temporary  Duration: [5m v]        |
|  ( ) Always allowed                     |
|  ( ) Budgeted   Time/day: [15m v]       |
|                                         |
|  Reason (optional):                     |
|  [_________________________________]    |
|                                         |
|  +-----------------------------------+  |
|  | (i) This domain is categorized    |  |
|  |   as: ENTERTAINMENT               |  |
|  |   Current status: blocked         |  |
|  +-----------------------------------+  |
|                                         |
|  [Cancel]              [Allow Site]     |
+-----------------------------------------+
```

- **Click path:** Dashboard → [+ Allow a Site] → Fill domain → Select scope → Confirm
- **Backend calls:**
  - Temporary: `POST /api/override {domain, duration}`
  - Always: `POST /api/domains/whitelist {domain, action: "add"}`
  - Budgeted: `POST /api/domains/budgets/domain {domain, max_cumulative_time_seconds}`
- **Agent action:** Immediate — override on next `should_block` check (< 30s cache)
- **Audit:** `AuditEvent {event_type: "admin_allow", domain, scope, duration, reason}`

### Variant B: Inline Quick Action

```
+---------------------------------------------------------+
|  youtube.com                                            |
|  Category: ENTERTAINMENT  Status: blocked  Overrides: 3 |
|                                                         |
|  [Allow 5m] [Allow 15m] [Allow Always] [Set Budget v]  |
|                                                         |
|  Reason: [_________________________________] (optional) |
+---------------------------------------------------------+
```

- **Click path:** Dashboard friction list → Click domain → Select action (1 click)
- **Backend calls:** Same as Variant A
- **Advantage:** Fewer clicks for common actions

### Variant C: Search + Act

```
+---------------------------------------------------------+
|  Search: [Search domains...                          ]  |
|                                                         |
|  youtube.com  | ENTERTAINMENT | blocked | 3 overrides   |
|    [Allow 5m] [Allow 15m] [Always Allow] [Edit Budget]  |
|                                                         |
|  youtu.be     | ENTERTAINMENT | blocked | 0 overrides   |
|    [Allow 5m] [Allow 15m] [Always Allow] [Edit Budget]  |
+---------------------------------------------------------+
```

- **Click path:** Nav → Search → Type domain → Select action
- **Backend calls:** `GET /api/domains/overview?search=youtube` then mutation

**Recommended:** Variant B for dashboard context (inline), Variant A for standalone. Both available.

**Missing backend:** None — all endpoints exist. Need G1 for remote access.

---

## C.3 — Block a Site (Workflow B.2)

### Variant A: Block Modal

```
+-----------------------------------------+
|  Block a Site                     [X]   |
+-----------------------------------------+
|                                         |
|  Domain: [_________________________]    |
|                                         |
|  Action:                                |
|  (*) Block immediately                  |
|  ( ) Categorize as: [social_media v]    |
|  ( ) Set zero budget (hard block)       |
|                                         |
|  Reason (optional):                     |
|  [_________________________________]    |
|                                         |
|  [Cancel]               [Block Site]    |
+-----------------------------------------+
```

- **Click path:** Dashboard → [+ Block a Site] → Fill domain → Select action → Confirm
- **Backend calls:**
  - Block: `POST /api/should_block/rules {domain, reason}`
  - Categorize: `POST /api/domains/category {domains: [domain], category}`
  - Zero budget: `POST /api/domains/budgets/domain {domain, max_cumulative_time_seconds: 0}`
- **Agent action:** Immediate block on next navigation
- **Audit:** `AuditEvent {event_type: "admin_block", domain, action}`

### Variant B: From Activity Log

```
+---------------------------------------------------------+
|  Activity Log                                           |
|  +-----------------------------------------------------+|
|  | 3:15 PM | youtube.com/watch?v=... | 12m | not blocked||
|  |         | Category: ENTERTAINMENT                    ||
|  |         | [Block] [Categorize] [Set Budget]          ||
|  +-----------------------------------------------------+|
|  | 2:45 PM | reddit.com/r/gaming    | 8m  | not blocked||
|  |         | Category: GAMING                           ||
|  |         | [Block] [Categorize] [Set Budget]          ||
|  +-----------------------------------------------------+|
+---------------------------------------------------------+
```

- **Click path:** Nav → Activity → Spot unblocked distraction → [Block]

**Recommended:** Both — Variant A for proactive blocking, Variant B for reactive (from activity log).

**Missing backend:** None.

---

## C.4 — Emergency Access Override (Workflow B.3)

### Variant A: Dedicated Emergency Panel

```
+---------------------------------------------------------+
|  (!) Emergency Access                             [X]   |
+---------------------------------------------------------+
|                                                         |
|  This grants immediate access to a blocked site.        |
|  All emergency overrides are logged and reported.       |
|                                                         |
|  Domain: [_________________________]                    |
|                                                         |
|  Duration: [15 minutes v]                               |
|  (Maximum: 30 minutes)                                  |
|                                                         |
|  Reason (REQUIRED):                                     |
|  [_________________________________]                    |
|                                                         |
|  [x] I understand this will be logged and reported      |
|                                                         |
|  [Cancel]           [Grant Emergency Access]            |
+---------------------------------------------------------+
```

- **Click path:** Dashboard → [Emergency Allow] → Fill form → Check box → Grant
- **Backend calls:** `POST /api/override {domain, duration, request_reason: "EMERGENCY: <reason>"}`
- **Agent action:** Immediate override, screenshot, parent email
- **Audit:** `AuditEvent {event_type: "override_granted", metadata: {emergency: true}}`

### Variant B: Confirmation Step

```
+---------------------------------------------------------+
|  Confirm Emergency Access                               |
+---------------------------------------------------------+
|                                                         |
|  You are granting emergency access to:                  |
|  Domain: youtube.com                                    |
|  Duration: 15 minutes                                   |
|  Reason: "Need to watch safety video for class"         |
|                                                         |
|  This action will:                                      |
|  - Be logged in the audit trail                         |
|  - Send a notification email to parent                  |
|  - Capture a screenshot for accountability              |
|                                                         |
|  [Go Back]              [Confirm & Grant Access]        |
+---------------------------------------------------------+
```

- **Click path:** After Variant A form → Review → Confirm (2-step)

**Recommended:** Variant A + B combined (form → confirmation). Emergency should feel deliberate.

**Missing backend:** Emergency flag in override data model; budget bypass for emergencies.

---

## C.5 — Promote Exception to Rule (Workflow B.5)

### Variant A: Guided Wizard

```
+---------------------------------------------------------+
|  Promote to Rule: youtube.com                     [X]   |
+---------------------------------------------------------+
|                                                         |
|  This domain was overridden 7 times this week.          |
|  Average duration: 8 minutes per override.              |
|  Classification: ENTERTAINMENT / EDUCATIONAL (60%)      |
|                                                         |
|  Recommended action based on usage:                     |
|  +-----------------------------------------------------+|
|  | (*) Set daily budget: 30 minutes                    ||
|  |     (Based on avg usage of 24 min/day)              ||
|  | ( ) Always allow (no restrictions)                  ||
|  | ( ) Keep current rules (dismiss suggestion)         ||
|  +-----------------------------------------------------+|
|                                                         |
|  [Cancel]                    [Apply Rule]               |
+---------------------------------------------------------+
```

- **Click path:** Dashboard "Needs Attention" → [Promote to Rule] → Review → Apply
- **Backend calls:**
  - Read: `GET /api/override/log?domain=youtube.com`
  - Budget: `POST /api/domains/budgets/domain {domain, max_cumulative_time_seconds: 1800}`
  - Or allow: `POST /api/domains/whitelist {domain, action: "add"}`
- **Audit:** `AuditEvent {event_type: "rule_promoted", domain, new_rule_type}`

### Variant B: Batch Promotion

```
+---------------------------------------------------------+
|  Promotion Suggestions                                  |
+---------------------------------------------------------+
|  These domains have been overridden frequently:         |
|                                                         |
|  [x] youtube.com  | 7x/week | Suggest: 30m budget      |
|  [x] reddit.com   | 5x/week | Suggest: 15m budget      |
|  [ ] discord.com  | 3x/week | Suggest: keep blocked     |
|                                                         |
|  [Apply Selected]  [Customize]  [Dismiss All]           |
+---------------------------------------------------------+
```

- **Click path:** Dashboard → "Needs Attention" badge → Batch review
- **Advantage:** Handle multiple promotions at once

**Recommended:** Variant A for individual, Variant B for weekly review.

**Missing backend:** G6 — aggregation of override frequency (compute client-side from `/api/override/log`).

---

## C.6 — Rule Editor (Workflow B.7)

### Variant A: Table-Based (Desktop)

```
+-------------------------------------------------------------+
|  Rules & Configuration                                      |
+-------------------------------------------------------------+
|  [Domains] [Categories] [Budgets] [Enforcement]             |
+-------------------------------------------------------------+
|  Search: [Filter domains...     ]  Status: [All v]          |
|                                                              |
|  Domain          | Category      | Status   | Budget | Act  |
|  ----------------+---------------+----------+--------+----- |
|  facebook.com    | social_media  | blocked  | 10m/d  | [E]  |
|  youtube.com     | entertainment | budgeted | 30m/d  | [E]  |
|  reddit.com      | entertainment | blocked  | 15m/d  | [E]  |
|  khan-academy.org| education     | allowed  |  --    | [E]  |
|  google.com      | productivity  | allowed  |  --    | [E]  |
|                                                              |
|  [+ Add Domain]                    Page 1 of 3 [< >]        |
+-------------------------------------------------------------+
|  Master Budget: 45 min/day  [Edit]                           |
|  Enforcement Mode: Enforcing  [Change]                       |
+-------------------------------------------------------------+
```

- **Click path:** Nav → Rules → Filter/search → [E] → Edit modal
- **Backend calls:** `GET /api/domains/overview`, then mutations per edit
- **Agent action:** Immediate via `domain_config.json` save
- **Audit:** Config change event

### Variant B: Category-Grouped (Mobile-Friendly)

```
+-------------------------------------------------------------+
|  Rules -- By Category                                       |
+-------------------------------------------------------------+
|                                                              |
|  v Social Media (blocked) ------------------- 5 domains     |
|    facebook.com, instagram.com, twitter.com, tiktok.com,    |
|    snapchat.com  [Edit Category] [Add Domain]               |
|                                                              |
|  v Entertainment (budgeted) ----------------- 8 domains     |
|    youtube.com (30m), netflix.com (15m), reddit.com (15m)   |
|    ... [Edit Category] [Add Domain]                         |
|                                                              |
|  v Education (allowed) ---------------------- 12 domains    |
|    khan-academy.org, wikipedia.org, coursera.org ...        |
|    [Edit Category] [Add Domain]                             |
|                                                              |
|  > Gaming (blocked) ------------------------- 3 domains     |
|  > Productivity (allowed) ------------------- 15 domains    |
+-------------------------------------------------------------+
```

- **Click path:** Nav → Rules → Expand category → Edit/Add

**Recommended:** Variant A for desktop, Variant B for mobile.

**Missing backend:** None — `GET /api/domains/overview` provides all data.

---

## C.7 — Device Management (Workflow B.6)

### Variant A: Device Cards

```
+-------------------------------------------------------------+
|  Devices                                                    |
+-------------------------------------------------------------+
|                                                              |
|  +-------------------------------------------------------+  |
|  | [G] Prasun-PC                                         |  |
|  | Status: Online  |  Last seen: just now                |  |
|  | Mode: Enforcing |  Browser: Chrome (connected)        |  |
|  | Focus: 82/100   |  Budget: 12m / 45m                  |  |
|  |                                                       |  |
|  | [View Dashboard] [Change Mode v] [Settings]           |  |
|  +-------------------------------------------------------+  |
|                                                              |
|  +-------------------------------------------------------+  |
|  | [R] Family-Laptop                                     |  |
|  | Status: Offline |  Last seen: 2 hours ago             |  |
|  | Mode: Enforcing |  Browser: Edge (disconnected)       |  |
|  |                                                       |  |
|  | [View Last Data] [Settings]                           |  |
|  +-------------------------------------------------------+  |
|                                                              |
|  [+ Add Device]                                              |
+-------------------------------------------------------------+
```

- **Click path:** Nav → Devices → Select device → Actions
- **Backend calls:** `GET /api/health`, `GET /api/status` per device
- **Audit:** Mode change events

**Recommended:** Variant A — simple card layout scales to 1-5 devices.

**Missing backend:** G3 (multi-device registry), G1 (remote auth), G8 (live status).

---

## C.8 — Request/Approval Flow (Workflow B.8)

### Variant A: Notification + Quick Approve

```
+---------------------------------+
|  FocusGuard          [= Menu]   |
+---------------------------------+
|  (!) 1 pending request          |
|  +-----------------------------+|
|  | Prasun requests access to:  ||
|  | youtube.com                 ||
|  | Reason: "math tutorial"     ||
|  | Requested: 15 minutes       ||
|  |                             ||
|  | [Approve 15m] [Approve 5m] ||
|  | [Deny] [Deny + Message]    ||
|  +-----------------------------+|
+---------------------------------+
```

- **Click path:** Push notification → Open app → Review → Approve/Deny (1-2 taps on mobile)
- **Backend calls:** `POST /admin/api/v1/requests/{id}/approve {duration}` or `/deny`
- **Agent action:** Create override on approval; notify user on denial
- **Audit:** Request + approval/denial events

### Variant B: Request Queue

```
+---------------------------------------------------------+
|  Pending Requests                                       |
+---------------------------------------------------------+
|  +-----------------------------------------------------+|
|  | youtube.com | "math tutorial" | 15m | 2 min ago     ||
|  | [Approve] [Approve 5m] [Deny]                       ||
|  +-----------------------------------------------------+|
|  | discord.com | "study group" | 30m | 5 min ago       ||
|  | [Approve] [Approve 15m] [Deny]                      ||
|  +-----------------------------------------------------+|
|                                                         |
|  Auto-deny after: [30 minutes v]                        |
+---------------------------------------------------------+
```

**Recommended:** Variant A for mobile (push + quick action), Variant B for desktop queue view.

**Missing backend:** G5 (entire request/approval system), push notifications.

---

# Section D — Information Architecture / Navigation

## D.1 Top-Level Navigation

| Nav Item | Desktop | Mobile | Description |
|---|---|---|---|
| **Dashboard** | Yes | Yes | Landing page — status + attention items + quick actions |
| **Activity** | Yes | Yes (simplified) | Activity logs, search logs, timeline view |
| **Rules** | Yes | Yes (limited editing) | Domain rules, categories, budgets, enforcement mode |
| **Overrides** | Yes | Yes | Active overrides, history, promotion suggestions |
| **Reports** | Yes | No (desktop only) | Weekly/monthly reports, trends, deep drill-down |
| **Devices** | Yes | Yes | Device list, status, mode control |
| **Settings** | Yes | Yes | Admin account, notifications, email config |

**Mobile navigation:** Bottom tab bar with Dashboard, Activity, Overrides, Devices, More (hamburger for Rules, Settings).

**Desktop navigation:** Left sidebar with all items visible. Collapsible to icon-only.

## D.2 Landing Page Behavior

- **Default:** Dashboard view for the primary (or only) device
- **Multi-device:** Device selector dropdown in header; dashboard shows selected device
- **First visit:** Onboarding wizard — connect device, set up admin account, configure email
- **Returning visit:** Dashboard with "Needs Attention" items surfaced first
- **Mobile:** Compact dashboard (Wireframe C.1 Variant C) with bottom tab navigation

## D.3 "Always Accessible" Strategy

The admin UI must remain accessible even when the agent is blocking sites:

1. **Dedicated port:** Admin UI served on `http://localhost:3000` (or LAN IP) — separate from tab server
2. **Agent whitelist:** Admin UI domain/IP added to `always_allowed_domains` in `domain_config.json` during setup
3. **Extension whitelist:** `background.js` safe list includes admin UI origin
4. **System whitelist:** Added to `system_whitelist` in `DomainConfigManager`
5. **Hosts-file exception:** `HostsBlocker` never blocks admin UI address
6. **CORS:** Admin web server sets appropriate CORS headers for the admin origin

**ASSUMPTION:** For MVP, admin UI runs locally on agent machine (port 3000), accessed via LAN IP for remote. Cloud relay is Phase 4+.

## D.4 Role-Based Access

| Role | Capabilities | Auth Method |
|---|---|---|
| **Admin** | Full control — rules, overrides, reporting, device management, settings | Username + password + optional 2FA |
| **Partner** | View reporting, grant/deny override requests, no rule editing | Username + password |
| **Read-Only** | View dashboard and reports only | Username + password |

**ASSUMPTION:** Role-based access is Phase 4. MVP has single admin role with password auth.

---

# Section E — Backend Interface Contract (UX-Driven API Spec)

## E.1 Architecture Decision

**REST API** served by a new lightweight web server (separate from the tab server) that:
1. Serves the admin SPA (static files)
2. Proxies API calls to the existing tab server on `127.0.0.1:8765`
3. Adds admin authentication layer (JWT)
4. Adds WebSocket endpoint for live updates (Phase 3+)

**ASSUMPTION:** Admin web server runs on agent machine, port 3000. Remote access via LAN IP or future cloud relay.

## E.2 Endpoint Catalog

All endpoints prefixed with `/admin/api/v1/`. Gateway authenticates and proxies to tab server.

### Authentication

```
POST /admin/api/v1/auth/login
  Request:  { "username": "admin", "password": "..." }
  Response: { "token": "jwt...", "expires_at": "ISO8601", "role": "admin" }

POST /admin/api/v1/auth/refresh
  Request:  { "token": "jwt..." }
  Response: { "token": "new-jwt...", "expires_at": "ISO8601" }

POST /admin/api/v1/auth/logout
  Response: { "success": true }

GET /admin/api/v1/auth/me
  Response: { "username": "admin", "role": "admin", "created_at": "ISO8601" }
```

### Dashboard (Aggregated)

```
GET /admin/api/v1/dashboard?device_id=
  Response: {
    "device": { "name", "status", "enforcement_mode", "last_seen" },
    "focus_score": 82,
    "budget": { "used_seconds", "total_seconds", "percent" },
    "blocks_today": 15,
    "overrides_today": 5,
    "attention_items": [
      { "type": "frequent_override", "domain": "youtube.com", "count": 3,
        "suggestion": "promote_to_rule" },
      { "type": "uncategorized", "domain": "newsite.com",
        "suggestion": "categorize" }
    ],
    "recent_overrides": [ ... ],
    "top_friction": [ { "domain", "override_count", "time_used_seconds" } ]
  }
```

**Implementation:** Composed from `GET /api/health` + `GET /api/distraction/budget` + `GET /api/distraction/sites` + `GET /api/override/stats` + `GET /api/override/log?limit=10`. The gateway aggregates and computes `attention_items` heuristically.

### Exceptions / Overrides (Admin-Initiated)

```
POST /admin/api/v1/exceptions
  Request: {
    "device_id": "prasun-pc",
    "domain": "youtube.com",
    "type": "temporary" | "permanent" | "budgeted",
    "duration_seconds": 300,
    "budget_seconds_per_day": 1800,
    "reason": "homework video",
    "emergency": false
  }
  Response: {
    "id": "exc_abc123", "status": "active",
    "expires_at": "ISO8601", "audit_event_id": "evt_xyz"
  }

GET /admin/api/v1/exceptions?device_id=&status=active|expired|all&limit=&offset=
  Response: { "exceptions": [...], "total": 42, "page": 1 }

DELETE /admin/api/v1/exceptions/{id}
  Response: { "revoked": true }

POST /admin/api/v1/exceptions/{id}/promote
  Request: { "target_type": "always_allowed" | "budgeted",
             "budget_seconds_per_day": 1800 }
  Response: { "rule_created": true, "rule_type": "budgeted", "domain": "youtube.com" }
```

**Implementation:** Maps to `POST /api/override`, `GET /api/override/active`, `POST /api/override/revoke`, `POST /api/domains/whitelist` or `POST /api/domains/budgets/domain`.

### Rules

```
GET /admin/api/v1/rules/domains?device_id=&category=&status=&search=&limit=&offset=
  Response: { "domains": [...], "total": 150, "page": 1 }

PUT /admin/api/v1/rules/domains/{domain}
  Request: { "category": "entertainment", "status": "budgeted",
             "budget": { "max_cumulative_time_seconds": 1800 } }
  Response: { "updated": true, "domain": "youtube.com" }

DELETE /admin/api/v1/rules/domains/{domain}
  Response: { "deleted": true }

GET /admin/api/v1/rules/categories?device_id=
  Response: { "categories": { "social_media": { "status": "blocked",
              "domain_count": 5 }, ... } }

PUT /admin/api/v1/rules/categories/{category}
  Request: { "status": "blocked" | "allowed" | "budgeted" }
  Response: { "updated": true }

GET /admin/api/v1/rules/budgets?device_id=
  Response: { "master": {...}, "classification": {...}, "per_domain": {...} }

PUT /admin/api/v1/rules/budgets/master
  Request: { "max_total_distraction_seconds": 2700 }
  Response: { "updated": true }

PUT /admin/api/v1/rules/budgets/classification/{key}
  Request: { "max_cumulative_time_seconds": 900, ... }
  Response: { "updated": true }

PUT /admin/api/v1/rules/budgets/domain/{domain}
  Request: { "max_cumulative_time_seconds": 1800, "max_overrides_per_day": 5 }
  Response: { "updated": true }
```

**Implementation:** Maps to `GET /api/domains/overview`, `POST /api/domains/category`, `POST /api/domains/whitelist`, `POST /api/domains/budgets/*`.

### Devices

```
GET /admin/api/v1/devices
  Response: { "devices": [{ "id", "name", "status", "enforcement_mode",
              "last_seen", "browser_status" }] }

GET /admin/api/v1/devices/{id}
  Response: { "id", "name", "status", "enforcement_mode", "health",
              "browser_connections", "config_summary" }

PUT /admin/api/v1/devices/{id}/enforcement
  Request: { "mode": "enforcing", "password": "..." }
  Response: { "updated": true, "mode": "enforcing" }
```

**Implementation:** Maps to `GET /api/health`, `GET /api/status`, `POST /api/enforcement_mode`.

### Reporting

```
GET /admin/api/v1/reports/daily?device_id=&date=
  Response: { "date", "summary": {...}, "hourly_breakdown": [...],
              "top_domains": [...] }

GET /admin/api/v1/reports/weekly?device_id=&week=
  Response: { "week", "daily_summaries": [...], "trends": {...},
              "recommendations": [...] }

GET /admin/api/v1/reports/activity?device_id=&since=&until=&type=&domain=&limit=&offset=
  Response: { "activities": [...], "total": 500 }

GET /admin/api/v1/reports/overrides?device_id=&since=&until=&domain=&limit=&offset=
  Response: { "overrides": [...], "total": 42 }

GET /admin/api/v1/reports/audit?device_id=&since=&until=&event_type=&limit=&offset=
  Response: { "events": [...], "total": 200 }

GET /admin/api/v1/reports/search-patterns?device_id=&since=&limit=
  Response: { "patterns": [...] }
```

**Implementation:** Maps to `GET /api/audit/summary`, `GET /api/activity/*`, `GET /api/override/*`, `GET /api/search/*`. Weekly reports require cross-day aggregation (G10 — computed in gateway).

### WebSocket (Live Updates — Phase 3+)

```
WS /admin/api/v1/ws?token=jwt...
  Server -> Client messages:
    { "type": "device_status", "device_id", "status", "enforcement_mode" }
    { "type": "block_event", "device_id", "domain", "timestamp" }
    { "type": "override_request", "device_id", "domain", "reason" }
    { "type": "override_expired", "device_id", "domain" }
    { "type": "budget_warning", "device_id", "percent" }
```

**Implementation:** Gateway polls tab server periodically and pushes diffs to connected WebSocket clients.

## E.3 Idempotency Rules

- `PUT` operations are idempotent (same payload = same result)
- `POST /admin/api/v1/exceptions` accepts `Idempotency-Key` header; duplicates within 5s for same domain are deduplicated
- `DELETE` operations are idempotent (deleting non-existent resource returns success)

## E.4 Pagination / Filtering

- All list endpoints: `limit` (default 50, max 200), `offset` (default 0)
- Response includes `total` for pagination UI
- Date filtering: ISO 8601 (`since`, `until`)
- Text search: `search` query param (domain substring match)
- Sort: `sort=field:asc|desc` (default: most recent first)

## E.5 Error Model

```json
{
  "error": {
    "code": "DEVICE_OFFLINE",
    "message": "Device prasun-pc is not reachable",
    "details": { "last_seen": "2026-02-09T14:00:00Z" },
    "retry_after_seconds": 30
  }
}
```

Standard error codes: `UNAUTHORIZED`, `FORBIDDEN`, `DEVICE_OFFLINE`, `CONFLICT`, `BUDGET_EXHAUSTED`, `VALIDATION_ERROR`, `NOT_FOUND`, `INTERNAL_ERROR`.

## E.6 Versioning Strategy

- API versioned via URL path (`/admin/api/v1/`)
- Policy versioning (G7): Each `domain_config.json` mutation increments a `version` counter
- `GET /admin/api/v1/rules/versions?device_id=&limit=` — version history
- `POST /admin/api/v1/rules/rollback {device_id, version}` — restore previous
- **Phase 2+ feature** — MVP uses simple overwrite

---

# Section F — Telemetry & Reporting Design

## F.1 Event Taxonomy

| Event Type | Source | Description |
|---|---|---|
| `block` | Agent | Domain blocked by rule or classification |
| `allow` | Agent | Domain allowed (whitelisted, budgeted, or unblocked) |
| `override_requested` | Agent/User | Override request initiated |
| `override_granted` | Agent | Override approved (self-service or admin) |
| `override_denied` | Agent | Override denied (budget exhausted, etc.) |
| `override_expired` | Agent | Override time elapsed |
| `override_revoked` | Admin | Admin manually revoked override |
| `admin_allow` | Admin UI | Admin allowed a domain (temp/perm/budget) |
| `admin_block` | Admin UI | Admin blocked a domain |
| `rule_promoted` | Admin UI | Exception promoted to permanent rule |
| `rule_changed` | Admin UI | Rule/budget/category modified |
| `enforcement_mode_changed` | Admin UI/Agent | Enforcement mode changed |
| `device_online` | Agent | Agent started or became reachable |
| `device_offline` | Agent | Agent stopped or became unreachable |
| `budget_warning` | Agent | Budget usage exceeded warning threshold |
| `budget_exhausted` | Agent | Daily budget fully consumed |
| `config_tamper_detected` | Agent | Config file modified outside FocusGuard |
| `screenshot_captured` | Agent | Accountability screenshot taken |
| `parent_notified` | Agent | Email notification sent to parent |
| `search_distracting` | Agent | Distracting search query detected |
| `emergency_override` | Admin UI | Emergency access granted |
| `classification_changed` | Agent | Domain reclassified |
| `enforcement_password_failed` | Agent | Failed password attempt for mode change |

**Existing coverage:** `AuditEventType` in `audit_logger.py` covers: `override_requested`, `override_granted`, `override_denied`, `override_expired`, `override_revoked`, `screenshot_captured`, `parent_notified`, `budget_exhausted`, `classification_changed`. The coordinator `EventTypes` in `events.py` covers component lifecycle, activity, browser, distraction, and alert events.

**Gap:** `admin_allow`, `admin_block`, `rule_promoted`, `rule_changed`, `device_online/offline`, `emergency_override`, `enforcement_password_failed` need to be added to `AuditEventType` or a new admin event logger.

## F.2 Required Event Fields

```json
{
  "event_id": "evt_abc123",
  "event_type": "override_granted",
  "timestamp": "2026-02-09T16:15:00Z",
  "device_id": "prasun-pc",
  "user_id": "default",
  "admin_id": "admin",
  "target_type": "domain",
  "target_id": "youtube.com",
  "target_url": "https://youtube.com/watch?v=abc",
  "rule_id": "youtube.com",
  "exception_id": "exc_abc123",
  "classification": {
    "category": "ENTERTAINMENT",
    "usefulness": "EDUCATIONAL",
    "confidence": 0.85
  },
  "duration_seconds": 300,
  "reason": "homework video",
  "emergency": false,
  "budget_before": { "used_seconds": 600, "total_seconds": 2700 },
  "budget_after": { "used_seconds": 900, "total_seconds": 2700 },
  "metadata": {}
}
```

**Existing coverage:** `AuditEvent` in `audit_logger.py` has: `id`, `timestamp`, `event_type`, `domain`, `url`, `category`, `usefulness`, `confidence`, `classifier_used`, `override_id`, `duration_seconds`, `remaining_budget_seconds`, `screenshot_id`, `parent_notified`, `request_reason`, `denial_reason`, `browser`, `tab_id`, `metadata`.

**Gap:** Missing `device_id`, `user_id`, `admin_id`, `target_type`, `rule_id`, `exception_id`, `emergency`, `budget_before/after`. These can be added to `metadata` dict in MVP, then promoted to first-class fields.

## F.3 Aggregations for Dashboards

| Aggregation | Purpose | Computation |
|---|---|---|
| **Daily block count** | Headline metric | `COUNT(block events) GROUP BY date` |
| **Daily override count** | Override frequency | `COUNT(override_granted) GROUP BY date` |
| **Top overridden domains (weekly)** | Promotion candidates | `COUNT(override_granted) GROUP BY domain ORDER BY count DESC` |
| **Time by category (daily)** | Category breakdown | `SUM(active_seconds) GROUP BY category` |
| **Focus score trend (7-day)** | Progress tracking | Daily focus scores array |
| **Budget utilization (daily)** | Budget health | `used_seconds / total_seconds` per day |
| **Override denial rate** | Friction indicator | `denied / (granted + denied)` per domain |
| **Distracting search heatmap** | Pattern detection | `COUNT(search_distracting) GROUP BY hour_of_day` |
| **Top friction points** | Actionable insights | Domains with highest `override_count + denial_count` |
| **Streak days** | Gamification | Consecutive days with blocking activity |

**Existing coverage:** `AuditLogger.get_daily_summary()` provides `overrides_granted`, `overrides_denied`, `by_category`, `by_domain`, `distracting_content_accessed`. `OverrideManager.get_daily_stats()` provides per-domain override counts. `DomainUsageTracker` provides daily usage stats. `MasterDistractionBudget.check_budget()` provides budget status.

**Gap:** Cross-day aggregation (weekly trends, 7-day focus score) must be computed in the admin gateway by loading multiple daily files. No pre-computed aggregates exist.

## F.4 Data Retention

| Data Type | Operational | Long-Term | Current Implementation |
|---|---|---|---|
| Audit events | 90 days (daily JSON) | Archive yearly | `~/.focus_guard/audit/audit_YYYY-MM-DD.json` |
| Override logs | 30 days | Monthly aggregates | `~/.focus_guard/override_log.json` |
| Activity logs | 30 days | Daily aggregates | `ActivityLogger` on disk |
| Search logs | 30 days | Weekly patterns | `SearchLogger` on disk |
| Domain usage | 90 days | Keep aggregates | `domain_usage_history.json` |
| Screenshots | 7 days (full) | 30 days (thumbnails) | `ScreenshotService` |
| Config versions | 30 versions | Last 10 | **NOT IMPLEMENTED** (G7) |
| Deployment config | Current only | N/A | `deployment_config.json` |

**Existing:** `StorageConfig.log_retention_days` = 30, `database_retention_days` = 90. No automated cleanup implemented — **Gap:** Need retention enforcement cron/task.

---

# Section G — Phased Project Plan (MVP to V2)

## PHASE 0: Discovery & UX Alignment

**Goal:** Validate UX design, finalize wireframes, align on architecture decisions.

**Deliverables:**
- [ ] Finalized wireframes (Figma or equivalent) for all 8 workflows
- [ ] Admin API contract reviewed and approved
- [ ] Architecture decision: local-only vs cloud relay (recommend local for MVP)
- [ ] Component breakdown and state management design
- [ ] Test strategy document

**Engineering Tasks:**

| Area | Task | Scope |
|---|---|---|
| Frontend | Project scaffold (React + Vite + TailwindCSS + shadcn/ui) | Small |
| Frontend | Design system selection, component library setup | Small |
| Backend | Prototype admin auth module (JWT generation/validation) | Small |
| Backend | Evaluate admin gateway approach (Python FastAPI vs Node Express) | Small |
| Agent | No changes | — |

**Dependencies:** None (greenfield)

**Risks:** Scope creep in wireframe iteration; architecture decision (local vs cloud) affects all phases.

**Definition of Done:** Wireframes approved, API contract signed off, project scaffold running with placeholder pages, test strategy documented.

**Scope:** Small

---

## PHASE 1: MVP Admin Control (Status + Exceptions + Device Connectivity)

**Goal:** Admin can see device status, view recent activity, and create/revoke exceptions from a web browser on the same LAN.

**Deliverables:**
- [ ] Admin web server running on agent machine (port 3000)
- [ ] Admin login page with JWT auth
- [ ] Dashboard page: device status, focus score, budget, recent overrides, top friction
- [ ] Exception creation: allow temporarily, allow permanently, block a site
- [ ] Override revocation from admin UI
- [ ] Active overrides list with countdown timers
- [ ] Mobile-responsive layout (dashboard + exceptions)

**Engineering Tasks:**

| Area | Task | Scope |
|---|---|---|
| Backend | Admin web server (FastAPI) — serves SPA + proxies to tab server | Medium |
| Backend | Admin user model + password hash storage in `deployment_config.json` | Small |
| Backend | JWT auth middleware (login, refresh, logout, me) | Medium |
| Backend | Dashboard aggregation endpoint (compose from tab server APIs) | Medium |
| Backend | Exception creation endpoint (maps to override/whitelist/budget) | Small |
| Backend | CORS configuration for admin origin | Small |
| Backend | Auto-whitelist admin UI in `domain_config.json` on startup | Small |
| Frontend | Login page + JWT token management (localStorage + refresh) | Small |
| Frontend | Dashboard layout (Variant B wireframe) | Medium |
| Frontend | Components: StatusCard, BudgetBar, FrictionList, OverrideList | Medium |
| Frontend | ExceptionModal (allow/block dialog — Variant A wireframe) | Medium |
| Frontend | API client with auth header injection + error handling | Small |
| Frontend | Error/loading state patterns (skeleton screens, toast notifications) | Small |
| Frontend | Responsive breakpoints (desktop 1024px+, tablet 768px, mobile 375px) | Small |
| Agent | Add `admin_ui_port` to `DeploymentConfig` | Small |
| Agent | Bind admin server to `0.0.0.0` (LAN-accessible) with auth | Small |
| Agent | Start admin web server in `runner.py` alongside tab server | Small |

**Dependencies:** Phase 0 complete.

**Risks:**
- Tab server auth token must be accessible to admin gateway (same machine, read from `api_token.json`)
- LAN access requires firewall rule on Windows (document in setup)
- JWT secret storage (use `secure_storage.py` or separate file)

**Definition of Done:**
- Admin can log in from another device on same LAN
- Dashboard shows live device status, budget, overrides
- Admin can allow a site (temporary + permanent) and block a site
- Admin can revoke an active override
- All mutations audit-logged
- Mobile layout functional on iPhone Safari

**Scope:** Medium

---

## PHASE 2: Rules & Contexts (Rule Editor + Promotion Flow)

**Goal:** Admin can edit domain rules, categories, budgets, and promote frequently-overridden exceptions to permanent rules.

**Deliverables:**
- [ ] Rule editor page (table-based for desktop, category-grouped for mobile)
- [ ] Domain search and filtering
- [ ] Category management (move domains between categories)
- [ ] Per-domain budget editor
- [ ] Classification budget editor
- [ ] Master budget editor
- [ ] Enforcement mode control (with password)
- [ ] Promotion workflow: suggest frequently-overridden domains, guided wizard
- [ ] Emergency access override (dedicated panel with confirmation)

**Engineering Tasks:**

| Area | Task | Scope |
|---|---|---|
| Frontend | RuleEditor page (Variant A table + Variant B grouped) | Large |
| Frontend | DomainSearch component with debounced filtering | Small |
| Frontend | CategoryManager (drag-drop or select to move domains) | Medium |
| Frontend | BudgetEditor (per-domain, classification, master) | Medium |
| Frontend | EnforcementModeControl (with password dialog) | Small |
| Frontend | PromotionWizard (Variant A guided + Variant B batch) | Medium |
| Frontend | EmergencyOverridePanel (form + confirmation step) | Small |
| Backend | Promotion endpoint (`POST /admin/api/v1/exceptions/{id}/promote`) | Small |
| Backend | "Attention items" heuristic (frequently overridden domains) | Medium |
| Backend | Emergency flag support in override request | Small |
| Agent | Add `emergency` field to `OverrideManager.request_override()` | Small |
| Agent | Emergency overrides bypass budget limits | Small |
| Agent | Add `rule_promoted` to `AuditEventType` | Small |

**Dependencies:** Phase 1 complete.

**Risks:**
- Rule conflicts (domain in both allowed and blocked) — need validation layer
- Emergency budget bypass could be abused — limit to N per day

**Definition of Done:**
- Admin can view, search, filter, and edit all domain rules
- Admin can change categories, budgets, and enforcement mode
- Promotion wizard suggests domains overridden 3+ times in 7 days
- Emergency override works with required reason and confirmation
- All changes audit-logged with before/after snapshots

**Scope:** Large

---

## PHASE 3: Reporting (Actionable Dashboard + Insights)

**Goal:** Admin has actionable reporting with trends, patterns, and recommendations.

**Deliverables:**
- [ ] Reports page (desktop only) with daily/weekly views
- [ ] Activity timeline visualization
- [ ] Override history with filtering and export
- [ ] Search pattern analysis
- [ ] Focus score trend chart (7-day, 30-day)
- [ ] Budget utilization chart
- [ ] "Top friction points" with actionable recommendations
- [ ] WebSocket/SSE for live dashboard updates

**Engineering Tasks:**

| Area | Task | Scope |
|---|---|---|
| Frontend | Reports page with tab navigation (Daily, Weekly, Activity, Overrides) | Large |
| Frontend | Chart components (line chart for trends, bar for categories, heatmap for time) | Medium |
| Frontend | Activity timeline component | Medium |
| Frontend | Override history table with filtering, sorting, pagination | Medium |
| Frontend | Export to CSV/PDF | Small |
| Frontend | WebSocket client for live updates | Medium |
| Backend | Weekly aggregation endpoint (load 7 daily audit files, compute trends) | Medium |
| Backend | Monthly aggregation endpoint | Medium |
| Backend | Recommendations engine (simple heuristics: frequent overrides, budget near limit) | Medium |
| Backend | WebSocket endpoint (poll tab server, push diffs) | Medium |
| Agent | Add `log_event` for `admin_allow`, `admin_block`, `rule_changed` to `AuditEventType` | Small |
| Agent | Retention enforcement task (cleanup old audit/log files) | Small |

**Dependencies:** Phase 2 complete.

**Risks:**
- Cross-day aggregation performance (loading many JSON files) — consider caching
- WebSocket reliability on unstable networks — implement reconnection logic
- Chart library bundle size — use lightweight library (e.g., Recharts or lightweight-charts)

**Definition of Done:**
- Admin can view daily and weekly reports with charts
- Activity timeline shows productive/idle/distraction periods
- Override history is searchable and exportable
- Live dashboard updates via WebSocket (block events, override events)
- Recommendations surface actionable insights

**Scope:** Large

---

## PHASE 4: Hardening (AuthZ, Auditing, Offline, Resilience)

**Goal:** Production-ready security, resilience, and multi-user support.

**Deliverables:**
- [ ] Role-based access control (admin, partner, read-only)
- [ ] Admin account management (create, edit, delete accounts)
- [ ] Comprehensive audit trail for all admin actions
- [ ] Offline device handling (queue actions, show staleness)
- [ ] Rate limiting on admin API
- [ ] HTTPS support (self-signed cert or Let's Encrypt for LAN)
- [ ] Session management (concurrent sessions, force logout)
- [ ] Policy versioning and rollback (G7)
- [ ] Data retention enforcement (automated cleanup)

**Engineering Tasks:**

| Area | Task | Scope |
|---|---|---|
| Backend | Role-based access middleware | Medium |
| Backend | Admin account CRUD (stored in secure_storage) | Medium |
| Backend | Comprehensive admin action audit logging | Medium |
| Backend | Action queue for offline devices | Medium |
| Backend | Rate limiting middleware | Small |
| Backend | HTTPS/TLS configuration | Medium |
| Backend | Session management (token blacklist, concurrent session limit) | Medium |
| Backend | Policy version tracking (snapshot on each mutation) | Medium |
| Backend | Policy rollback endpoint | Small |
| Backend | Retention enforcement cron task | Small |
| Frontend | Account management UI | Medium |
| Frontend | Role-based UI (hide/disable features per role) | Small |
| Frontend | Offline device indicators and queued action display | Small |
| Agent | Action queue consumer (apply queued actions on reconnect) | Medium |

**Dependencies:** Phase 3 complete.

**Risks:**
- HTTPS on LAN is complex (self-signed certs cause browser warnings)
- Policy rollback could cause inconsistent state if agent has applied changes
- Multi-admin concurrent editing needs conflict resolution

**Definition of Done:**
- Three roles functional with appropriate access restrictions
- All admin actions have audit trail entries
- Offline devices show last-known state; actions queue and apply on reconnect
- HTTPS enabled with documented cert setup
- Policy versioning with rollback functional

**Scope:** Large

---

## PHASE 5: Mobile Polish (Mobile-First Views + Notification Hooks)

**Goal:** Optimized mobile experience with push notifications for time-sensitive actions.

**Deliverables:**
- [ ] Mobile-optimized views for all pages
- [ ] Bottom tab navigation with badges
- [ ] Push notifications for override requests (G5), budget warnings, device offline
- [ ] Request/approval flow (G5) — user requests, admin approves from mobile
- [ ] PWA support (installable, offline-capable shell)
- [ ] Touch-optimized interactions (swipe to approve/deny, pull to refresh)

**Engineering Tasks:**

| Area | Task | Scope |
|---|---|---|
| Frontend | Mobile-first responsive redesign for all pages | Large |
| Frontend | Bottom tab navigation with notification badges | Small |
| Frontend | PWA manifest + service worker (offline shell, caching) | Medium |
| Frontend | Touch gestures (swipe actions, pull-to-refresh) | Medium |
| Frontend | Push notification integration (Web Push API) | Medium |
| Frontend | Request/approval UI (Variant A notification + Variant B queue) | Medium |
| Backend | Web Push subscription management | Medium |
| Backend | Push notification triggers (override request, budget warning, device offline) | Medium |
| Backend | Request queue (user submits request, admin approves/denies) | Large |
| Agent | Request submission endpoint (user-facing, no auth) | Medium |
| Agent | Request status polling endpoint | Small |

**Dependencies:** Phase 4 complete.

**Risks:**
- Web Push requires HTTPS and service worker — depends on Phase 4 HTTPS
- Push notification delivery is not guaranteed (browser may throttle)
- Request/approval flow adds significant complexity to agent

**Definition of Done:**
- All pages usable on mobile (375px viewport)
- Push notifications delivered for override requests and budget warnings
- Request/approval flow: user requests from blocking page, admin approves from mobile
- PWA installable on iOS and Android
- Touch interactions feel native

**Scope:** Large

---

# Section H — Frontend Implementation Plan

## H.1 Proposed Frontend Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Framework** | React 18+ (with Vite) | Widely adopted, large ecosystem, good for SPA. Vite for fast dev builds. |
| **Language** | TypeScript | Type safety for API contracts and component props. |
| **Styling** | TailwindCSS 3+ | Utility-first, responsive by default, small bundle with purge. |
| **Component Library** | shadcn/ui | Accessible, composable, built on Radix UI primitives. Copies into project (no runtime dep). |
| **Icons** | Lucide React | Consistent icon set, tree-shakeable. |
| **State Management** | TanStack Query (React Query) | Server state with caching, refetching, optimistic updates. Backend authoritative. |
| **Routing** | React Router v6 | Standard SPA routing with nested layouts. |
| **Forms** | React Hook Form + Zod | Performant forms with schema validation matching API contracts. |
| **Charts** | Recharts | Lightweight, React-native charting for reports (Phase 3). |
| **WebSocket** | Native WebSocket + reconnecting-websocket | Lightweight. Phase 3+. |
| **Testing** | Vitest + Testing Library + Playwright | Unit/integration/E2E. |
| **Build** | Vite | Fast HMR, optimized production builds, static output served by admin gateway. |

**ASSUMPTION:** Repo is Python-only today. This is a greenfield frontend. Built SPA served as static files by admin gateway (FastAPI `StaticFiles`).

## H.2 Component Breakdown

### Layout Components

| Component | Description | Phase |
|---|---|---|
| `AppShell` | Top-level layout: sidebar (desktop) / bottom tabs (mobile) | 1 |
| `Sidebar` | Desktop left nav, collapsible | 1 |
| `BottomTabs` | Mobile bottom tab nav with badges | 1 |
| `Header` | Top bar: device selector, settings, user menu | 1 |
| `PageContainer` | Content area with breadcrumbs and title | 1 |

### Dashboard Components

| Component | Description | Phase |
|---|---|---|
| `StatusCard` | Device status (online/offline, mode, last seen) | 1 |
| `BudgetBar` | Progress bar for budget utilization with color coding | 1 |
| `FocusScoreRing` | Circular progress for focus score (0-100) | 1 |
| `FrictionList` | Top friction points with inline actions | 1 |
| `OverrideList` | Recent overrides with status badges | 1 |
| `AttentionBanner` | "Needs Attention" items with suggested actions | 1 |
| `QuickActions` | Floating action buttons: Allow, Block, Emergency | 1 |
| `ActivityTimeline` | Horizontal timeline bar (productive/idle/distraction) | 3 |

### Exception/Override Components

| Component | Description | Phase |
|---|---|---|
| `ExceptionModal` | Allow/block dialog with scope selection | 1 |
| `EmergencyPanel` | Emergency override form + confirmation step | 2 |
| `OverrideCountdown` | Live countdown timer for active overrides | 1 |
| `OverrideHistoryTable` | Paginated, filterable override history | 1 |

### Rule Editor Components

| Component | Description | Phase |
|---|---|---|
| `DomainTable` | Sortable, filterable table with inline edit | 2 |
| `DomainSearch` | Debounced search with autocomplete | 2 |
| `CategoryAccordion` | Collapsible category groups (mobile) | 2 |
| `BudgetEditor` | Form for per-domain / classification / master budgets | 2 |
| `EnforcementControl` | Mode selector with password dialog | 2 |
| `PromotionWizard` | Guided promotion with data-driven suggestions | 2 |
| `BatchPromotion` | Multi-select promotion for weekly review | 2 |

### Reporting Components

| Component | Description | Phase |
|---|---|---|
| `DailySummaryCard` | Summary stats for a single day | 3 |
| `WeeklyTrendChart` | Line chart: focus score, budget, overrides over 7 days | 3 |
| `CategoryBreakdownChart` | Bar/pie chart: time by content category | 3 |
| `SearchPatternList` | Distracting search patterns with frequency | 3 |
| `ExportButton` | Export data to CSV/PDF | 3 |

### Device & Shared Components

| Component | Description | Phase |
|---|---|---|
| `DeviceCard` | Device status card with actions | 1 |
| `DeviceList` | Grid/list of device cards | 1 |
| `LoadingSkeleton` | Skeleton placeholder during loading | 1 |
| `ErrorBoundary` | Catch and display component errors | 1 |
| `Toast` | Notification toasts (success/error/warning) | 1 |
| `ConfirmDialog` | Generic confirmation for destructive actions | 1 |
| `EmptyState` | Friendly empty state with guidance + CTA | 1 |
| `Pagination` | Page controls for list endpoints | 1 |
| `Badge` | Status badges (online/offline, granted/denied) | 1 |

## H.3 State Management Approach

**Principle:** Backend is authoritative. Frontend caches for responsiveness but defers to server state.

- **Server state (TanStack Query):**
  - Dashboard: `staleTime: 30s`, `refetchInterval: 30s` (polling until WebSocket Phase 3)
  - Rules/domains: `staleTime: 60s`, refetch on mutation success
  - Override list: `staleTime: 10s`, refetch on mutation
  - Reports: `staleTime: 5min`

- **Optimistic updates** for quick-feedback mutations (allow/block/revoke):
  1. Immediately update UI
  2. Send mutation to backend
  3. On success: invalidate related queries
  4. On failure: rollback, show error toast

- **Client state:** Minimal — UI state only (modal open/closed, selected tab, sidebar). React `useState`/`useReducer`. No global store.

- **Auth state:** JWT in `localStorage`. Refresh via API client interceptor. Redirect to login on 401.

## H.4 Accessibility

- **Keyboard:** All elements focusable/operable. Tab order follows layout. Modal traps focus.
- **ARIA:** Buttons, inputs, dynamic content labeled. Status indicators use `aria-live`.
- **Color contrast:** WCAG AA (4.5:1 text, 3:1 large). Status colors paired with icons/text.
- **Responsive:** Fluid 375px–1920px. No horizontal scroll.
- **Reduced motion:** Respect `prefers-reduced-motion`. Disable animations when set.
- **Focus indicators:** Visible focus rings (TailwindCSS `ring` utilities).

## H.5 Error / Loading State Patterns

| State | Pattern |
|---|---|
| **Loading (initial)** | Skeleton placeholders matching final layout |
| **Loading (refetch)** | Subtle spinner in header, data stays visible |
| **Error (network)** | Banner: "Unable to reach device. Retrying..." + retry button |
| **Error (auth)** | Redirect to login with "Session expired" |
| **Error (validation)** | Inline field errors + toast summary |
| **Error (conflict)** | Dialog explaining conflict with resolution options |
| **Empty (no data)** | Illustration + guidance text + CTA |
| **Offline (device)** | Grayed-out card with "Last seen: X" |
| **Success (mutation)** | Green toast: "youtube.com allowed for 5 minutes" |

---

# Section I — Automated Testing Plan (UI + Integration)

## I.1 Unit Tests (Vitest + Testing Library)

### Component Rendering

| Test Suite | What to Test | Priority |
|---|---|---|
| `StatusCard.test.tsx` | Renders online/offline states, enforcement mode badge, last-seen text | High |
| `BudgetBar.test.tsx` | Progress bar width matches percent, color changes at thresholds (green/yellow/red) | High |
| `FocusScoreRing.test.tsx` | Score renders correctly, ring fill matches value | Medium |
| `ExceptionModal.test.tsx` | Form renders all scope options, domain input validation, submit/cancel buttons | High |
| `OverrideCountdown.test.tsx` | Countdown decrements, shows "Expired" at 0, calls onExpire callback | High |
| `FrictionList.test.tsx` | Renders domain list, inline action buttons present, empty state when no data | Medium |
| `DomainTable.test.tsx` | Sorting, filtering, pagination, inline edit triggers | Medium |
| `PromotionWizard.test.tsx` | Shows override count, recommended action, apply/cancel buttons | Medium |
| `EmergencyPanel.test.tsx` | Required reason validation, confirmation checkbox required before submit | High |
| `Toast.test.tsx` | Shows/hides, correct variant (success/error/warning), auto-dismiss | Low |

### Form Validation

| Test Suite | What to Test |
|---|---|
| `exception-form.test.ts` | Domain required, duration > 0 for temporary, budget > 0 for budgeted, reason required for emergency |
| `budget-form.test.ts` | `max_cumulative_time_seconds` >= 0, `max_overrides_per_day` >= 0, classification key format `CAT:USE` |
| `login-form.test.ts` | Username required, password required, error message on invalid credentials |
| `enforcement-form.test.ts` | Mode must be valid enum, password required when `config_password_hash` is set |

### Data Transformations

| Test Suite | What to Test |
|---|---|
| `dashboard-aggregation.test.ts` | `computeAttentionItems()` — identifies domains overridden 3+ times, uncategorized domains |
| `time-formatting.test.ts` | `formatDuration(seconds)` — "5m", "1h 30m", "< 1m" |
| `budget-calculations.test.ts` | Percent computation, threshold detection (warning at 70%, exhausted at 100%) |
| `override-grouping.test.ts` | Group overrides by domain, compute frequency, sort by count |

## I.2 Integration Tests (Vitest + MSW for Mocked Backend)

Use [MSW (Mock Service Worker)](https://mswjs.io/) to intercept API calls with realistic responses.

### Contract Tests

| Test | Description |
|---|---|
| `api-client.test.ts` | API client adds JWT header, handles 401 with redirect, handles 500 with error toast |
| `auth-flow.test.ts` | Login → receive JWT → store in localStorage → subsequent requests include token → refresh on expiry → logout clears token |
| `dashboard-fetch.test.ts` | Dashboard page fetches `/admin/api/v1/dashboard`, renders data correctly, handles loading/error states |
| `exception-create.test.ts` | ExceptionModal submits `POST /admin/api/v1/exceptions`, handles success (toast + close modal), handles error (inline message) |
| `override-revoke.test.ts` | Revoke button sends `DELETE /admin/api/v1/exceptions/{id}`, optimistic removal from list, rollback on failure |

### Exception Creation Flows

| Test | Steps |
|---|---|
| `allow-temporary.test.ts` | Open modal → enter domain → select "Temporary" → set 5m → submit → verify `POST` payload `{type: "temporary", duration_seconds: 300}` → verify toast |
| `allow-permanent.test.ts` | Open modal → enter domain → select "Always allowed" → submit → verify payload `{type: "permanent"}` → verify domain appears in allowed list |
| `block-site.test.ts` | Open modal → enter domain → select "Block immediately" → submit → verify `POST /api/should_block/rules` called → verify toast |
| `emergency-override.test.ts` | Open emergency panel → enter domain → enter reason → check confirmation → submit → verify payload includes `emergency: true` → verify confirmation step shown |

### Rule Editor Flows

| Test | Steps |
|---|---|
| `edit-domain-budget.test.ts` | Load rules page → click edit on domain → change budget → save → verify `PUT` payload → verify table updates |
| `change-category.test.ts` | Load rules page → select domain → change category → save → verify `PUT` payload |
| `change-enforcement.test.ts` | Click enforcement control → select new mode → enter password → confirm → verify `PUT` with password → verify mode updates |
| `promote-exception.test.ts` | Dashboard shows attention item → click "Promote" → wizard shows override stats → select "Budget 30m" → apply → verify `POST .../promote` |

### Offline / Error States

| Test | Steps |
|---|---|
| `device-offline.test.ts` | MSW returns `{error: {code: "DEVICE_OFFLINE"}}` → verify grayed-out UI, "Last seen" shown, retry button present |
| `network-error.test.ts` | MSW returns network error → verify error banner, retry button, data preserved from cache |
| `auth-expired.test.ts` | MSW returns 401 → verify redirect to login, "Session expired" message |
| `conflict-error.test.ts` | MSW returns `{error: {code: "CONFLICT"}}` → verify conflict dialog with resolution options |

## I.3 End-to-End Tests (Playwright)

### Setup

- **Config:** `playwright.config.ts` with projects for desktop Chrome (1280x800) and mobile Safari (375x812)
- **Base URL:** `http://localhost:3000` (admin UI dev server)
- **Auth fixture:** `auth.setup.ts` — logs in as admin, saves storage state for reuse
- **Mock server:** Optional — can run against real admin gateway + tab server for true E2E, or use Playwright route interception for isolated tests

### Desktop Viewport Suite

| Test | Critical Path |
|---|---|
| `login.spec.ts` | Navigate to `/` → redirected to `/login` → enter credentials → submit → redirected to `/dashboard` |
| `dashboard-load.spec.ts` | Login → dashboard loads → status card visible → budget bar visible → friction list visible |
| `allow-site-temporary.spec.ts` | Dashboard → click "Allow a Site" → fill domain "youtube.com" → select "Temporary 5m" → submit → toast "youtube.com allowed for 5 minutes" → override appears in list |
| `block-site.spec.ts` | Dashboard → click "Block a Site" → fill domain "tiktok.com" → select "Block immediately" → submit → toast "tiktok.com blocked" |
| `emergency-allow.spec.ts` | Dashboard → click "Emergency Allow" → fill domain → fill reason → check confirmation → submit → confirmation step → confirm → toast "Emergency access granted" |
| `revoke-override.spec.ts` | Dashboard → override list → click "Revoke" on active override → confirm dialog → toast "Override revoked" → override removed from list |
| `rule-editor.spec.ts` | Nav → Rules → search "youtube" → click edit → change budget to 30m → save → toast "Rule updated" → table shows new budget |
| `promote-exception.spec.ts` | Dashboard → attention item "youtube.com overridden 3x" → click "Promote" → wizard → select "Budget 30m" → apply → toast "Rule created" |
| `change-enforcement.spec.ts` | Nav → Rules → Enforcement → change to "Advisory" → enter password → confirm → toast "Mode changed" |

### Mobile Viewport Suite

| Test | Critical Path |
|---|---|
| `mobile-dashboard.spec.ts` | Login → compact dashboard → status visible → attention items visible → bottom tabs visible |
| `mobile-allow-site.spec.ts` | Dashboard → tap "Allow" in bottom actions → fill domain → select scope → submit → toast |
| `mobile-override-list.spec.ts` | Bottom tab "Overrides" → list loads → tap override → details expand |
| `mobile-navigation.spec.ts` | Bottom tabs navigate correctly → hamburger menu opens → Rules accessible |

### Critical Workflow: Full Override Lifecycle

```
test('full override lifecycle', async ({ page }) => {
  // 1. Admin allows a site temporarily
  await page.goto('/dashboard');
  await page.click('[data-testid="allow-site-button"]');
  await page.fill('[data-testid="domain-input"]', 'youtube.com');
  await page.click('[data-testid="scope-temporary"]');
  await page.selectOption('[data-testid="duration-select"]', '300');
  await page.click('[data-testid="submit-allow"]');
  await expect(page.locator('[data-testid="toast-success"]')).toBeVisible();

  // 2. Override appears in active list with countdown
  await expect(page.locator('[data-testid="override-youtube.com"]')).toBeVisible();
  await expect(page.locator('[data-testid="countdown-youtube.com"]')).toContainText(/\d+:\d+/);

  // 3. Admin revokes the override
  await page.click('[data-testid="revoke-youtube.com"]');
  await page.click('[data-testid="confirm-revoke"]');
  await expect(page.locator('[data-testid="toast-success"]')).toContainText('revoked');
  await expect(page.locator('[data-testid="override-youtube.com"]')).not.toBeVisible();
});
```

## I.4 API Contract Tests

### Schema Validation

Use Zod schemas (shared between frontend and test suite) to validate API responses:

```typescript
// schemas/dashboard.ts
const DashboardResponseSchema = z.object({
  device: z.object({ name: z.string(), status: z.string(), enforcement_mode: z.string() }),
  focus_score: z.number().min(0).max(100),
  budget: z.object({ used_seconds: z.number(), total_seconds: z.number(), percent: z.number() }),
  blocks_today: z.number(),
  overrides_today: z.number(),
  attention_items: z.array(z.object({ type: z.string(), domain: z.string() })),
  recent_overrides: z.array(z.any()),
  top_friction: z.array(z.object({ domain: z.string(), override_count: z.number() })),
});

// tests/api-contract.test.ts
test('GET /admin/api/v1/dashboard returns valid schema', async () => {
  const res = await fetch('/admin/api/v1/dashboard?device_id=test', { headers: authHeaders });
  const data = await res.json();
  expect(() => DashboardResponseSchema.parse(data)).not.toThrow();
});
```

### Idempotency Tests

| Test | Description |
|---|---|
| `idempotent-put.test.ts` | `PUT /rules/budgets/domain/youtube.com` twice with same payload → both return 200, state unchanged |
| `idempotent-delete.test.ts` | `DELETE /exceptions/abc` twice → first returns 200, second returns 200 (not 404) |
| `duplicate-exception.test.ts` | `POST /exceptions` twice with same `Idempotency-Key` within 5s → second returns same `id` as first |

## I.5 Agent-in-the-Loop Tests

**ASSUMPTION:** These tests run with a real FocusGuard agent (tab server) running locally. They verify that admin UI actions actually change agent enforcement state.

### Setup

- Start tab server in test mode: `python -m focus_guard.core.browser_v2.tab_server.runner --test-mode`
- Test mode uses isolated config files (temp directory) and in-memory storage
- Admin gateway connects to test tab server

### Test Cases

| Test | Steps | Verification |
|---|---|---|
| `agent-block-enforced.test.ts` | Admin blocks "test.com" via UI → call tab server `GET /api/should_block?domain=test.com` | Response: `should_block: true` |
| `agent-override-active.test.ts` | Admin allows "test.com" temporarily (5m) → call `GET /api/override?domain=test.com` | Response: `has_override: true, remaining_seconds > 0` |
| `agent-override-revoked.test.ts` | Admin revokes override → call `GET /api/override?domain=test.com` | Response: `has_override: false` |
| `agent-whitelist-applied.test.ts` | Admin always-allows "test.com" → call `GET /api/should_block?domain=test.com` | Response: `should_block: false` |
| `agent-budget-applied.test.ts` | Admin sets budget 0s for "test.com" → call `GET /api/domains/budgets` | Budget shows `max_cumulative_time_seconds: 0` |
| `agent-mode-changed.test.ts` | Admin changes mode to "tracking" → call `GET /api/enforcement_mode` | Response: `enforcement_mode: "tracking"` |
| `agent-audit-logged.test.ts` | Admin allows "test.com" → call `GET /api/audit?domain=test.com&limit=1` | Latest event has `event_type` matching admin action |

## I.6 Test Data Strategy

### Fixtures

```
tests/fixtures/
  dashboard-response.json      # Realistic dashboard data
  domains-overview.json        # 50 domains across categories
  override-log.json            # 30 days of override history
  audit-events.json            # Sample audit events for all types
  empty-state.json             # Empty responses for new-install testing
  error-responses.json         # All error code variants
```

### Deterministic Clocks

For override expiry and time-based tests:

```typescript
// Use vi.useFakeTimers() in Vitest
beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-02-09T15:00:00Z'));
});

afterEach(() => {
  vi.useRealTimers();
});

test('override countdown reaches zero', async () => {
  // Create override expiring in 300s
  render(<OverrideCountdown expiresAt="2026-02-09T15:05:00Z" />);
  expect(screen.getByText('5:00')).toBeInTheDocument();

  // Advance 4 minutes
  act(() => vi.advanceTimersByTime(240_000));
  expect(screen.getByText('1:00')).toBeInTheDocument();

  // Advance to expiry
  act(() => vi.advanceTimersByTime(60_000));
  expect(screen.getByText('Expired')).toBeInTheDocument();
});
```

### Audit Log Validation

```typescript
// Helper to verify audit log entries after admin actions
async function expectAuditEntry(params: {
  domain: string;
  event_type: string;
  after: Date;
}) {
  const res = await fetch(
    `/admin/api/v1/reports/audit?domain=${params.domain}&event_type=${params.event_type}&since=${params.after.toISOString()}&limit=1`,
    { headers: authHeaders }
  );
  const data = await res.json();
  expect(data.events.length).toBeGreaterThan(0);
  expect(data.events[0].event_type).toBe(params.event_type);
  expect(data.events[0].domain).toBe(params.domain);
  return data.events[0];
}

// Usage in E2E test
test('allowing a site creates audit entry', async () => {
  const before = new Date();
  // ... perform allow action via UI ...
  const entry = await expectAuditEntry({
    domain: 'youtube.com',
    event_type: 'admin_allow',
    after: before,
  });
  expect(entry.reason).toBeTruthy();
});
```

---

# Section J — Risk Register & Mitigation

## J.1 Agent Offline / Out-of-Sync

| Attribute | Detail |
|---|---|
| **Risk** | Agent device is offline, powered off, or network-unreachable when admin makes changes. |
| **Likelihood** | High (laptops sleep, travel, network changes) |
| **Impact** | Admin actions appear to succeed but are not enforced. User bypasses blocking during offline window. |
| **Mitigation (MVP)** | Admin gateway checks agent health before mutations. If unreachable, return `DEVICE_OFFLINE` error with `last_seen` timestamp. UI shows "Device offline — changes will not take effect until device reconnects." |
| **Mitigation (Phase 4)** | Action queue: gateway stores pending mutations. Agent polls for queued actions on reconnect. Conflict resolution: last-write-wins with audit trail. |
| **Detection** | Heartbeat polling (every 30s). `HeartbeatMonitor` already exists in `runner.py`. Expose last-heartbeat via `/api/health`. |

## J.2 Conflicts Between Rules and Exceptions

| Attribute | Detail |
|---|---|
| **Risk** | Domain is simultaneously in always-allowed list AND has a blocking rule, or has an active override AND admin blocks it. |
| **Likelihood** | Medium (admin error, multiple admins, stale state) |
| **Impact** | Unpredictable blocking behavior. User confusion. |
| **Mitigation** | Define clear precedence: (1) Emergency override > (2) Admin block > (3) Always-allowed > (4) Active override > (5) Classification budget > (6) Category block. Document in UI. Admin gateway validates mutations and returns `CONFLICT` error with explanation when precedence would cause unexpected behavior. |
| **Existing support** | `BlockingManager.should_block()` already checks overrides before rules. `DomainConfigManager` has `get_domain_status()` which resolves status. Extend with explicit conflict detection. |

## J.3 Security of Admin Access

| Attribute | Detail |
|---|---|
| **Risk** | Unauthorized access to admin UI allows disabling blocking, viewing browsing history, or modifying rules. |
| **Likelihood** | Medium (LAN access, shared networks, shoulder surfing) |
| **Impact** | Critical — complete bypass of FocusGuard protections. Privacy violation. |
| **Mitigation (MVP)** | JWT auth with strong password. Session timeout (30 min idle). Login attempts rate-limited (5 failures → 15 min lockout). All auth failures logged to audit + email alert. Admin UI only accessible via LAN (not exposed to internet). |
| **Mitigation (Phase 4)** | HTTPS (self-signed or LAN CA). Optional 2FA (TOTP). Role-based access. Session management (force logout, concurrent session limit). IP allowlist. |
| **Existing support** | `APIAuthManager` handles bearer token auth for tab server. `config_password_hash` protects enforcement mode changes. Email alerts on failed password attempts already implemented in `server.py`. |

## J.4 Reporting Privacy Concerns

| Attribute | Detail |
|---|---|
| **Risk** | Detailed browsing history and search logs feel like surveillance. User (especially older children) may feel violated, damaging trust. |
| **Likelihood** | High (inherent tension in monitoring tools) |
| **Impact** | User circumvention attempts increase. Relationship damage. |
| **Mitigation** | (1) Use neutral, non-punitive language throughout UI (already a constraint). (2) Reports show patterns and categories, not individual URLs by default. (3) "Detailed view" requires explicit click (progressive disclosure). (4) Focus on actionable insights ("youtube.com overridden 3x — consider budgeting") not raw surveillance ("visited youtube.com at 3:15 PM for 12 minutes"). (5) Privacy policy visible in settings. (6) Configurable detail level in `DeploymentConfig`. |
| **Existing support** | `PopupConfig.tone` already supports encouraging/firm/playful. Email reports use `get_summary_for_email()` which provides summaries, not raw logs. |

## J.5 UX Complexity Creep

| Attribute | Detail |
|---|---|
| **Risk** | Adding features across phases makes the UI overwhelming. Admin spends more time configuring than the tool saves. |
| **Likelihood** | High (natural tendency in feature-rich tools) |
| **Impact** | Admin abandons the tool or misconfigures it. |
| **Mitigation** | (1) Dashboard "Needs Attention" pattern — surface only actionable items, not everything. (2) Sensible defaults for all settings (existing `DeploymentConfig` defaults are good). (3) Progressive disclosure — advanced settings behind expandable sections. (4) "Quick actions" for the 3 most common tasks (allow, block, emergency). (5) Each phase has UX review checkpoint before proceeding. (6) Mobile view forces simplification — if it doesn't fit on mobile, reconsider if it's needed. |

## J.6 Race Conditions and Eventual Consistency

| Attribute | Detail |
|---|---|
| **Risk** | Admin allows a site, but the agent's blocking cache hasn't expired yet (up to 30s TTL in `BlockingManager`). User still sees block page. |
| **Likelihood** | Medium (every override/rule change has a propagation delay) |
| **Impact** | Low — temporary confusion, resolves within 30s. |
| **Mitigation** | (1) After mutation, UI shows "Change applied. May take up to 30 seconds to take effect." (2) For overrides: `OverrideManager` is checked on every `should_block` call, so overrides are near-instant. (3) For rule changes: `BlockingManager` cache TTL is 30s; consider adding a cache-invalidation signal. (4) For `domain_config.json` changes: `DomainConfigManager` change callbacks already notify listeners. (5) Phase 3 WebSocket can push "rule applied" confirmation back to UI. |
| **Existing support** | `BlockingManager._cache` has configurable TTL. `DomainConfigManager._change_callbacks` notify on config changes. Override checks bypass the blocking cache. |

## J.7 Tab Server Port Conflicts

| Attribute | Detail |
|---|---|
| **Risk** | Tab server (port 8765) or admin server (port 3000) conflicts with another application on the machine. |
| **Likelihood** | Low (uncommon ports) |
| **Impact** | FocusGuard fails to start or admin UI is inaccessible. |
| **Mitigation** | (1) Configurable ports in `DeploymentConfig` (`tab_server_port`, `admin_ui_port`). (2) Startup check: if port in use, try next port and log warning. (3) Port displayed in system tray tooltip / startup log. (4) Browser extension configured with correct port via `extension_config.json`. |
| **Existing support** | Tab server port is configurable in `runner.py`. `ApiServerComponent` port is configurable via config manager. |

## J.8 Data Loss / Corruption

| Attribute | Detail |
|---|---|
| **Risk** | `domain_config.json`, audit logs, or override logs become corrupted (crash during write, disk full, permission error). |
| **Likelihood** | Low (but catastrophic when it happens) |
| **Impact** | Rules lost (all blocking stops), audit trail gaps, override state inconsistent. |
| **Mitigation** | (1) `DomainConfigManager` already has SHA-256 integrity check + tamper detection + auto-revert to last known good. (2) Atomic writes: write to temp file, then rename (already implemented in `DomainConfigManager._save_config()`). (3) Backup config on each successful save (keep last 5). (4) Audit logger: if write fails, buffer in memory and retry. (5) Phase 4: policy versioning provides implicit backup. |
| **Existing support** | `DomainConfigManager` integrity checks, `SecureStorage` with ACLs, `config_tamper_detected` email alerts. |

## J.9 Browser Extension Disconnection

| Attribute | Detail |
|---|---|
| **Risk** | Browser extension loses connection to tab server. Blocking stops working in the browser. |
| **Likelihood** | Medium (browser updates, extension crashes, tab server restart) |
| **Impact** | High — blocking completely bypassed until reconnection. |
| **Mitigation** | (1) `HeartbeatMonitor` detects disconnection and logs event. (2) `background.js` fail-closed: blocks non-safe domains when server unreachable (already implemented). (3) `declarativeNetRequest` rules synced as backup blocking (already implemented). (4) Admin UI shows browser connection status via `GET /api/status`. (5) Email alert on prolonged disconnection. |
| **Existing support** | Fail-closed in `background.js`, `declarativeNetRequest` sync, `HeartbeatMonitor`, browser status in `TabStorage`. |

## J.10 Admin Gateway as Single Point of Failure

| Attribute | Detail |
|---|---|
| **Risk** | If the admin gateway process crashes, admin loses all remote access. Agent continues enforcing but admin cannot make changes. |
| **Likelihood** | Low (simple HTTP server) |
| **Impact** | Medium — blocking continues (safe default), but admin cannot respond to user needs. |
| **Mitigation** | (1) Admin gateway runs as a supervised process alongside tab server in `runner.py`. Auto-restart on crash. (2) Health check endpoint for monitoring. (3) Fallback: admin can SSH/RDP to machine and use tab server directly via `curl` or local browser. (4) Agent's self-service override system (via browser extension popup) remains functional even if admin gateway is down. |

---

# Addendum K — Application Monitoring, Blocking & Reporting

> The original Sections A–J are browser/domain-centric. FocusGuard also monitors and blocks **desktop applications and windows** via a parallel subsystem. This addendum extends every relevant section to cover application-level tracking, blocking, reporting, and admin control.

## K.1 Additional System Primitives (extends Section A)

### Existing Entities — Application Layer

| Entity | Description | Storage | ID Format | File |
|---|---|---|---|---|
| **WindowInfo** | Snapshot of active window: `app_name`, `window_title`, `pid`, `hwnd`, `rect`, `area`, `percent`, optional `url`/`domain` | In-memory | `pid` + `hwnd` | `core/activity/models.py` |
| **ActivityEvent** | Timestamped record of window activation, tab change, idle state change | In-memory + `ActivityLogger` on disk | Timestamp | `core/activity/models.py` |
| **BlockingPolicy** | Rich policy: `app_patterns`, `app_blacklist`, `app_whitelist`, `domain_patterns`, time restrictions, grace period, override settings | `PolicyEngine` in-memory (import/export to dict) | `name` string | `core/activity/blocking/models.py` |
| **BlockingDecision** | Result of evaluating a window against policies: action (ALLOW/WARN/BLOCK/REDIRECT), grace period, override flag | In-memory | Transient | `core/activity/blocking/models.py` |
| **BlockingEvent** | Logged event: blocked/warned/overridden/grace_period for an app | `PolicyEngine.blocking_events` list (last 1000) | Transient | `core/activity/blocking/models.py` |
| **TimeRestriction** | Time-based rule: `DAILY_HOURS`, `DAILY_LIMIT`, `WEEKLY_LIMIT`, `BREAK_INTERVAL` with day-of-week support | Embedded in `BlockingPolicy` | N/A | `core/activity/blocking/models.py` |
| **OverrideRequest (App)** | Request to override app block: `app_name`, `domain`, `reason`, `duration_minutes`, `password` | `PolicyEngine.active_overrides` dict | `app_name:domain` key | `core/activity/blocking/models.py` |
| **BlockingSystem** | Integrated system: `PolicyEngine` + `ApplicationBlocker` + `NotificationManager` | Singleton-like | N/A | `core/activity/blocking/blocking_system.py` |

### Existing Capabilities — Application Layer

| Capability | Implementation | Status |
|---|---|---|
| **Active window polling** | `ActivityMonitor.get_active_window()` → `WindowsActivityMonitor` (win32gui/psutil) | Working |
| **Top windows detection** | `ActivityMonitor.get_top_windows()` — visible windows in top screen region | Working |
| **Idle detection** | `IdleDetector` with configurable thresholds | Working |
| **App blocking by name** | `BlockingPolicy.app_blacklist` / `app_patterns` matching | Working |
| **App whitelisting** | `BlockingPolicy.app_whitelist` — only allow listed apps | Working |
| **Time-based restrictions** | `TimeRestriction` — daily hours, daily/weekly limits, break intervals | Working (limits placeholder) |
| **Grace period before block** | `ApplicationBlocker._start_grace_period()` — configurable seconds | Working |
| **Process termination** | `ProcessManager.terminate_process()` — graceful then force | Working |
| **App override (local)** | `PolicyEngine.request_override()` — time-limited, password-optional | Working |
| **Override revocation** | `PolicyEngine.revoke_override()` | Working |
| **Blocking notifications** | `NotificationManager` — Windows toast, macOS osascript, Linux notify-send | Working |
| **Override dialog (local)** | `NotificationManager.show_override_dialog()` — tkinter/zenity/osascript | Working |
| **Context switch detection** | `ContextSwitchRule` — alerts on excessive app switching | Working |
| **Usage tracking** | `PolicyEngine._update_usage_tracking()` — per app:domain decision counts | Working |
| **Blocking statistics** | `ApplicationBlocker.get_blocking_statistics()` — totals + active counts | Working |
| **Policy import/export** | `PolicyEngine.export_policies()` / `import_policies()` — dict serialization | Working |
| **Event bus integration** | `ActivityMonitorComponent` publishes `WINDOW_CHANGED`, `IDLE_STATE_CHANGED` | Working |

### Application-Layer Capability Gaps

| ID | Gap | Impact | Effort |
|---|---|---|---|
| **GA1** | No admin API endpoints for app blocking policies | Admin cannot manage app policies from web UI | Medium |
| **GA2** | No persistent storage for `BlockingPolicy` objects | Policies lost on restart; only in-memory | Medium |
| **GA3** | No app usage time tracking (only decision counts) | Cannot show "Spotify: 45 min today" in dashboard | Medium |
| **GA4** | No app categorization system (unlike domain categories) | Cannot group apps by type (games, social, productivity) | Medium |
| **GA5** | No app-level budgets (only time restrictions in policy) | Cannot set "30 min/day for games" like domain budgets | Medium |
| **GA6** | `PolicyEngine` usage limits check is a placeholder | `_exceeds_usage_limits()` always returns `False` | Small |
| **GA7** | No app blocking audit trail (separate from browser audit) | App blocks not visible in admin reports | Medium |
| **GA8** | No app-level override audit logging | App overrides not tracked for accountability | Small |
| **GA9** | App blocking and browser blocking are separate systems | No unified view; admin must manage two rule sets | Large |
| **GA10** | No app usage history persistence | Cannot show weekly app usage trends | Medium |

---

## K.2 Application UX Workflows (extends Section B)

### B.9 — Block an Application

- **Priority:** P1 (core admin action)
- **Trigger:** Admin wants to prevent user from running a specific application (e.g., Steam, Discord desktop app, games)
- **Goal:** Application is terminated (with grace period) whenever launched; logged in audit trail
- **Steps:**
  1. Admin navigates to Rules → Applications tab
  2. Searches or browses application list
  3. Selects app → chooses action: Block / Warn / Time-Restrict
  4. Optionally sets grace period, warning message, override policy
  5. Confirms → policy saved and enforced immediately
- **Backend/Agent State Changes:**
  - `PolicyEngine.add_policy(BlockingPolicy)` with `app_blacklist: ["steam.exe"]`
  - Policy persisted to `app_policies.json` (**GA2** — new file)
  - `ApplicationBlocker` picks up policy on next evaluation cycle (< 1s)
- **Required Telemetry:** `app_policy_created`, `app_blocked`, `app_warned`
- **Edge Cases:**
  - System apps (explorer.exe, svchost.exe) must be protected — maintain system app whitelist
  - App renamed by user — match by window title pattern as fallback
  - Multiple processes for one app (e.g., Chrome has many) — match by process name, not PID
- **Security:** System process whitelist must be tamper-protected. App blocking requires admin auth.
- **Gaps:** GA1, GA2, GA7

### B.10 — Allow an Application (Override / Whitelist)

- **Priority:** P1
- **Trigger:** Admin wants to allow a currently blocked app temporarily or permanently
- **Goal:** App runs without interference for specified duration or permanently
- **Steps:**
  1. Admin sees blocked app in dashboard or notification
  2. Clicks "Allow" → selects scope: Temporary (5m/15m/30m/1h), Always, Scheduled
  3. Optionally adds reason
  4. Confirms → override active immediately
- **Backend/Agent State Changes:**
  - Temporary: `PolicyEngine.request_override(OverrideRequest)` — sets expiry
  - Always: Add to `app_whitelist` in matching policy, or create allow policy
  - Scheduled: Create `TimeRestriction` with `DAILY_HOURS` for allowed window
- **Required Telemetry:** `app_override_granted`, `app_whitelisted`
- **Edge Cases:**
  - Override expires while app is in use — show grace period warning before termination
  - App already running when blocked — grace period applies
- **Gaps:** GA1, GA8

### B.11 — View Application Usage Report

- **Priority:** P2
- **Trigger:** Admin wants to understand how time is spent across applications (not just browser)
- **Goal:** See time-per-app breakdown, top apps, productive vs distracting, trends
- **Steps:**
  1. Admin navigates to Reports → Applications tab
  2. Sees daily/weekly breakdown: time per app, category, productivity score
  3. Can drill into specific app: usage timeline, block/warn events, override history
  4. Can take action: block, budget, categorize from report view
- **Backend/Agent State Changes:** Read-only (unless admin takes action from report)
- **Required Telemetry:** `app_usage_session_start`, `app_usage_session_end`, `app_focus_time`
- **Edge Cases:**
  - Idle time attribution — don't count idle time toward last active app
  - Background apps — only count foreground/active window time
  - Multi-monitor — track which monitor has focus
- **Gaps:** GA3, GA4, GA5, GA10

### B.12 — Set Application Time Budget

- **Priority:** P2
- **Trigger:** Admin wants to limit daily time for a category of apps (e.g., "30 min/day for games")
- **Goal:** Apps in category are blocked after budget is exhausted; user sees countdown
- **Steps:**
  1. Admin navigates to Rules → Applications → Budgets
  2. Creates or edits budget: select app category or individual app
  3. Sets daily limit (minutes), optional weekly limit
  4. Optionally sets allowed hours (e.g., only after 4 PM)
  5. Confirms → budget enforced immediately
- **Backend/Agent State Changes:**
  - Create `BlockingPolicy` with `TimeRestriction(type=DAILY_LIMIT, max_duration_minutes=30)`
  - `PolicyEngine._exceeds_usage_limits()` must be implemented (**GA6**)
  - Usage time tracked per app per day (**GA3**)
- **Required Telemetry:** `app_budget_created`, `app_budget_warning`, `app_budget_exhausted`
- **Edge Cases:**
  - Budget shared across category (all games share 30 min) vs per-app
  - App recategorized mid-day — budget carries over or resets?
  - Budget rollover — unused time does NOT roll over (daily reset)
- **Gaps:** GA3, GA4, GA5, GA6

### B.13 — Manage Application Categories

- **Priority:** P2
- **Trigger:** Admin wants to group applications into categories for bulk rules and reporting
- **Goal:** Apps organized into categories (Games, Social, Productivity, Education, etc.)
- **Steps:**
  1. Admin navigates to Rules → Applications → Categories
  2. Sees auto-detected apps with suggested categories
  3. Can reassign apps between categories, create custom categories
  4. Category-level rules apply to all member apps
- **Backend/Agent State Changes:**
  - New `AppCategoryManager` (analogous to `DomainConfigManager`) — persists to `app_categories.json`
  - Categories: `games`, `social`, `productivity`, `education`, `entertainment`, `communication`, `development`, `system`, `other`
- **Required Telemetry:** `app_categorized`, `app_category_changed`
- **Gaps:** GA4

---

## K.3 Application Wireframes (extends Section C)

### C.9 — Application Rules Editor

```
+-------------------------------------------------------------+
|  Rules & Configuration                                      |
+-------------------------------------------------------------+
|  [Domains] [Applications] [Categories] [Budgets]            |
+-------------------------------------------------------------+
|  Search: [Filter apps...          ]  Status: [All v]        |
|                                                              |
|  Application      | Category      | Status   | Budget | Act |
|  -----------------+---------------+----------+--------+---- |
|  steam.exe        | games         | blocked  |  --    | [E] |
|  discord.exe      | social        | budgeted | 30m/d  | [E] |
|  spotify.exe      | entertainment | allowed  |  --    | [E] |
|  code.exe         | development   | allowed  |  --    | [E] |
|  vlc.exe          | entertainment | warned   | 60m/d  | [E] |
|                                                              |
|  [+ Add App Rule]                  Page 1 of 2 [< >]        |
+-------------------------------------------------------------+
|  Detected Apps (not yet categorized):                        |
|  notepad++.exe, putty.exe, filezilla.exe  [Categorize All]  |
+-------------------------------------------------------------+
```

- **Click path:** Nav → Rules → Applications tab → Filter/search → [E] → Edit modal
- **Backend calls:** `GET /admin/api/v1/apps/policies`, then mutations per edit
- **Agent action:** Immediate via `PolicyEngine.add_policy()` / `update_policy()`
- **Audit:** `app_policy_changed` event

### C.10 — Application Usage Dashboard Widget

```
+-------------------------------------------------------+
| Application Usage Today                                |
+-------------------------------------------------------+
|                                                        |
|  code.exe          ==================== 2h 15m  [ok]   |
|  chrome.exe        ==============       1h 30m  [ok]   |
|  discord.exe       =====                32m/30m [!]    |
|  spotify.exe       ====                 28m     [ok]   |
|  steam.exe         X blocked (3 attempts)       [E]    |
|                                                        |
|  Total Active: 5h 45m  |  Productive: 72%             |
|  Context Switches: 23  |  Idle: 1h 15m                |
|                                                        |
|  [View Full Report]  [Manage App Rules]                |
+-------------------------------------------------------+
```

- **Click path:** Dashboard → "Application Usage" widget (below browser section)
- **Backend calls:** `GET /admin/api/v1/apps/usage/today?device_id=`
- **Agent action:** None (read-only)
- **Audit:** None

### C.11 — Block Application Modal

```
+-----------------------------------------+
|  Block Application                [X]   |
+-----------------------------------------+
|                                         |
|  Application: [_____________________]   |
|  (or select from detected apps v)       |
|                                         |
|  Action:                                |
|  (*) Block (terminate + prevent)        |
|  ( ) Warn (show notification only)      |
|  ( ) Time-restrict (set budget)         |
|                                         |
|  Grace period: [30 seconds v]           |
|  Override allowed: [x] Yes              |
|                                         |
|  Category: [games v]                    |
|                                         |
|  Schedule (optional):                   |
|  [ ] Only during: [9:00 AM] - [4:00 PM]|
|  [ ] Days: [x]M [x]T [x]W [x]T [x]F   |
|                                         |
|  [Cancel]            [Block App]        |
+-----------------------------------------+
```

- **Click path:** Dashboard → [+ Block App] or Rules → Applications → [+ Add App Rule]
- **Backend calls:** `POST /admin/api/v1/apps/policies`
- **Agent action:** `PolicyEngine.add_policy()` → immediate enforcement
- **Audit:** `app_policy_created` event

### C.12 — Application Time Budget Editor

```
+-----------------------------------------+
|  App Time Budget: Games           [X]   |
+-----------------------------------------+
|                                         |
|  Category: Games (5 apps)               |
|  steam.exe, epicgames.exe,              |
|  roblox.exe, minecraft.exe, gog.exe     |
|                                         |
|  Daily limit: [30] minutes              |
|  Weekly limit: [___] minutes (optional) |
|                                         |
|  Allowed hours (optional):              |
|  [x] Only after: [4:00 PM]             |
|  [ ] Only on weekends                   |
|                                         |
|  When budget exhausted:                 |
|  (*) Block immediately                  |
|  ( ) Warn then block after [5] min      |
|                                         |
|  Used today: 12m / 30m (40%)            |
|  ========--------                       |
|                                         |
|  [Cancel]          [Save Budget]        |
+-----------------------------------------+
```

- **Click path:** Rules → Applications → Budgets → Edit category budget
- **Backend calls:** `PUT /admin/api/v1/apps/budgets/{category}`
- **Agent action:** `PolicyEngine` updated with `TimeRestriction(DAILY_LIMIT)`
- **Audit:** `app_budget_changed` event

---

## K.4 Application API Endpoints (extends Section E)

### Application Policies

```
GET /admin/api/v1/apps/policies?device_id=&category=&status=&search=&limit=&offset=
  Response: {
    "policies": [
      {
        "id": "policy_steam_block",
        "name": "Block Steam",
        "app_patterns": ["steam.exe", "steamwebhelper.exe"],
        "app_blacklist": ["steam.exe"],
        "category": "games",
        "action": "block",
        "grace_period_seconds": 30,
        "override_allowed": true,
        "time_restrictions": [],
        "enabled": true,
        "created_at": "ISO8601",
        "updated_at": "ISO8601"
      }
    ],
    "total": 12
  }

POST /admin/api/v1/apps/policies
  Request: {
    "name": "Block Steam",
    "app_patterns": ["steam.exe"],
    "category": "games",
    "action": "block",
    "grace_period_seconds": 30,
    "override_allowed": true,
    "time_restrictions": [
      { "type": "daily_hours", "start_time": "09:00", "end_time": "16:00",
        "days_of_week": [0,1,2,3,4] }
    ]
  }
  Response: { "id": "policy_abc", "created": true }

PUT /admin/api/v1/apps/policies/{id}
  Request: { ... same fields as POST ... }
  Response: { "updated": true }

DELETE /admin/api/v1/apps/policies/{id}
  Response: { "deleted": true }
```

**Implementation:** New admin gateway endpoints → new `AppPolicyManager` that wraps `PolicyEngine.add_policy()` / `remove_policy()` / `update_policy()` with persistence to `app_policies.json`.

### Application Overrides

```
POST /admin/api/v1/apps/overrides
  Request: {
    "device_id": "prasun-pc",
    "app_name": "steam.exe",
    "duration_minutes": 30,
    "reason": "downloading game update"
  }
  Response: { "id": "ovr_abc", "expires_at": "ISO8601" }

GET /admin/api/v1/apps/overrides?device_id=&status=active|expired|all
  Response: { "overrides": [...], "total": 5 }

DELETE /admin/api/v1/apps/overrides/{app_name}
  Response: { "revoked": true }
```

**Implementation:** Maps to `PolicyEngine.request_override()`, `get_active_overrides()`, `revoke_override()`.

### Application Categories

```
GET /admin/api/v1/apps/categories?device_id=
  Response: {
    "categories": {
      "games": { "apps": ["steam.exe", "epicgames.exe"], "status": "blocked", "budget_minutes": null },
      "social": { "apps": ["discord.exe", "slack.exe"], "status": "budgeted", "budget_minutes": 30 },
      "productivity": { "apps": ["code.exe", "notepad++.exe"], "status": "allowed", "budget_minutes": null }
    }
  }

PUT /admin/api/v1/apps/categories/{category}
  Request: { "apps": ["steam.exe", "epicgames.exe", "roblox.exe"], "status": "blocked" }
  Response: { "updated": true }

POST /admin/api/v1/apps/categories/{category}/apps
  Request: { "app_name": "minecraft.exe" }
  Response: { "added": true }

DELETE /admin/api/v1/apps/categories/{category}/apps/{app_name}
  Response: { "removed": true }
```

**Implementation:** New `AppCategoryManager` (**GA4**) — persists to `app_categories.json`.

### Application Budgets

```
GET /admin/api/v1/apps/budgets?device_id=
  Response: {
    "per_app": {
      "discord.exe": { "daily_limit_minutes": 30, "used_today_minutes": 12, "percent": 40 }
    },
    "per_category": {
      "games": { "daily_limit_minutes": 30, "used_today_minutes": 0, "percent": 0 }
    }
  }

PUT /admin/api/v1/apps/budgets/app/{app_name}
  Request: { "daily_limit_minutes": 30, "weekly_limit_minutes": 150 }
  Response: { "updated": true }

PUT /admin/api/v1/apps/budgets/category/{category}
  Request: { "daily_limit_minutes": 60, "allowed_hours": { "start": "16:00", "end": "21:00" } }
  Response: { "updated": true }
```

**Implementation:** Requires **GA3** (app usage time tracking) and **GA5** (app-level budgets) and **GA6** (implement `_exceeds_usage_limits()`).

### Application Usage & Reporting

```
GET /admin/api/v1/apps/usage/today?device_id=
  Response: {
    "apps": [
      { "app_name": "code.exe", "category": "development", "active_minutes": 135,
        "status": "allowed", "block_attempts": 0 },
      { "app_name": "discord.exe", "category": "social", "active_minutes": 32,
        "status": "budgeted", "budget_minutes": 30, "over_budget": true }
    ],
    "total_active_minutes": 345,
    "productive_percent": 72,
    "context_switches": 23,
    "idle_minutes": 75
  }

GET /admin/api/v1/apps/usage/history?device_id=&since=&until=&app_name=&category=
  Response: {
    "daily": [
      { "date": "2026-02-09", "apps": [...], "productive_percent": 72 },
      { "date": "2026-02-08", "apps": [...], "productive_percent": 68 }
    ]
  }

GET /admin/api/v1/apps/blocking/events?device_id=&since=&until=&app_name=&limit=&offset=
  Response: {
    "events": [
      { "timestamp": "ISO8601", "event_type": "blocked", "app_name": "steam.exe",
        "policy_name": "Block Steam", "reason": "Blocked by policy" }
    ],
    "total": 15
  }

GET /admin/api/v1/apps/detected?device_id=
  Response: {
    "detected": [
      { "app_name": "notepad++.exe", "first_seen": "ISO8601", "last_seen": "ISO8601",
        "total_minutes_today": 15, "category": null, "policy": null }
    ]
  }
```

**Implementation:** `apps/usage/today` aggregated from `PolicyEngine.usage_tracking` + new `AppUsageTracker` (**GA3**). `apps/detected` from `ActivityMonitor` window polling history. `apps/blocking/events` from `PolicyEngine.blocking_events` + new persistent log (**GA7**).

---

## K.5 Application Telemetry Events (extends Section F)

| Event Type | Source | Description |
|---|---|---|
| `app_policy_created` | Admin UI | New app blocking policy created |
| `app_policy_changed` | Admin UI | App policy modified |
| `app_policy_deleted` | Admin UI | App policy removed |
| `app_blocked` | Agent | Application terminated by policy |
| `app_warned` | Agent | Warning shown for restricted app |
| `app_grace_period` | Agent | Grace period started before block |
| `app_override_granted` | Agent/Admin | App override approved |
| `app_override_expired` | Agent | App override time elapsed |
| `app_override_revoked` | Admin | App override manually revoked |
| `app_budget_created` | Admin UI | App time budget created |
| `app_budget_warning` | Agent | App budget at 70%+ |
| `app_budget_exhausted` | Agent | App daily budget fully consumed |
| `app_categorized` | Admin UI | App assigned to category |
| `app_usage_session_start` | Agent | App became foreground window |
| `app_usage_session_end` | Agent | App lost foreground focus |
| `context_switch_alert` | Agent | Excessive app switching detected |
| `idle_state_changed` | Agent | User went idle / returned from idle |

**Existing coverage:** `BlockingEvent` in `models.py` covers `blocked`, `warned`, `overridden`, `grace_period`. `EventTypes.WINDOW_CHANGED` and `IDLE_STATE_CHANGED` in coordinator events.

**Gap:** All `app_policy_*`, `app_budget_*`, `app_categorized`, `app_usage_session_*` events are new. Need `AppAuditLogger` (analogous to browser `AuditLogger`) or extend existing `AuditLogger` with app event types.

---

## K.6 Application Dashboard Aggregations (extends Section F.3)

| Aggregation | Purpose | Computation |
|---|---|---|
| **Time per app (daily)** | App usage breakdown | `SUM(session_duration) GROUP BY app_name WHERE date = today` |
| **Time per category (daily)** | Category breakdown | `SUM(session_duration) GROUP BY category` |
| **Productive time percent** | Headline metric | `productive_time / (productive_time + distracting_time) * 100` |
| **Top distracting apps (weekly)** | Actionable insight | Apps in distracting categories sorted by total time |
| **App block attempts (daily)** | Enforcement metric | `COUNT(app_blocked) GROUP BY app_name` |
| **Context switch frequency** | Focus indicator | `COUNT(WINDOW_CHANGED) per hour` |
| **App budget utilization** | Budget health | `used_minutes / budget_minutes` per app/category |
| **Idle time (daily)** | Activity metric | `SUM(idle_duration) WHERE date = today` |
| **App usage trend (7-day)** | Progress tracking | Daily productive_percent array |

---

## K.7 Phased Integration (extends Section G)

### Phase 1 Additions (MVP)

| Area | Task | Scope |
|---|---|---|
| Backend | `AppPolicyManager` — CRUD for `BlockingPolicy` with persistence to `app_policies.json` | Medium |
| Backend | Admin API endpoints: `GET/POST/PUT/DELETE /admin/api/v1/apps/policies` | Medium |
| Backend | Admin API: `POST/GET/DELETE /admin/api/v1/apps/overrides` | Small |
| Backend | Wire `PolicyEngine` into admin gateway (read policies on startup, save on change) | Small |
| Frontend | "Applications" tab in Rules page (Wireframe C.9) | Medium |
| Frontend | Block Application modal (Wireframe C.11) | Small |
| Agent | Persist `BlockingPolicy` list to `app_policies.json` on mutation | Small |
| Agent | Load policies from `app_policies.json` on startup | Small |

### Phase 2 Additions

| Area | Task | Scope |
|---|---|---|
| Backend | `AppCategoryManager` — app categorization with persistence (**GA4**) | Medium |
| Backend | `AppUsageTracker` — foreground time tracking per app (**GA3**) | Medium |
| Backend | Implement `PolicyEngine._exceeds_usage_limits()` (**GA6**) | Small |
| Backend | Admin API: app categories, budgets, usage endpoints | Medium |
| Frontend | Application Usage dashboard widget (Wireframe C.10) | Medium |
| Frontend | App Time Budget editor (Wireframe C.12) | Medium |
| Frontend | App category management UI | Medium |
| Agent | Track foreground app sessions (start/end timestamps, duration) | Medium |
| Agent | Persist daily app usage stats to `app_usage_history.json` (**GA10**) | Small |

### Phase 3 Additions

| Area | Task | Scope |
|---|---|---|
| Backend | App usage reporting endpoints (daily, weekly, history) | Medium |
| Backend | App blocking event log persistence (**GA7**) | Small |
| Backend | App override audit logging (**GA8**) | Small |
| Frontend | Application reports page (time charts, category breakdown, trends) | Large |
| Frontend | Context switch visualization | Small |
| Frontend | Unified view: browser + app activity in single timeline (**GA9** partial) | Large |

---

## K.8 Application-Specific Frontend Components (extends Section H.2)

| Component | Description | Phase |
|---|---|---|
| `AppPolicyTable` | Sortable/filterable table of app blocking policies | 1 |
| `BlockAppModal` | Create/edit app blocking policy with schedule options | 1 |
| `AppOverrideList` | Active app overrides with countdown timers | 1 |
| `AppUsageWidget` | Dashboard widget: bar chart of time per app today | 2 |
| `AppCategoryManager` | Assign apps to categories, create custom categories | 2 |
| `AppBudgetEditor` | Per-app and per-category time budget form | 2 |
| `DetectedAppsList` | Uncategorized apps detected by agent, with quick-categorize actions | 2 |
| `AppUsageChart` | Line/bar chart: daily app usage over time | 3 |
| `AppBlockingLog` | Paginated log of app block/warn/override events | 3 |
| `UnifiedTimeline` | Combined browser + app activity timeline | 3 |
| `ProductivityScore` | Circular gauge: productive vs distracting time (apps + browser) | 2 |

---

## K.9 Application Testing (extends Section I)

### Unit Tests

| Test Suite | What to Test |
|---|---|
| `AppPolicyTable.test.tsx` | Renders policies, sort/filter, inline edit triggers |
| `BlockAppModal.test.tsx` | Form validation: app name required, action required, grace period >= 0 |
| `AppUsageWidget.test.tsx` | Bar widths match minutes, over-budget highlighted, empty state |
| `AppBudgetEditor.test.tsx` | Daily limit > 0, weekly >= daily * 5, allowed hours validation |

### Integration Tests

| Test | Steps |
|---|---|
| `block-app.test.ts` | Open modal → enter "steam.exe" → select "Block" → submit → verify `POST /apps/policies` payload → verify toast |
| `allow-app-temporary.test.ts` | Override list → click "Allow 30m" on blocked app → verify `POST /apps/overrides` → verify countdown |
| `set-app-budget.test.ts` | Budget editor → select "games" → set 30m → save → verify `PUT /apps/budgets/category/games` |
| `categorize-app.test.ts` | Detected apps list → click "Categorize" → select "games" → verify `POST /apps/categories/games/apps` |

### E2E Tests (Playwright)

| Test | Critical Path |
|---|---|
| `app-block-flow.spec.ts` | Rules → Applications → [+ Add App Rule] → fill "steam.exe" → Block → confirm → appears in table |
| `app-budget-flow.spec.ts` | Rules → Applications → Budgets → edit "games" → set 30m → save → budget shows in table |
| `app-usage-dashboard.spec.ts` | Dashboard → scroll to "Application Usage" → verify bars render → click "View Full Report" → report page loads |

### Agent-in-the-Loop Tests

| Test | Steps | Verification |
|---|---|---|
| `agent-app-blocked.test.ts` | Admin blocks "notepad.exe" via UI → launch notepad on agent | Notepad terminated within grace period |
| `agent-app-override.test.ts` | Admin grants 5m override for "notepad.exe" → launch notepad | Notepad runs; after 5m, terminated |
| `agent-app-usage.test.ts` | Focus on "code.exe" for 60s → query usage API | `code.exe` shows ~1 min active time |

---

## K.10 Application-Specific Risks (extends Section J)

### J.11 System Process Termination

| Attribute | Detail |
|---|---|
| **Risk** | Admin accidentally blocks a system-critical process (explorer.exe, svchost.exe, csrss.exe), causing OS instability or crash. |
| **Likelihood** | Medium (user error, especially with pattern matching like "*.exe") |
| **Impact** | Critical — OS crash, data loss, requires reboot |
| **Mitigation** | (1) Maintain hardcoded system process whitelist that cannot be overridden: `explorer.exe`, `svchost.exe`, `csrss.exe`, `winlogon.exe`, `dwm.exe`, `taskmgr.exe`, `lsass.exe`, `services.exe`, `smss.exe`, `wininit.exe`, `FocusGuard.exe`. (2) Admin UI shows warning when blocking pattern matches a system process. (3) `ApplicationBlocker` refuses to terminate PIDs in system whitelist. (4) Pattern matching validates against known system processes before saving. |
| **Existing support** | `ProcessManager.terminate_process()` exists but has no system process protection — **must be added**. |

### J.12 App Blocking Evasion via Rename

| Attribute | Detail |
|---|---|
| **Risk** | User renames `steam.exe` to `homework.exe` to bypass app blocking policy. |
| **Likelihood** | Medium (tech-savvy users) |
| **Impact** | Medium — blocking bypassed for that app |
| **Mitigation** | (1) Match by window title patterns in addition to process name (Steam's window title contains "Steam" regardless of exe name). (2) Match by file path / install directory. (3) Match by digital signature / publisher (Phase 4+). (4) Log process name changes as suspicious activity. (5) `BlockingPolicy.app_patterns` already supports substring matching — encourage title-based patterns. |
| **Existing support** | `BlockingPolicy.matches_application()` does substring matching on `app_name`. Can be extended to match `window_title` as well. |

### J.13 App vs Browser Blocking Inconsistency

| Attribute | Detail |
|---|---|
| **Risk** | Discord blocked as app but accessible via browser (discord.com). User opens browser version to bypass app block. |
| **Likelihood** | High (obvious workaround) |
| **Impact** | Medium — undermines blocking intent |
| **Mitigation** | (1) When admin blocks an app, suggest also blocking the corresponding domain (show "Also block discord.com?" prompt). (2) Maintain app-to-domain mapping: `discord.exe` ↔ `discord.com`, `steam.exe` ↔ `store.steampowered.com`, etc. (3) Phase 3: unified blocking view that shows both app and domain rules for a service. (4) "Block Service" action that creates both app policy and domain rule simultaneously. |
| **Existing support** | None — app and browser blocking are completely separate systems (**GA9**). |

### J.14 App Usage Tracking Accuracy

| Attribute | Detail |
|---|---|
| **Risk** | Foreground time tracking is inaccurate: counts idle time, misses multi-monitor focus, doesn't distinguish active use from background window. |
| **Likelihood** | Medium |
| **Impact** | Low-Medium — inaccurate reports, unfair budget enforcement |
| **Mitigation** | (1) Subtract idle time from active app session (already have `IdleDetector`). (2) Only count time when app is foreground AND user is not idle. (3) For budget enforcement, use conservative estimate (count less time, not more). (4) Show "approximate" label on usage reports. (5) Multi-monitor: `get_top_windows()` already detects visible windows — can attribute time to multiple visible apps. |
| **Existing support** | `IdleDetector` provides idle time. `ActivityMonitorComponent` publishes `IDLE_STATE_CHANGED`. `WindowsActivityMonitor.get_top_windows()` detects visible windows with area/percent. |

---

## K.11 Unified Dashboard Vision

The dashboard should present a **single view** combining browser and application activity:

```
+-------------------------------------------------------------+
|  FocusGuard Admin                    [Devices v] [Settings]  |
+-------------------------------------------------------------+
|  Device: Prasun-PC  [G] Online  |  Mode: Enforcing          |
|  Focus Score: 78  |  Budget: 12m/45m (browser) + 18m/30m (apps)
+-------------------------------------------------------------+
|                                                              |
|  Timeline -- Today                                           |
|  9AM ---- 10AM ---- 11AM ---- 12PM ---- 1PM ---- 2PM - now  |
|  [code.exe]  [chrome/github]  [discord]  [chrome/yt]  [code] |
|  ==productive==  ==productive==  ##dist##  ++override++ ==p== |
|                                                              |
|  +-- Needs Attention --------------------------------+       |
|  | (!) discord.exe over budget (32m / 30m)           |       |
|  |     [Extend Budget] [Block App] [Ignore]          |       |
|  | (!) youtube.com overridden 3x today               |       |
|  |     [Promote to Rule] [Adjust Budget] [Ignore]    |       |
|  | (i) notepad++.exe detected, not categorized       |       |
|  |     [Categorize] [Block] [Allow]                  |       |
|  +---------------------------------------------------+       |
|                                                              |
|  +-- Browser Activity ----+  +-- App Activity --------+     |
|  | Budget: 12m / 45m      |  | Budget: 18m / 30m      |     |
|  | Top: youtube.com (8m)  |  | Top: discord.exe (32m) |     |
|  | Overrides: 3 today     |  | Blocks: 2 today        |     |
|  | [View Details]         |  | [View Details]         |     |
|  +------------------------+  +------------------------+     |
|                                                              |
|  Quick Actions:                                              |
|  [Allow Site] [Block Site] [Allow App] [Block App]           |
+-------------------------------------------------------------+
```

This unified view requires **GA9** (partial) — combining data from both subsystems in the dashboard aggregation endpoint. The timeline shows both browser and app activity on a single track, color-coded by productivity.

---

# Appendix: File Reference

Key files referenced in this document:

| File | Purpose |
|---|---|
| `focus_guard/core/browser_v2/tab_server/server.py` | Tab server HTTP endpoints |
| `focus_guard/core/browser_v2/tab_server/runner.py` | Tab server lifecycle and orchestration |
| `focus_guard/core/browser_v2/tab_server/override_manager.py` | Override management with budgets |
| `focus_guard/core/browser_v2/tab_server/blocking.py` | Blocking rules and decisions |
| `focus_guard/core/browser_v2/tab_server/domain_usage_tracker.py` | Domain usage tracking and budgets |
| `focus_guard/core/browser_v2/tab_server/audit_logger.py` | Structured audit logging |
| `focus_guard/core/browser_v2/tab_server/api_auth.py` | API bearer token auth |
| `focus_guard/core/browser_v2/tab_server/classification_service.py` | Domain classification |
| `focus_guard/core/browser_v2/tab_server/activity_logger.py` | Activity event logging |
| `focus_guard/core/browser_v2/tab_server/search_logger.py` | Search query logging |
| `focus_guard/core/browser_v2/tab_server/heartbeat_monitor.py` | Extension liveness check |
| `focus_guard/core/browser_v2/tab_server/hosts_blocker.py` | OS-level hosts file blocking |
| `focus_guard/core/browser_v2/tab_server/secure_storage.py` | Secure storage with ACLs |
| `focus_guard/core/browser_v2/tab_server/api_models.py` | Typed data models (TabInfo, etc.) |
| `focus_guard/core/domain/domain_config_manager.py` | Domain config persistence + integrity |
| `focus_guard/core/distraction/config.py` | Distraction rule configuration |
| `focus_guard/core/distraction/rules/url_rule.py` | URL-based distraction detection |
| `focus_guard/core/coordinator/events.py` | Event bus and event types |
| `focus_guard/core/coordinator/components/api.py` | Coordinator API server component |
| `focus_guard/core/api/server.py` | Core aiohttp API server |
| `focus_guard/deployment/config.py` | Deployment configuration schema |
| `config/users/default.json` | Default user configuration |
| `focus_guard/core/activity/monitor.py` | Core ActivityMonitor — active window + idle detection |
| `focus_guard/core/activity/models.py` | WindowInfo, ActivityEvent data models |
| `focus_guard/core/activity/platform/base.py` | PlatformActivityMonitor abstract interface |
| `focus_guard/core/activity/platform/windows.py` | Windows win32gui/psutil active window implementation |
| `focus_guard/core/activity/blocking/models.py` | BlockingPolicy, BlockingDecision, BlockingEvent, OverrideRequest, TimeRestriction |
| `focus_guard/core/activity/blocking/policy_engine.py` | PolicyEngine — evaluates apps against policies, usage tracking, overrides |
| `focus_guard/core/activity/blocking/application_blocker.py` | ApplicationBlocker — process termination with grace periods |
| `focus_guard/core/activity/blocking/blocking_system.py` | BlockingSystem — integrated policy + blocker + notifications |
| `focus_guard/core/activity/blocking/notification_manager.py` | NotificationManager — platform-specific toast/dialog notifications |
| `focus_guard/core/distraction/detector.py` | StandardDistractionDetector — rule-based distraction detection |
| `focus_guard/core/distraction/rules/context_rule.py` | ContextSwitchRule — excessive app switching detection |
| `focus_guard/core/coordinator/components/activity.py` | ActivityMonitorComponent — event bus integration for window/idle events |

---

*End of document.*
