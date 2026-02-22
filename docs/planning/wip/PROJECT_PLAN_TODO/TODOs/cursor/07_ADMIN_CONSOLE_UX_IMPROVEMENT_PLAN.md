# FocusGuard Admin Console — UX Improvement Blueprint

**Created**: February 21, 2026  
**Purpose**: Comprehensive review of the admin console from a parent/admin perspective, with a phased plan for making it genuinely useful, intuitive, and aligned with the application's capabilities.

---

## 1. Current State Assessment

### What Exists Today
The admin console is a React + Tailwind CSS + TanStack Query SPA served at `http://127.0.0.1:58393/admin`. It has:

- **Login page** — username/password auth
- **Dashboard** — 8+ data cards (device status, focus score, budget, overrides, activity pulse, open tabs, blocked tabs, blocked sites, saved links, top friction, recent overrides, attention items)
- **Exceptions** — create/list/revoke overrides (temporary, permanent, budgeted, block)
- **Devices** — single-device status display
- **Settings** — empty placeholder
- **Saved Links** — list of URLs saved from blocked pages

### Who Uses This and Why

The **primary user is a parent** who wants to:
1. **Glance**: "Is my child focused right now?" (5-second answer)
2. **Review**: "What happened today/this week?" (2-minute review)
3. **Act**: "Block this site" / "Allow this for homework" / "Adjust time limits" (quick action)
4. **Configure**: "Set up rules, budgets, and policies" (occasional)

The **secondary user is the child/student** who sees:
- The blocked page when a site is blocked
- The extension popup showing connection status
- The saved links feature on the blocked page

---

## 2. Critical UX Problems

### P1: The Dashboard is a Data Dump, Not an Answer

The dashboard shows 8+ cards with no hierarchy. A parent opening this at dinner wants ONE answer: "How did the day go?" Instead they get a wall of numbers.

**Fix**: Redesign dashboard around two modes:
- **At-a-Glance** (default): Hero section with today's verdict (good/mixed/concerning), focus score ring with trend arrow, one-line budget status, alert count badge
- **Deep Dive** (expandable): Click to reveal detailed cards

**Proposed layout**:
```
┌─────────────────────────────────────────────────┐
│  Today's Focus                        Feb 21    │
│  ┌──────────┐  ┌───────────────────────────────┐│
│  │  Score    │  │ "Siyona had a good focus day. ││
│  │   82/100  │  │  12 min of entertainment used ││
│  │  ↑ +5     │  │  out of 45 min allowed."      ││
│  └──────────┘  └───────────────────────────────┘│
│                                                  │
│  Budget ████████████░░░░  27% used               │
│  Blocks: 4 sites blocked  Overrides: 1 used      │
│                                                  │
│  ⚠ 1 alert: reddit.com overridden 3 times today  │
└─────────────────────────────────────────────────┘
│  [Activity Timeline]  [Blocked Sites]  [Tabs]    │
│  (expandable detail sections below)              │
```

### P2: No Actionable Controls — The Admin Can't Actually Do Anything

The admin console is read-only except for creating exceptions. A parent cannot:
- Change time budgets
- Add/remove blocked domains
- Switch enforcement mode
- Change the admin password
- Configure email reports
- View or search historical activity

The Settings page is literally an empty placeholder with the text "P3-04 shell route placeholder."

**Fix**: Wire the Settings page and add quick-action buttons throughout:
- Dashboard: "Block this domain" next to each friction domain
- Dashboard: enforcement mode toggle with password confirmation
- Settings: Budget configuration (sliders, not raw seconds)
- Settings: Domain management (add to allow/block list)
- Settings: Email report configuration
- Settings: Password change
- Settings: Export data

### P3: Developer Terminology, Not Parent Language

| Current | Better |
|---------|--------|
| "Exceptions" | "Rules & Overrides" |
| "Friction Domains" | "Problem Sites" |
| "Enforcement Mode" | "Protection Level" |
| "Budget Used" | "Screen Time Used" |
| "Attention Items" | "Alerts" |
| "duration_seconds: 300" | "5 minutes" |
| "budget_seconds_per_day" | "Daily limit" |
| `frequent_override` type | "Siyona keeps trying to access reddit.com" |
| "tracking / advisory / enforcing" | "Monitor Only / Warn / Block" |

### P4: No Time Context — Everything is "Now"

There's no way to see what happened yesterday, this week, or last month. Parents check the dashboard in the evening and want to review the full day. The dashboard only shows current-moment data.

**Fix**: Add time-range selectors and an activity timeline:
- Date picker (Today / Yesterday / This Week / Custom)
- Activity timeline showing hour-by-hour breakdown
- Weekly trend charts (focus score over 7 days, budget usage trend)

### P5: Saved Links Page is a Dead End

The Saved Links page fetches its data by calling the *dashboard* endpoint and extracting the `saved_links` field. This means:
- It shows the same 5 recent links as the dashboard card
- No pagination, search, or filtering
- No way to mark as viewed or delete from the UI
- No way to "release" a link for viewing during break time

**Fix**: Dedicate a proper saved links API and UI with:
- Full paginated list with search
- Mark as viewed / delete actions
- "Allow for 30 min" quick action (creates a temporary exception)
- Grouped by domain

---

## 3. Detailed Improvement Plan

### Phase A: Dashboard Redesign (High Impact, 3-5 days)

#### A1. Hero Summary Section
Replace the current 4-card top grid with a single hero section:
- Large focus score ring with color (green/amber/red) and trend indicator (↑↓)
- Natural-language summary sentence: "Siyona had a productive day. Used 12 of 45 min entertainment budget."
- Budget progress bar (full-width, prominent)
- Quick stats row: blocks today, overrides used, active time

#### A2. Alerts & Actions Bar
Replace the current "Attention Items" chips with an actionable alert bar:
- Each alert has an icon, human-readable message, and an action button
- Example: "⚠ reddit.com was overridden 3 times → [Block Now] [Set Limit]"
- Example: "📊 Budget at 80% → [Adjust Limits]"
- Positioned prominently below the hero section

#### A3. Activity Timeline
Add a new card with an hourly activity timeline:
- Horizontal bar chart showing each hour of the day
- Color-coded: green (educational), red (entertainment/blocked), gray (idle/inactive)
- Click on an hour to see which sites were visited
- This is the single most useful thing for a parent reviewing the day

#### A4. Collapsible Detail Sections
Move current detailed cards (open tabs, blocked sites, recent overrides, friction domains) into collapsible accordion sections:
- Default collapsed to reduce visual noise
- "Open Tabs" only shown if child is currently active
- "Blocked Sites" shows domain + count + category with "Block" / "Allow" quick actions

#### A5. Date/Time Range Selector
Add a date picker above the dashboard:
- Presets: Today, Yesterday, This Week, Last 7 Days
- Custom date range
- Dashboard data re-fetches for selected period
- Requires backend support (new query parameter on dashboard aggregation)

### Phase B: Settings & Configuration (High Impact, 3-5 days)

#### B1. Budget Configuration Panel
Full budget management UI:
- Master distraction budget: slider (15 min – 4 hours) with current usage indicator
- Per-category budgets: cards for Entertainment, Social Media, Gaming with individual sliders
- Override limits: max overrides per day, override duration
- All changes save via tab server API (`/api/domains/budgets/*`)

#### B2. Domain Management Panel
Searchable domain management:
- Table of all known domains with category, status (allowed/blocked/budgeted), and usage
- Actions: Move to category, Allow, Block, Set custom budget
- Add new domain manually
- Filter by category tab (Education, Entertainment, Social Media, etc.)
- This wires to existing `/api/domains/*` endpoints

#### B3. Protection Level Toggle
Replace "enforcement_mode" with a human-friendly protection level selector:
- Three cards with icons and descriptions:
  - 🟢 **Monitor Only**: Track everything, don't block. Good for observation.
  - 🟡 **Warn**: Show warnings, but allow access. Good for building awareness.
  - 🔴 **Block**: Full enforcement. Block distracting sites when budget is spent.
- Password required to change (uses existing enforcement password)

#### B4. Email Report Configuration
Wire the email settings into the Settings page:
- Toggle: Enable/disable email reports
- Recipient email address
- Report frequency (hourly interval, daily summary)
- Test email button
- Show recent report status (last sent time, success/failure)

#### B5. Security Settings
- Change admin password
- View audit log of config changes
- View/revoke API tokens
- Extension connection status

### Phase C: Navigation & Information Architecture (Medium Impact, 2-3 days)

#### C1. Rename Routes and Navigation
| Current | New | Icon |
|---------|-----|------|
| Dashboard | Home | 🏠 |
| Exceptions | Rules & Overrides | 📋 |
| Devices | — (merge into Home) | — |
| Settings | Settings | ⚙️ |
| (not in nav) Saved Links | Saved Links | 📌 |
| (new) | Activity | 📊 |
| (new) | Alerts | 🔔 |

#### C2. Add Saved Links to Navigation
Currently missing from sidebar/bottom nav. Add it as a top-level navigation item.

#### C3. Merge Devices into Dashboard
With a single device, the Devices page adds no value. Merge device status into the dashboard hero section and into Settings. If multi-device is added later, re-introduce as its own page.

#### C4. Add Activity Page
Dedicated activity page with:
- Full-day timeline view
- Searchable/filterable activity log
- Domain usage breakdown (pie chart or bar chart)
- Historical trend view (focus score over time)

#### C5. Add Alerts/Notifications Page
Dedicated alerts page showing:
- All attention items with timestamps
- Override request history
- Config change log
- Extension disconnect events

### Phase D: Exception/Override UX Polish (Medium Impact, 2 days)

#### D1. Human-Friendly Time Inputs
Replace raw seconds inputs with human-friendly controls:
- Duration: "5 minutes" / "15 minutes" / "30 minutes" / "1 hour" / Custom
- Daily budget: slider from 0 to 120 minutes
- Show result in natural language: "Allow youtube.com for 15 minutes"

#### D2. Override History with Context
Show overrides with full context:
- Which site, when, how long, reason given
- Whether the override was used (the child actually visited the site)
- Whether it expired or was revoked
- Group by date

#### D3. Quick Actions from Dashboard
Add contextual actions to dashboard cards:
- Each blocked site: "Allow for 30 min" / "Always Allow" / "Keep Blocked"
- Each friction domain: "Block Now" / "Set Daily Limit" / "Review"
- Each override: "Revoke" / "Extend"

### Phase E: Visual Design & Polish (Lower Priority, 2-3 days)

#### E1. Design System Consistency
- Define a color palette: primary (teal/ocean), success (green), warning (amber), danger (red)
- Consistent card styles with clear visual hierarchy
- Icon set (use Lucide or Heroicons for consistency)
- Loading skeletons instead of "Loading dashboard..."

#### E2. Mobile Optimization
- Bottom nav needs Saved Links and Activity items
- Dashboard cards should stack vertically on mobile
- Touch-friendly tap targets on all buttons
- Swipe gestures for date navigation

#### E3. Dark Mode
- Add theme toggle in settings
- Use Tailwind dark: variants
- Respect system preference by default

#### E4. Blocked Page ↔ Admin Console Design Alignment
The blocked page (extension) has a polished dark gradient design. The admin console has a minimal white design. Align the branding:
- Use the same gradient colors for accent elements
- Same icon style and typography
- FocusGuard logo/wordmark in sidebar

---

## 4. Backend Support Required

| Frontend Feature | Backend Change Needed |
|------------------|-----------------------|
| Date range on dashboard | Add `start_date` / `end_date` params to dashboard aggregation |
| Activity timeline | New endpoint: `GET /api/activity/timeline?date=2026-02-21` returning hourly buckets |
| Budget configuration | Already exists: `POST /api/domains/budgets/*` — just needs UI |
| Domain management | Already exists: `GET/POST /api/domains/*` — just needs UI |
| Email config | New endpoint: `POST /admin/api/v1/settings/email` proxying to deployment config |
| Password change | New endpoint: `POST /admin/api/v1/settings/password` |
| Full saved links | Already exists: `GET /api/saved_links` — needs pagination params and dedicated frontend query |
| Enforcement mode | Already exists: `POST /api/enforcement_mode` — just needs UI |
| Weekly trends | New endpoint: `GET /api/analytics/trend?days=7` returning daily focus scores |

---

## 5. Implementation Priority

| Phase | Impact | Effort | Priority |
|-------|--------|--------|----------|
| A: Dashboard Redesign | Very High | 3-5 days | **P0 — Do First** |
| B: Settings & Configuration | Very High | 3-5 days | **P0 — Do First** |
| C: Navigation & IA | Medium | 2-3 days | **P1 — Do Next** |
| D: Exception/Override Polish | Medium | 2 days | **P1 — Do Next** |
| E: Visual Design & Polish | Medium | 2-3 days | **P2 — When Possible** |

**Total estimated effort**: 12-18 days

---

## 6. Key Design Principles

1. **Answer the parent's question first**: "How is my child doing?" before showing raw data
2. **Actions over information**: Every data point should suggest an action
3. **Human language over technical terms**: "15 minutes" not "900 seconds"
4. **Progressive disclosure**: Show summary first, details on demand
5. **Mobile-first**: Parents check from their phone at the dinner table
6. **Consistent with the blocked page**: The child sees a polished blocked page; the parent should see a polished admin console
7. **No dead ends**: Every page should offer something to do, not just something to read

---

## 7. Auth Bug Found During Review

In `admin_ui/src/auth/AuthProvider.tsx`, the `login` function has a bug:

```typescript
async function login(username: string, password: string): Promise<void> {
    await authApi.login(username, password);
    const me = await authApi.me();
    setUser(user);  // BUG: should be setUser(me)
    setStatus("authenticated");
}
```

`setUser(user)` references the current state variable (null on first login) instead of `setUser(me)` which is the freshly fetched user object. This means after login, `user` stays null until the next page refresh triggers `bootstrapSession()`. This should be fixed immediately.
