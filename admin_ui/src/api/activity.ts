import { requestJson } from "./client";

// ── Types ─────────────────────────────────────────────────────────

export type AppUsageEntry = {
  app_name: string;
  active_seconds: number;
  sample_count: number;
  last_domain?: string | null;
  last_title?: string | null;
  is_browser: boolean;
  category?: string;
  subcategory?: string;
  productivity_score?: number | null;
};

export type DailyBreakdownEntry = {
  date: string;
  day_of_week: string;
  total_seconds: number;
  app_count: number;
  sample_count: number;
};

export type AppUsageResponse = {
  date: string;
  start_date?: string;
  end_date?: string;
  apps: AppUsageEntry[];
  total_active_seconds: number;
  total_sessions: number;
  daily_breakdown?: DailyBreakdownEntry[];
  message?: string;
};

// ── API functions ─────────────────────────────────────────────────

export function getAppUsage(
  opts: { date?: string; startDate?: string; endDate?: string; limit?: number } = {},
): Promise<AppUsageResponse> {
  const limit = opts.limit ?? 30;
  let qs = `?limit=${limit}`;
  if (opts.startDate && opts.endDate) {
    qs += `&start_date=${opts.startDate}&end_date=${opts.endDate}`;
  } else if (opts.date) {
    qs += `&date=${opts.date}`;
  }
  return requestJson<AppUsageResponse>(`/activity/apps${qs}`);
}
