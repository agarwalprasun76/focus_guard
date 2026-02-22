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
  device: {
    id: string;
    name: string;
    status: string;
    enforcement_mode: string;
    last_seen: string | null;
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

export function getDashboard(deviceId?: string): Promise<DashboardResponse> {
  const query = deviceId ? `?device_id=${encodeURIComponent(deviceId)}` : "";
  return requestJson<DashboardResponse>(`/dashboard${query}`);
}
