import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ApiClientError, dashboardApi, metaApi } from "../api";
import type { DashboardResponse, DashboardAttentionItem } from "../api/dashboard";
import { useOnlineStatus } from "../hooks/useOnlineStatus";
import { EmptyState, ErrorState, LoadingState, OfflineState } from "../ui/QueryStates";

// ── Helpers ────────────────────────────────────────────────────────

function formatMinutes(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0 min";
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return rm > 0 ? `${h}h ${rm}m` : `${h}h`;
}

function formatRelativeSeconds(value: number | null): string {
  if (value === null || value < 0) return "--";
  const mins = Math.floor(value / 60);
  const secs = Math.floor(value % 60);
  if (mins >= 60) {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    if (m === 0) return h === 1 ? "1 hour left" : `${h} hours left`;
    return `${h}h ${m} min left`;
  }
  if (secs === 0) return mins === 1 ? "1 minute left" : `${mins} minutes left`;
  return `${mins} min ${secs} sec left`;
}

/** Human-readable duration for display (e.g. "5 minutes", "1 hour 15 minutes"). */
function formatDurationHuman(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0 minutes";
  const totalMins = Math.round(seconds / 60);
  if (totalMins < 60) return totalMins === 1 ? "1 minute" : `${totalMins} minutes`;
  const h = Math.floor(totalMins / 60);
  const m = totalMins % 60;
  if (m === 0) return h === 1 ? "1 hour" : `${h} hours`;
  return `${h} hour${h > 1 ? "s" : ""} ${m} minute${m > 1 ? "s" : ""}`;
}

/** Domains to hide from Problem Sites / Recent Overrides (synthetic, internal, test). */
const SYNTHETIC_DOMAIN_PATTERNS = [
  "localhost",
  "127.0.0.1",
  "internal",
  "smoke",
  "example.com",
  "test.",
  ".local",
];

function isSyntheticDomain(domain: string | null | undefined): boolean {
  if (!domain || typeof domain !== "string") return true;
  const d = domain.toLowerCase();
  return SYNTHETIC_DOMAIN_PATTERNS.some((p) => d.includes(p));
}

function getRefetchIntervalMs(defaultMs: number, key: string): number {
  const globalAny = globalThis as Record<string, unknown>;
  const value = globalAny[key];
  if (typeof value === "number" && Number.isFinite(value) && value >= 500) return value;
  return defaultMs;
}

function scoreColor(score: number): string {
  if (score >= 70) return "text-emerald-600";
  if (score >= 40) return "text-amber-600";
  return "text-red-600";
}

function scoreRingColor(score: number): string {
  if (score >= 70) return "#059669";
  if (score >= 40) return "#d97706";
  return "#dc2626";
}

function budgetBarColor(pct: number): string {
  if (pct > 80) return "bg-red-500";
  if (pct > 50) return "bg-amber-500";
  return "bg-emerald-500";
}

function scoreVerdict(score: number): string {
  if (score >= 80) return "Excellent focus today!";
  if (score >= 60) return "Good focus day.";
  if (score >= 40) return "Mixed focus — some distractions.";
  return "Lots of distractions today.";
}

function buildNaturalSummary(d: DashboardResponse): string {
  const usedMin = Math.round(d.budget.used_seconds / 60);
  const totalMin = Math.round(d.budget.total_seconds / 60);
  const blocks = d.blocks_today;
  const overrides = d.overrides_today;

  let summary = `${usedMin} min of screen time used out of ${totalMin} min allowed.`;
  if (blocks > 0) summary += ` ${blocks} site${blocks > 1 ? "s" : ""} blocked.`;
  if (overrides > 0) summary += ` ${overrides} override${overrides > 1 ? "s" : ""} used.`;
  return summary;
}

function alertMessage(item: DashboardAttentionItem): string {
  const domain = item.domain ?? "a site";
  switch (item.type) {
    case "frequent_override":
      return `${domain} was overridden ${item.count} time${item.count > 1 ? "s" : ""} today`;
    case "budget_warning":
      return `Screen time budget is running low`;
    case "budget_exceeded":
      return `Screen time budget exceeded`;
    case "high_block_count":
      return `${domain} was blocked ${item.count} time${item.count > 1 ? "s" : ""}`;
    default:
      return `${item.type}: ${domain} (${item.count})`;
  }
}

function alertIcon(type: string): string {
  switch (type) {
    case "frequent_override": return "🔄";
    case "budget_warning": return "⏳";
    case "budget_exceeded": return "🚫";
    case "high_block_count": return "🛑";
    default: return "⚠️";
  }
}

// ── Focus Score Ring (SVG) ─────────────────────────────────────────

function FocusScoreRing({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(100, score));
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const color = scoreRingColor(clamped);

  return (
    <div className="relative flex items-center justify-center" style={{ width: 140, height: 140 }}>
      <svg width="140" height="140" viewBox="0 0 140 140" className="-rotate-90">
        <circle cx="70" cy="70" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="10" />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`text-3xl font-bold ${scoreColor(clamped)}`}>{clamped}</span>
        <span className="text-[10px] font-medium uppercase tracking-wider text-gray-400">Focus</span>
      </div>
    </div>
  );
}

// ── Collapsible Section ────────────────────────────────────────────

function CollapsibleSection({
  title,
  badge,
  defaultOpen = false,
  children,
}: {
  title: string;
  badge?: string | number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="rounded-xl border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <h3 className="font-display text-base text-ink">{title}</h3>
          {badge != null && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-gray-500">
              {badge}
            </span>
          )}
        </div>
        <svg
          className={`h-4 w-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="border-t border-slate-100 px-4 py-3">{children}</div>}
    </section>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────

function toYYYYMMDD(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function getDateRangeForPreset(preset: "today" | "yesterday" | "last7"): { startDate: string; endDate: string } {
  const now = new Date();
  const today = toYYYYMMDD(now);
  if (preset === "today") return { startDate: today, endDate: today };
  if (preset === "yesterday") {
    const y = new Date(now);
    y.setDate(y.getDate() - 1);
    const yesterday = toYYYYMMDD(y);
    return { startDate: yesterday, endDate: yesterday };
  }
  const start = new Date(now);
  start.setDate(start.getDate() - 6);
  return { startDate: toYYYYMMDD(start), endDate: today };
}

function formatDateRangeLabel(startDate: string, endDate: string): string {
  if (startDate === endDate) {
    const d = new Date(startDate + "T12:00:00");
    return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" });
  }
  const s = new Date(startDate + "T12:00:00");
  const e = new Date(endDate + "T12:00:00");
  return `${s.toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${e.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`;
}

export function Dashboard() {
  const online = useOnlineStatus();
  const [datePreset, setDatePreset] = useState<"today" | "yesterday" | "last7">("today");
  const dateRange = getDateRangeForPreset(datePreset);
  const dashboardRefetchMs = getRefetchIntervalMs(20000, "__FG_TEST_DASHBOARD_REFETCH_MS__");
  const metaRefetchMs = getRefetchIntervalMs(30000, "__FG_TEST_META_REFETCH_MS__");

  const metaQuery = useQuery({
    queryKey: ["gateway-meta"],
    queryFn: () => metaApi.getMeta(),
    refetchInterval: online ? metaRefetchMs : false,
  });

  const dashboardQuery = useQuery({
    queryKey: ["dashboard", "default-device", dateRange.startDate, dateRange.endDate],
    queryFn: () =>
      dashboardApi.getDashboard({
        deviceId: "default-device",
        startDate: dateRange.startDate,
        endDate: dateRange.endDate,
      }),
    refetchInterval: online ? dashboardRefetchMs : false,
    retry: 2,
    retryDelay: (attempt) => Math.min(3000, 500 * 2 ** attempt),
  });

  if (dashboardQuery.isLoading) {
    return <LoadingState label="dashboard" />;
  }

  if (dashboardQuery.isError && !dashboardQuery.data) {
    const message =
      dashboardQuery.error instanceof ApiClientError
        ? `${dashboardQuery.error.code}: ${dashboardQuery.error.message}${
            dashboardQuery.error.requestId ? ` (request ${dashboardQuery.error.requestId})` : ""
          }`
        : "Unable to load dashboard";
    return <ErrorState message={message} />;
  }

  const dashboard = dashboardQuery.data;
  if (!dashboard) {
    return <EmptyState message="No dashboard data available yet." />;
  }

  if (metaQuery.data && !metaQuery.data.capabilities.dashboard) {
    return <EmptyState message="Dashboard capability is unavailable in this runtime profile." />;
  }

  const budgetPct = Math.min(100, Math.max(0, Math.round(dashboard.budget.percent)));
  const savedLinks = dashboard.saved_links ?? { total: 0, unviewed: 0, top_domains: [], recent: [] };
  const activitySummary = dashboard.activity_summary ?? {
    total_events: 0, blocked_count: 0, distracting_count: 0,
    blocked_percentage: 0, distracting_percentage: 0,
  };
  const openTabs = dashboard.open_tabs ?? [];
  const recentBlockedTabs = dashboard.recent_blocked_tabs ?? [];
  const modeLabel =
    dashboard.device.enforcement_mode === "enforcing" ? "Block" :
    dashboard.device.enforcement_mode === "advisory" ? "Warn" : "Monitor Only";

  return (
    <div className="space-y-5">
      {/* ── Status banners ──────────────────────────────────────── */}
      {!online && <OfflineState message="You appear offline. Data will refresh when connection returns." />}
      {metaQuery.data?.readiness.tab_server === "offline" && (
        <OfflineState message="Tab server is offline. Data may be stale." />
      )}
      {dashboardQuery.isError && dashboardQuery.data && (
        <OfflineState message="Showing last known snapshot while runtime recovers." />
      )}

      {/* ── Date range selector (Phase A5) ────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm text-gray-500">
          Showing: <strong className="text-gray-700">{formatDateRangeLabel(dateRange.startDate, dateRange.endDate)}</strong>
        </span>
        <div className="flex gap-1">
          {(["today", "yesterday", "last7"] as const).map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => setDatePreset(preset)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                datePreset === preset
                  ? "bg-ocean text-white"
                  : "bg-slate-100 text-gray-600 hover:bg-slate-200"
              }`}
            >
              {preset === "last7" ? "Last 7 days" : preset === "today" ? "Today" : "Yesterday"}
            </button>
          ))}
        </div>
      </div>

      {/* ── Hero Section ────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl text-ink">
            {datePreset === "today" ? "Today's Focus" : datePreset === "yesterday" ? "Yesterday's Focus" : "Focus Summary"}
          </h2>
          <div className="flex items-center gap-2">
            <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
              modeLabel === "Block" ? "bg-red-100 text-red-700" :
              modeLabel === "Warn" ? "bg-amber-100 text-amber-700" :
              "bg-emerald-100 text-emerald-700"
            }`}>
              {modeLabel}
            </span>
            <span className="text-xs text-gray-400">
              {new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
            </span>
          </div>
        </div>

        <div className="mt-4 flex flex-col items-center gap-5 sm:flex-row sm:items-start">
          {/* Score ring */}
          <FocusScoreRing score={dashboard.focus_score} />

          {/* Summary + budget */}
          <div className="flex-1 space-y-3">
            <div>
              <p className={`text-lg font-semibold ${scoreColor(dashboard.focus_score)}`}>
                {scoreVerdict(dashboard.focus_score)}
              </p>
              <p className="mt-1 text-sm text-gray-600">{buildNaturalSummary(dashboard)}</p>
            </div>

            {/* Budget bar */}
            <div>
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>Screen Time Budget</span>
                <span className="font-semibold">
                  {formatMinutes(dashboard.budget.used_seconds)} / {formatMinutes(dashboard.budget.total_seconds)}
                </span>
              </div>
              <div className="mt-1.5 h-3 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${budgetBarColor(budgetPct)}`}
                  style={{ width: `${budgetPct}%` }}
                />
              </div>
              <p className="mt-1 text-right text-[10px] text-gray-400">{budgetPct}% used</p>
            </div>

            {/* Quick stats row */}
            <div className="flex flex-wrap gap-3">
              <div className="rounded-lg bg-red-50 px-3 py-1.5">
                <span className="text-[10px] uppercase tracking-wide text-gray-500">Blocked</span>
                <p className="text-sm font-bold text-red-700">{dashboard.blocks_today}</p>
              </div>
              <div className="rounded-lg bg-blue-50 px-3 py-1.5">
                <span className="text-[10px] uppercase tracking-wide text-gray-500">Overrides</span>
                <p className="text-sm font-bold text-blue-700">{dashboard.overrides_today}</p>
              </div>
              <div className="rounded-lg bg-slate-50 px-3 py-1.5">
                <span className="text-[10px] uppercase tracking-wide text-gray-500">Events</span>
                <p className="text-sm font-bold text-gray-700">{activitySummary.total_events}</p>
              </div>
              {savedLinks.unviewed > 0 && (
                <Link to="/saved-links" className="rounded-lg bg-purple-50 px-3 py-1.5 transition hover:bg-purple-100">
                  <span className="text-[10px] uppercase tracking-wide text-gray-500">Saved Links</span>
                  <p className="text-sm font-bold text-purple-700">{savedLinks.unviewed} new</p>
                </Link>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── Alerts & Actions Bar ────────────────────────────────── */}
      {dashboard.attention_items.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Alerts</h3>
          {dashboard.attention_items.map((item) => (
            <div
              key={`${item.type}-${item.domain ?? "none"}`}
              className="flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-2.5"
            >
              <div className="flex items-center gap-2.5">
                <span className="text-lg">{alertIcon(item.type)}</span>
                <p className="text-sm text-gray-800">{alertMessage(item)}</p>
              </div>
              <div className="flex gap-1.5">
                {item.domain && (
                  <Link
                    to="/overrides"
                    className="rounded-md bg-ocean px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-ocean/90"
                  >
                    Manage
                  </Link>
                )}
                <Link
                  to="/settings"
                  className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-gray-600 hover:bg-slate-50"
                >
                  Settings
                </Link>
              </div>
            </div>
          ))}
        </section>
      )}

      {/* ── Activity Pulse ──────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
          <p className="text-[10px] uppercase tracking-wide text-gray-400">Activity Events</p>
          <p className="mt-1 text-xl font-bold text-ink">{activitySummary.total_events}</p>
        </div>
        <div className="rounded-xl border border-red-100 bg-red-50/50 px-4 py-3">
          <p className="text-[10px] uppercase tracking-wide text-gray-400">Blocked</p>
          <p className="mt-1 text-xl font-bold text-red-700">
            {activitySummary.blocked_count}
            <span className="ml-1 text-xs font-normal text-red-400">
              ({Math.round(activitySummary.blocked_percentage)}%)
            </span>
          </p>
        </div>
        <div className="rounded-xl border border-amber-100 bg-amber-50/50 px-4 py-3">
          <p className="text-[10px] uppercase tracking-wide text-gray-400">Distracting</p>
          <p className="mt-1 text-xl font-bold text-amber-700">
            {activitySummary.distracting_count}
            <span className="ml-1 text-xs font-normal text-amber-400">
              ({Math.round(activitySummary.distracting_percentage)}%)
            </span>
          </p>
        </div>
      </div>

      {/* ── Collapsible Detail Sections ─────────────────────────── */}
      <div className="space-y-3">
        {/* Blocked Sites */}
        <CollapsibleSection
          title="Blocked Sites Today"
          badge={dashboard.total_blocks > 0 ? dashboard.total_blocks : undefined}
          defaultOpen={dashboard.blocked_sites && dashboard.blocked_sites.length > 0}
        >
          {(!dashboard.blocked_sites || dashboard.blocked_sites.length === 0) ? (
            <p className="text-sm text-gray-500">No sites blocked yet today.</p>
          ) : (
            <ul className="space-y-2">
              {dashboard.blocked_sites.slice(0, 8).map((item) => (
                <li key={item.domain} className="flex items-center justify-between rounded-lg bg-red-50 px-3 py-2">
                  <div>
                    <p className="text-sm font-semibold text-ink">{item.domain}</p>
                    <p className="text-xs text-gray-500">{item.category ?? "Unknown"}</p>
                  </div>
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">
                    {item.count}x
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CollapsibleSection>

        {/* Problem Sites */}
        {(() => {
          const problemSites = dashboard.top_friction.filter((item) => !isSyntheticDomain(item?.domain));
          return (
            <CollapsibleSection
              title="Problem Sites"
              badge={problemSites.length > 0 ? problemSites.length : undefined}
              defaultOpen={problemSites.length > 0}
            >
              {problemSites.length === 0 ? (
                <p className="text-sm text-gray-500">No problem sites detected.</p>
              ) : (
                <ul className="space-y-2">
                  {problemSites.slice(0, 5).map((item) => (
                    <li key={item.domain} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                      <div>
                        <p className="text-sm font-semibold text-ink">{item.domain}</p>
                        <p className="text-xs text-gray-500">
                          {item.override_count} {item.override_count === 1 ? "override" : "overrides"} today
                        </p>
                      </div>
                      <p className="text-xs font-semibold text-gray-700">{formatDurationHuman(item.time_used_seconds)} screen time</p>
                    </li>
                  ))}
                </ul>
              )}
            </CollapsibleSection>
          );
        })()}

        {/* Open Tabs — only show if there are tabs */}
        {openTabs.length > 0 && (
          <CollapsibleSection title="Open Tabs" badge={openTabs.length}>
            <ul className="space-y-2">
              {openTabs.slice(0, 8).map((tab) => (
                <li key={`${tab.browser}-${tab.id}-${tab.url}`} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="truncate text-sm font-semibold text-ink">{tab.title || tab.url || "Untitled tab"}</p>
                  <p className="truncate text-xs text-gray-500">{tab.browser || "unknown"} • {tab.url}</p>
                </li>
              ))}
            </ul>
          </CollapsibleSection>
        )}

        {/* Recent Blocked Tabs */}
        {recentBlockedTabs.length > 0 && (
          <CollapsibleSection title="Recently Blocked Tabs" badge={recentBlockedTabs.length}>
            <ul className="space-y-2">
              {recentBlockedTabs.slice(0, 8).map((item, idx) => (
                <li key={`${item.timestamp ?? "na"}-${item.url}-${idx}`} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="truncate text-sm font-semibold text-ink">{item.domain || item.title || item.url}</p>
                  <p className="truncate text-xs text-gray-500">{item.browser || "unknown"} • {item.reason}</p>
                </li>
              ))}
            </ul>
          </CollapsibleSection>
        )}

        {/* Recent Overrides */}
        {(() => {
          const recentOverrides = dashboard.recent_overrides.filter((item) => !isSyntheticDomain(item?.domain));
          return (
            <CollapsibleSection
              title="Recent Overrides"
              badge={recentOverrides.length > 0 ? recentOverrides.length : undefined}
            >
              {recentOverrides.length === 0 ? (
                <p className="text-sm text-gray-500">No recent overrides.</p>
              ) : (
                <ul className="space-y-2">
                  {recentOverrides.slice(0, 5).map((item) => (
                    <li key={item.id} className="rounded-lg bg-slate-50 px-3 py-2">
                      <p className="text-sm font-semibold text-ink">{item.domain}</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {item.status === "Active" && item.remaining_seconds != null && item.remaining_seconds > 0
                          ? `Active • ${formatRelativeSeconds(item.remaining_seconds)}`
                          : "Expired"}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </CollapsibleSection>
          );
        })()}

        {/* Saved Links */}
        <CollapsibleSection
          title="Saved Links"
          badge={savedLinks.unviewed > 0 ? `${savedLinks.unviewed} new` : undefined}
        >
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">{savedLinks.total} total • {savedLinks.unviewed} unviewed</p>
            <Link to="/saved-links" className="text-xs font-semibold text-ocean hover:underline">View all</Link>
          </div>
          {savedLinks.recent.length === 0 ? (
            <p className="mt-2 text-sm text-gray-500">No saved links yet.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {savedLinks.recent.slice(0, 5).map((item) => (
                <li key={item.id} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="truncate text-sm font-semibold text-ink">{item.domain || item.title || "Saved link"}</p>
                  <p className="truncate text-xs text-gray-500">{item.comment || item.url}</p>
                </li>
              ))}
            </ul>
          )}
        </CollapsibleSection>
      </div>
    </div>
  );
}
