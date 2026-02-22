import { useQuery } from "@tanstack/react-query";

import { ApiClientError, dashboardApi, metaApi } from "../api";
import { useOnlineStatus } from "../hooks/useOnlineStatus";
import { EmptyState, ErrorState, LoadingState, OfflineState } from "../ui/QueryStates";

function formatRelativeSeconds(value: number | null): string {
  if (value === null || value < 0) {
    return "--";
  }
  const mins = Math.floor(value / 60);
  const secs = value % 60;
  return `${mins}m ${secs}s`;
}

function formatLastSeen(value: string | null): string {
  if (!value) {
    return "Unknown";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function getRefetchIntervalMs(defaultMs: number, key: string): number {
  const globalAny = globalThis as Record<string, unknown>;
  const value = globalAny[key];
  if (typeof value === "number" && Number.isFinite(value) && value >= 500) {
    return value;
  }
  return defaultMs;
}

export function Dashboard() {
  const online = useOnlineStatus();
  const dashboardRefetchMs = getRefetchIntervalMs(20000, "__FG_TEST_DASHBOARD_REFETCH_MS__");
  const metaRefetchMs = getRefetchIntervalMs(30000, "__FG_TEST_META_REFETCH_MS__");
  const metaQuery = useQuery({
    queryKey: ["gateway-meta"],
    queryFn: () => metaApi.getMeta(),
    refetchInterval: online ? metaRefetchMs : false,
  });

  const dashboardQuery = useQuery({
    queryKey: ["dashboard", "default-device"],
    queryFn: () => dashboardApi.getDashboard("default-device"),
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
  const savedLinks = dashboard.saved_links ?? {
    total: 0,
    unviewed: 0,
    top_domains: [],
    recent: [],
  };
  const activitySummary = dashboard.activity_summary ?? {
    total_events: 0,
    blocked_count: 0,
    distracting_count: 0,
    blocked_percentage: 0,
    distracting_percentage: 0,
  };
  const openTabs = dashboard.open_tabs ?? [];
  const recentBlockedTabs = dashboard.recent_blocked_tabs ?? [];

  if (metaQuery.data && !metaQuery.data.capabilities.dashboard) {
    return <EmptyState message="Dashboard capability is unavailable in this runtime profile." />;
  }

  return (
    <div className="space-y-4">
      {!online ? <OfflineState message="You appear offline. Dashboard data will refresh automatically when connection returns." /> : null}
      {metaQuery.data?.readiness.tab_server === "offline" ? (
        <OfflineState message="Gateway is online but tab server is offline. Data may be stale or degraded until runtime reconnects." />
      ) : null}
      {dashboardQuery.isError && dashboardQuery.data ? (
        <OfflineState message="Showing last known dashboard snapshot while runtime recovers." />
      ) : null}
      <h2 className="font-display text-2xl text-ink">Dashboard</h2>
      <p className="text-sm text-gray-600">Live summary with focus status, budget pressure, friction signals, and active override activity.</p>

      {metaQuery.data ? (
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-slate-300 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-700">
            Gateway: {metaQuery.data.readiness.gateway}
          </span>
          <span className="rounded-full border border-slate-300 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-700">
            Tab server: {metaQuery.data.readiness.tab_server}
          </span>
          <span className="rounded-full border border-slate-300 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-700">
            Enforcement: {metaQuery.data.readiness.enforcement}
          </span>
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-slate-300 p-4">
          <p className="text-xs uppercase tracking-wide text-gray-500">Device Status</p>
          <p className="mt-2 text-xl font-semibold text-ink">{dashboard.device.status}</p>
          <p className="mt-1 text-xs text-gray-500">{dashboard.device.name} • {dashboard.device.enforcement_mode}</p>
          <p className="mt-1 text-xs text-gray-500">Seen: {formatLastSeen(dashboard.device.last_seen)}</p>
        </div>
        <div className="rounded-xl border border-slate-300 p-4">
          <p className="text-xs uppercase tracking-wide text-gray-500">Focus Score</p>
          <p className="mt-2 text-xl font-semibold text-ink">{dashboard.focus_score}</p>
          <p className="mt-1 text-xs text-gray-500">Blocks today: {dashboard.blocks_today}</p>
        </div>
        <div className="rounded-xl border border-slate-300 p-4">
          <p className="text-xs uppercase tracking-wide text-gray-500">Budget Used</p>
          <p className="mt-2 text-xl font-semibold text-ink">{Math.round(dashboard.budget.percent)}%</p>
          <div className="mt-3 h-2 w-full rounded-full bg-slate-200">
            <div
              className="h-2 rounded-full bg-ocean"
              style={{ width: `${Math.min(100, Math.max(0, Math.round(dashboard.budget.percent)))}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-gray-500">
            {Math.round(dashboard.budget.used_seconds / 60)}m / {Math.round(dashboard.budget.total_seconds / 60)}m
          </p>
        </div>
        <div className="rounded-xl border border-slate-300 p-4">
          <p className="text-xs uppercase tracking-wide text-gray-500">Overrides</p>
          <p className="mt-2 text-xl font-semibold text-ink">{dashboard.overrides_today}</p>
          <p className="mt-1 text-xs text-gray-500">Recent items: {dashboard.recent_overrides.length}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Activity Pulse</h3>
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            <div className="rounded-lg bg-slate-50 px-3 py-2">
              <p className="text-[11px] uppercase tracking-wide text-gray-500">Events</p>
              <p className="mt-1 text-sm font-semibold text-ink">{activitySummary.total_events}</p>
            </div>
            <div className="rounded-lg bg-red-50 px-3 py-2">
              <p className="text-[11px] uppercase tracking-wide text-gray-500">Blocked</p>
              <p className="mt-1 text-sm font-semibold text-ink">
                {activitySummary.blocked_count} ({Math.round(activitySummary.blocked_percentage)}%)
              </p>
            </div>
            <div className="rounded-lg bg-amber-50 px-3 py-2">
              <p className="text-[11px] uppercase tracking-wide text-gray-500">Distracting</p>
              <p className="mt-1 text-sm font-semibold text-ink">
                {activitySummary.distracting_count} ({Math.round(activitySummary.distracting_percentage)}%)
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Open Tabs</h3>
          {openTabs.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">No active tab snapshot available.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {openTabs.slice(0, 8).map((tab) => (
                <li key={`${tab.browser}-${tab.id}-${tab.url}`} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="truncate text-sm font-semibold text-ink">{tab.title || tab.url || "Untitled tab"}</p>
                  <p className="truncate text-xs text-gray-500">{tab.browser || "unknown"} • {tab.url}</p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Recent Blocked Tabs</h3>
          {recentBlockedTabs.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">No recent blocked-tab events.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {recentBlockedTabs.slice(0, 8).map((item, idx) => (
                <li key={`${item.timestamp ?? "na"}-${item.url}-${idx}`} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="truncate text-sm font-semibold text-ink">{item.domain || item.title || item.url}</p>
                  <p className="truncate text-xs text-gray-500">{item.browser || "unknown"} • {item.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Blocked Sites Today</h3>
          <p className="mt-1 text-xs text-gray-500">Total blocks: {dashboard.total_blocks}</p>
          {(!dashboard.blocked_sites || dashboard.blocked_sites.length === 0) ? (
            <p className="mt-3 text-sm text-gray-500">No sites blocked yet today.</p>
          ) : (
            <ul className="mt-3 space-y-2">
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
        </section>

        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Saved Links</h3>
          <p className="mt-1 text-xs text-gray-500">
            {savedLinks.unviewed} unviewed • {savedLinks.total} total
          </p>
          {savedLinks.recent.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">No saved links yet. Use “Save for Later” on blocked pages.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {savedLinks.recent.slice(0, 5).map((item) => (
                <li key={item.id} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="truncate text-sm font-semibold text-ink">{item.domain || item.title || "Saved link"}</p>
                  <p className="truncate text-xs text-gray-500">{item.comment || item.url}</p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Top Friction Domains</h3>
          {dashboard.top_friction.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">No friction signals yet.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {dashboard.top_friction.slice(0, 5).map((item) => (
                <li key={item.domain} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                  <div>
                    <p className="text-sm font-semibold text-ink">{item.domain}</p>
                    <p className="text-xs text-gray-500">{item.override_count} overrides</p>
                  </div>
                  <p className="text-xs font-semibold text-gray-700">{Math.round(item.time_used_seconds / 60)}m used</p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Recent Overrides</h3>
          {dashboard.recent_overrides.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">No recent overrides.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {dashboard.recent_overrides.slice(0, 5).map((item) => (
                <li key={item.id} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-sm font-semibold text-ink">{item.domain}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    {item.status} • remaining {formatRelativeSeconds(item.remaining_seconds)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="rounded-xl border border-slate-300 p-4">
        <h3 className="font-display text-lg text-ink">Attention Items</h3>
        {dashboard.attention_items.length === 0 ? (
          <p className="mt-3 text-sm text-gray-500">No attention items right now.</p>
        ) : (
          <div className="mt-3 flex flex-wrap gap-2">
            {dashboard.attention_items.map((item) => (
              <span key={`${item.type}-${item.domain ?? "none"}`} className="rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                {item.type}: {item.domain ?? "n/a"} ({item.count})
              </span>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
