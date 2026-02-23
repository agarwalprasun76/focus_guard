import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { activityApi, ApiClientError } from "../api";
import type { AppUsageEntry, DailyBreakdownEntry } from "../api/activity";
import { useOnlineStatus } from "../hooks/useOnlineStatus";
import { EmptyState, ErrorState, LoadingState, OfflineState } from "../ui/QueryStates";

// ── Helpers ────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0 min";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return rm > 0 ? `${h}h ${rm}m` : `${h}h`;
}

function pctOfTotal(seconds: number, total: number): number {
  if (total <= 0) return 0;
  return Math.min(100, Math.round((seconds / total) * 100));
}

function appIcon(entry: AppUsageEntry): string {
  const name = entry.app_name.toLowerCase();
  if (entry.is_browser) return "🌐";
  if (name.includes("word") || name.includes("winword")) return "📝";
  if (name.includes("excel")) return "📊";
  if (name.includes("powerpoint") || name.includes("powerpnt")) return "📽️";
  if (name.includes("onenote")) return "📓";
  if (name.includes("outlook")) return "📧";
  if (name.includes("teams")) return "💬";
  if (name.includes("discord")) return "💬";
  if (name.includes("slack")) return "💬";
  if (name.includes("zoom")) return "📹";
  if (name.includes("code") || name.includes("devenv") || name.includes("idea")) return "💻";
  if (name.includes("terminal") || name.includes("cmd") || name.includes("powershell") || name.includes("windowsterminal")) return "⬛";
  if (name.includes("explorer")) return "📁";
  if (name.includes("notepad")) return "🗒️";
  if (name.includes("calculator") || name.includes("calc")) return "🔢";
  if (name.includes("spotify") || name.includes("music")) return "🎵";
  if (name.includes("vlc") || name.includes("media") || name.includes("video")) return "🎬";
  if (name.includes("game") || name.includes("steam") || name.includes("minecraft") || name.includes("roblox")) return "🎮";
  if (name.includes("paint") || name.includes("photoshop") || name.includes("gimp")) return "🎨";
  if (name.includes("pdf") || name.includes("acrobat")) return "📄";
  if (name.includes("settings") || name.includes("systemsettings")) return "⚙️";
  return "📦";
}

function categoryBadge(entry: AppUsageEntry): { label: string; className: string } | null {
  if (entry.category) {
    const cat = entry.category.toLowerCase();
    if (cat.includes("productive") || cat.includes("work") || cat.includes("education"))
      return { label: entry.category, className: "bg-emerald-100 text-emerald-700" };
    if (cat.includes("distract") || cat.includes("entertainment") || cat.includes("social"))
      return { label: entry.category, className: "bg-red-100 text-red-700" };
    if (cat.includes("communication") || cat.includes("utility"))
      return { label: entry.category, className: "bg-blue-100 text-blue-700" };
    return { label: entry.category, className: "bg-slate-100 text-slate-600" };
  }
  if (entry.is_browser) return { label: "Browser", className: "bg-blue-100 text-blue-700" };
  return null;
}

function barColor(entry: AppUsageEntry): string {
  if (entry.category) {
    const cat = entry.category.toLowerCase();
    if (cat.includes("distract") || cat.includes("entertainment") || cat.includes("social"))
      return "bg-red-400";
    if (cat.includes("productive") || cat.includes("work") || cat.includes("education"))
      return "bg-emerald-400";
  }
  if (entry.is_browser) return "bg-blue-400";
  return "bg-slate-400";
}

type ViewMode = "all" | "apps" | "browsers";

// ── Time range presets ─────────────────────────────────────────────

type RangePreset = {
  label: string;
  key: string;
  getDates: () => { startDate: string; endDate: string };
};

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function daysAgo(n: number): Date {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d;
}

const RANGE_PRESETS: RangePreset[] = [
  { label: "Today", key: "today", getDates: () => ({ startDate: isoDate(new Date()), endDate: isoDate(new Date()) }) },
  { label: "Yesterday", key: "yesterday", getDates: () => ({ startDate: isoDate(daysAgo(1)), endDate: isoDate(daysAgo(1)) }) },
  { label: "Last 3 days", key: "3d", getDates: () => ({ startDate: isoDate(daysAgo(2)), endDate: isoDate(new Date()) }) },
  { label: "Last 7 days", key: "7d", getDates: () => ({ startDate: isoDate(daysAgo(6)), endDate: isoDate(new Date()) }) },
  { label: "Last 30 days", key: "30d", getDates: () => ({ startDate: isoDate(daysAgo(29)), endDate: isoDate(new Date()) }) },
  { label: "Last 90 days", key: "90d", getDates: () => ({ startDate: isoDate(daysAgo(89)), endDate: isoDate(new Date()) }) },
];

// ── Main Component ─────────────────────────────────────────────────

export function AppActivity() {
  const online = useOnlineStatus();
  const today = isoDate(new Date());
  const [activePreset, setActivePreset] = useState("today");
  const [customStart, setCustomStart] = useState(today);
  const [customEnd, setCustomEnd] = useState(today);
  const [viewMode, setViewMode] = useState<ViewMode>("all");

  const { startDate, endDate } = useMemo(() => {
    if (activePreset === "custom") {
      return { startDate: customStart, endDate: customEnd };
    }
    const preset = RANGE_PRESETS.find((p) => p.key === activePreset);
    return preset ? preset.getDates() : { startDate: today, endDate: today };
  }, [activePreset, customStart, customEnd, today]);

  const isRange = startDate !== endDate;

  const query = useQuery({
    queryKey: ["activity-apps", startDate, endDate],
    queryFn: () =>
      isRange
        ? activityApi.getAppUsage({ startDate, endDate, limit: 50 })
        : activityApi.getAppUsage({ date: startDate, limit: 50 }),
    refetchInterval: online ? 30000 : false,
    retry: 2,
  });

  if (query.isLoading) return <LoadingState label="app activity" />;

  if (query.isError && !query.data) {
    const message =
      query.error instanceof ApiClientError
        ? `${query.error.code}: ${query.error.message}`
        : "Unable to load app activity";
    return <ErrorState message={message} />;
  }

  const data = query.data;
  if (!data) return <EmptyState message="No activity data available yet." />;

  const filteredApps = data.apps.filter((a) => {
    if (viewMode === "apps") return !a.is_browser;
    if (viewMode === "browsers") return a.is_browser;
    return true;
  });

  const browserTime = data.apps.filter((a) => a.is_browser).reduce((s, a) => s + a.active_seconds, 0);
  const appTime = data.apps.filter((a) => !a.is_browser).reduce((s, a) => s + a.active_seconds, 0);

  const rangeLabel = isRange ? `${startDate} to ${endDate}` : startDate;

  return (
    <div className="space-y-5">
      {!online && <OfflineState message="You appear offline. Data will refresh when connection returns." />}

      {/* Header */}
      <div>
        <h2 className="font-display text-2xl text-ink">App Activity</h2>
        <p className="text-sm text-gray-600">
          See how time is spent across all applications — not just the browser.
        </p>
      </div>

      {/* Time range presets */}
      <div className="space-y-2">
        <div className="flex flex-wrap gap-1.5">
          {RANGE_PRESETS.map((preset) => (
            <button
              key={preset.key}
              type="button"
              onClick={() => setActivePreset(preset.key)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                activePreset === preset.key
                  ? "bg-ocean text-white"
                  : "border border-slate-200 text-gray-600 hover:bg-slate-50"
              }`}
            >
              {preset.label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setActivePreset("custom")}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
              activePreset === "custom"
                ? "bg-ocean text-white"
                : "border border-slate-200 text-gray-600 hover:bg-slate-50"
            }`}
          >
            Custom Range
          </button>
        </div>
        {activePreset === "custom" && (
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-xs text-gray-500">From</label>
            <input
              type="date"
              value={customStart}
              max={today}
              onChange={(e) => setCustomStart(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
            />
            <label className="text-xs text-gray-500">To</label>
            <input
              type="date"
              value={customEnd}
              max={today}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
            />
          </div>
        )}
        <p className="text-xs text-gray-400">
          Showing: {rangeLabel}
          {isRange && data.daily_breakdown && data.daily_breakdown.length > 0 && (
            <span> ({data.daily_breakdown.length} days with activity)</span>
          )}
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
          <p className="text-[10px] uppercase tracking-wide text-gray-400">Total Screen Time</p>
          <p className="mt-1 text-xl font-bold text-ink">{formatDuration(data.total_active_seconds)}</p>
        </div>
        <div className="rounded-xl border border-blue-100 bg-blue-50/50 px-4 py-3">
          <p className="text-[10px] uppercase tracking-wide text-gray-400">Browser Time</p>
          <p className="mt-1 text-xl font-bold text-blue-700">
            {formatDuration(browserTime)}
            <span className="ml-1 text-xs font-normal text-blue-400">
              ({pctOfTotal(browserTime, data.total_active_seconds)}%)
            </span>
          </p>
        </div>
        <div className="rounded-xl border border-purple-100 bg-purple-50/50 px-4 py-3">
          <p className="text-[10px] uppercase tracking-wide text-gray-400">App Time</p>
          <p className="mt-1 text-xl font-bold text-purple-700">
            {formatDuration(appTime)}
            <span className="ml-1 text-xs font-normal text-purple-400">
              ({pctOfTotal(appTime, data.total_active_seconds)}%)
            </span>
          </p>
        </div>
      </div>

      {/* Day-of-week breakdown (for range queries) */}
      {isRange && data.daily_breakdown && data.daily_breakdown.length > 0 && (
        <DailyBreakdown entries={data.daily_breakdown} />
      )}

      {/* Filter tabs */}
      <div className="flex gap-1.5">
        {([
          { key: "all" as ViewMode, label: `All (${data.apps.length})` },
          { key: "apps" as ViewMode, label: `Apps (${data.apps.filter((a) => !a.is_browser).length})` },
          { key: "browsers" as ViewMode, label: `Browsers (${data.apps.filter((a) => a.is_browser).length})` },
        ]).map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setViewMode(tab.key)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
              viewMode === tab.key
                ? "bg-ocean text-white"
                : "border border-slate-200 text-gray-600 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Info message if no DB yet */}
      {data.message && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-gray-600">
          {data.message}
        </div>
      )}

      {/* App list */}
      {filteredApps.length === 0 ? (
        <EmptyState message={data.apps.length === 0 ? "No activity recorded yet for this period." : "No apps match this filter."} />
      ) : (
        <div className="space-y-2">
          {filteredApps.map((app) => (
            <AppRow key={app.app_name} entry={app} totalSeconds={data.total_active_seconds} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Daily Breakdown ─────────────────────────────────────────────────

function DailyBreakdown({ entries }: { entries: DailyBreakdownEntry[] }) {
  const maxSeconds = Math.max(...entries.map((e) => e.total_seconds), 1);

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-ink">Daily Breakdown</h3>
      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Day</th>
              <th className="px-3 py-2 text-right">Screen Time</th>
              <th className="px-3 py-2 text-right">Apps</th>
              <th className="px-3 py-2 w-40"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {entries.map((entry) => {
              const pct = Math.max(2, Math.round((entry.total_seconds / maxSeconds) * 100));
              return (
                <tr key={entry.date} className="hover:bg-slate-50/60">
                  <td className="whitespace-nowrap px-3 py-2 font-medium text-gray-800">{entry.date}</td>
                  <td className="px-3 py-2 text-gray-600">{entry.day_of_week}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right font-medium text-ink">
                    {formatDuration(entry.total_seconds)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-gray-500">{entry.app_count}</td>
                  <td className="px-3 py-2">
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-ocean/70 transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ── App Row ────────────────────────────────────────────────────────

function AppRow({ entry, totalSeconds }: { entry: AppUsageEntry; totalSeconds: number }) {
  const pct = pctOfTotal(entry.active_seconds, totalSeconds);
  const badge = categoryBadge(entry);

  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
      <div className="flex items-center gap-3">
        <span className="text-2xl">{appIcon(entry)}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-semibold text-ink">{entry.app_name}</p>
            {badge && (
              <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] font-semibold ${badge.className}`}>
                {badge.label}
              </span>
            )}
          </div>
          {entry.last_title && (
            <p className="truncate text-xs text-gray-500" title={entry.last_title}>
              {entry.last_title}
            </p>
          )}
        </div>
        <div className="text-right">
          <p className="text-sm font-bold text-ink">{formatDuration(entry.active_seconds)}</p>
          <p className="text-[10px] text-gray-400">{pct}%</p>
        </div>
      </div>
      {/* Usage bar */}
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor(entry)}`}
          style={{ width: `${Math.max(1, pct)}%` }}
        />
      </div>
      {/* Extra info row */}
      {(entry.last_domain || entry.productivity_score != null) && (
        <div className="mt-1.5 flex flex-wrap gap-3 text-[10px] text-gray-400">
          {entry.last_domain && <span>Domain: {entry.last_domain}</span>}
          {entry.productivity_score != null && (
            <span>Productivity: {Math.round(entry.productivity_score * 100)}%</span>
          )}
          <span>{entry.sample_count} samples</span>
        </div>
      )}
    </div>
  );
}
