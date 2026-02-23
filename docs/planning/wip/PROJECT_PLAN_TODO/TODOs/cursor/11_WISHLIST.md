# FocusGuard — Improvement Wishlist

**Created**: February 22, 2026  
**Purpose**: Running list of improvements, enhancements, and ideas to tackle when time permits. These are not blocking MVP but would significantly improve the product.

---

## Email Report Enhancements

| # | Improvement | Priority | Effort | Notes |
|---|------------|----------|--------|-------|
| W-01 | **Include link to admin console** in email body — `http://127.0.0.1:58393/admin` (or LAN IP if configured) | HIGH | 30min | Simple HTML link in email template |
| W-02 | **Include application info & privacy policy** — brief "About FocusGuard" section with link to privacy policy | MEDIUM | 1h | Add footer section to email template |
| W-03 | **Include FocusGuard icon/branding** — embed app icon in email header for brand recognition | MEDIUM | 1h | Base64 inline image or hosted URL |
| W-04 | **Add health check link** — include `http://127.0.0.1:58393/admin/status` link with note: "If no activity is reported and you suspect that shouldn't be the case, click here to check if FocusGuard is running properly" | HIGH | 30min | Conditional: only show when activity is zero |
| W-05 | **Support multiple email recipients** — allow comma-separated or list of recipient emails in config | HIGH | 2-3h | Update `deployment_config.json` schema, email reporter, first-run wizard, and settings UI |
| W-06 | **Richer email content** — top apps used, top domains visited, focus score trend, blocked site attempts, override usage summary | MEDIUM | 3-4h | Data already available from analytics service |

---

## App Health & Monitoring

| # | Improvement | Priority | Effort | Notes |
|---|------------|----------|--------|-------|
| W-10 | **App health monitoring module** — track component health (tab server, admin gateway, email reporter, activity logger, security monitors) with structured status | HIGH | 2-3 days | Local health dashboard + optional remote reporting |
| W-11 | **Remote health beacon** — opt-in anonymous health telemetry sent to a central endpoint for multi-user deployments. Includes: uptime, component status, error counts, version info | MEDIUM | 3-5 days | Requires server-side endpoint (could be simple cloud function) |
| W-12 | **Bug reporting from app** — "Report a Problem" button in tray menu and admin console that collects logs, config (sanitized), and system info into a ZIP for easy submission | HIGH | 1-2 days | Privacy-conscious: no browsing data, only app health data |
| W-13 | **Alert system for app provider** — when critical components fail (tab server down, extension disconnected, email send failure), send alert to configured provider email | MEDIUM | 1-2 days | Separate from user email reports |
| W-14 | **Health status page** — dedicated `/admin/status` page showing real-time component health with green/yellow/red indicators | MEDIUM | 1 day | Builds on existing `/admin/api/v1/meta` endpoint |

---

## Architecture: Multi-User & Multi-Device

| # | Improvement | Priority | Effort | Notes |
|---|------------|----------|--------|-------|
| W-20 | **Multi-user on same device** — support different Windows user accounts with separate config files, separate usage.db, separate budgets/rules. Each user gets their own FocusGuard profile. | HIGH | 1-2 weeks | Key decisions: per-user config in `%LOCALAPPDATA%\FocusGuard\<username>\`, shared service vs per-user process, admin vs child user roles |
| W-21 | **Same user across devices** — sync config (rules, budgets, domain lists) across multiple devices for the same user. Activity data stays local but config is shared. | MEDIUM | 2-3 weeks | Options: (a) cloud sync service, (b) shared network folder, (c) export/import config files. Start with (c) as MVP. |
| W-22 | **Config export/import** — export all config (deployment_config.json, domain_config.json, budgets) as a single portable file. Import on another device to replicate setup. | HIGH | 1-2 days | Stepping stone to W-21. Simple JSON bundle with version metadata. |
| W-23 | **Central management server** — for families/schools with multiple devices: web portal to manage all devices, push config changes, view aggregated reports | LOW | 4-8 weeks | Major architecture change. Consider as v2.0 feature. |

### Architecture Considerations for New Code

When writing new features, keep these principles in mind to make multi-user/multi-device easier later:

1. **Config paths should be parameterized** — never hardcode `C:\ProgramData\FocusGuard\`. Use a config resolver that can return per-user paths.
2. **Database paths should be per-profile** — usage.db, audit.db, etc. should be under a profile directory, not a global one.
3. **User identity should be explicit** — don't assume single user. Pass user/profile ID through the stack where relevant.
4. **Config should be serializable** — all runtime config should be exportable to JSON and importable from JSON.
5. **Health data should be structured** — use a standard schema for health events so they can be aggregated across devices later.

---

## Admin Console UX

| # | Improvement | Priority | Effort | Notes |
|---|------------|----------|--------|-------|
| W-30 | **Dark mode** — theme toggle in settings, respect system preference | LOW | 1-2 days | Use Tailwind dark: variants |
| W-31 | **Mobile optimization** — bottom nav needs all items, touch-friendly targets, swipe gestures | MEDIUM | 2-3 days | Parents check from phone at dinner |
| W-32 | **Design system consistency** — define color palette, consistent card styles, icon set (Lucide/Heroicons) | LOW | 1-2 days | |
| W-33 | **Loading skeletons** — replace "Loading..." text with skeleton UI | LOW | 1 day | |
| W-34 | **Blocked page ↔ admin console design alignment** — same gradient colors, icon style, typography | LOW | 1 day | |
| W-35 | **WebSocket real-time updates** — replace polling with push updates for instant feedback | MEDIUM | 3-4 days | |
| W-36 | **Weekly trend charts** — focus score over 7 days, budget usage trend | MEDIUM | 2-3 days | Data available from analytics service |

---

## Classification & Blocking

| # | Improvement | Priority | Effort | Notes |
|---|------------|----------|--------|-------|
| W-40 | **Classification feedback loop** — "This is actually educational" button on blocked page, admin override for URL classification | HIGH | 3-5 days | Store feedback, use for rule tuning |
| W-41 | **Classification caching** — server-side cache (24h rule-based, 1h LLM) to reduce redundant classification | MEDIUM | 1-2 days | |
| W-42 | **Extension event-driven updates** — replace 5s polling with tab event listeners, 30s heartbeat | MEDIUM | 1 day | 90% traffic reduction |
| W-43 | **News & streaming classifiers** — CNN, BBC, Netflix, Twitch | LOW | 3-5 days | |

---

## Infrastructure & DevOps

| # | Improvement | Priority | Effort | Notes |
|---|------------|----------|--------|-------|
| W-50 | **Inno Setup installer** — proper Windows installer with Start Menu, uninstaller, admin elevation | HIGH | 1-2 days | |
| W-51 | **Auto-update mechanism** — check version endpoint on startup, download in background, apply on restart | HIGH | 1-2 weeks | |
| W-52 | **Reduce exe size** (442 MB → ~150 MB) — UPX compression, exclude unused packages, strip debug symbols | MEDIUM | 1-2 days | |
| W-53 | **CI/CD pipeline** — GitHub Actions for test + build + release | MEDIUM | 1-2 days | |
| W-54 | **Database migration system** — version table, migration scripts, rollback | MEDIUM | 2-3 days | |
| W-55 | **Structured logging** — structlog or python-json-logger for consistent, parseable logs | LOW | 2-3 days | |
| W-56 | **Test suite consolidation** — single command to run all tests, convert standalone scripts to pytest | MEDIUM | 1-2 days | |

---

## Blocked Page & Extension

| # | Improvement | Priority | Effort | Notes |
|---|------------|----------|--------|-------|
| W-60 | **Budget context on blocked page** — show limit/used/remaining for current domain/category | HIGH | 2-4h | BUG-018 |
| W-61 | **Saved links in extension popup** — view saved links directly from extension | MEDIUM | 1-2 days | |
| W-62 | **Focus sessions / Pomodoro mode** — timed focus sessions with break reminders | LOW | 3-4 days | |
| W-63 | **Gamification & rewards** — streaks, achievements, focus score leaderboard | LOW | 2-3 weeks | |

---

## Domain page management
We should have a feature that can allow certain domains during certain times of the day/ so something along the lines of a popup next to the domain tha allows the admin to configure the schedule when it will be allowed. This could have a hierarchical config approach where certain times are focused times that dont allow any distractions and otehrs can allow some distraction limited by the budget. So for example class times no distractions, only educational content etc.

## School/Work Calendar Integration
We should have a feature that can allow the app to interface with the calendar so that it knows what times are blocked for what and then we can make the model better and more intelligent about allowing things during certain periods and blocking them otherwise.

## Timezone handling. Store activities in UTC time stamp while display results on front end using local timezone. 
Currently it seems we are doing the opposite

## Current CATEGORY LIST TIME LIMITS ON Settings PAGE are not clear. For e.g. education shows up twice, similarly entertainment shows up twice. What does that mean and why are they separately shown.

## On the settings page include a link to some sort of a user guide that explains the actions. I also noticed certain domains cant be allowed/blocked. For eg outlook.com, is it because they are whitelisted.

## How to Use This List



- Items are roughly ordered by priority within each section
- **HIGH** = would noticeably improve user experience or developer productivity
- **MEDIUM** = nice to have, improves polish or maintainability
- **LOW** = future vision, tackle when core is stable
- Move items to the active session plan when ready to work on them
- Mark completed items with ✅ and date
