import { requestJson } from "./client";

export type DashboardAttentionItem = {
  type: string;
  domain: string | null;
  count: number;
  suggestion: string;
};

export type DashboardRecentOverride = {
  id: string;
  domain: string;
  status: string;
  expires_at: string | null;
  remaining_seconds: number | null;
};

export type DashboardTopFrictionItem = {
  domain: string;
  override_count: number;
  time_used_seconds: number;
};

export type BlockedSiteItem = {
  domain: string;
  count: number;
  category?: string;
};

export type SavedLinkItem = {
  id: number;
  url: string;
  domain: string;
  title: string;
  category: string;
  comment: string;
  saved_at: string;
  viewed: boolean;
  viewed_at: string | null;
};

export type SavedLinksSummary = {
  total: number;
  unviewed: number;
  top_domains: Array<{ domain: string; count: number }>;
  recent: SavedLinkItem[];
};

export type DashboardActivitySummary = {
  total_events: number;
  blocked_count: number;
  distracting_count: number;
  blocked_percentage: number;
  distracting_percentage: number;
};

export type DashboardOpenTab = {
  id: string;
  browser: string;
  title: string;
  url: string;
  active: boolean;
};

export type DashboardRecentBlockedTab = {
  timestamp: string | null;
  domain: string;
  title: string;
  url: string;
  browser: string;
  reason: string;
};

export type DashboardResponse = {
  generated_at_utc?: number;
  device: {
    id: string;
    name: string;
    status: string;
    enforcement_mode: string;
    last_seen: string | null;
  };
  kpis?: {
    focus_score: number;
    blocks_today: number;
    overrides_today: number;
    usage_percent: number;
    total_events: number;
    blocked_count: number;
    distracting_count: number;
    unviewed_saved_links: number;
  };
  focus_score: number;
  budget: {
    used_seconds: number;
    total_seconds: number;
    percent: number;
  };
  blocks_today: number;
  overrides_today: number;
  blocked_sites: BlockedSiteItem[];
  total_blocks: number;
  saved_links: SavedLinksSummary;
  activity_summary: DashboardActivitySummary;
  open_tabs: DashboardOpenTab[];
  recent_blocked_tabs: DashboardRecentBlockedTab[];
  attention_items: DashboardAttentionItem[];
  recent_overrides: DashboardRecentOverride[];
  top_friction: DashboardTopFrictionItem[];
};

export type DashboardDateRange = {
  startDate: string; // YYYY-MM-DD
  endDate: string;   // YYYY-MM-DD
};

export function getDashboard(
  options?: { deviceId?: string; startDate?: string; endDate?: string }
): Promise<DashboardResponse> {
  const params = new URLSearchParams();
  if (options?.deviceId) params.set("device_id", options.deviceId);
  if (options?.startDate) params.set("start_date", options.startDate);
  if (options?.endDate) params.set("end_date", options.endDate);
  const query = params.toString() ? `?${params.toString()}` : "";
  return requestJson<DashboardResponse>(`/dashboard${query}`);
}
