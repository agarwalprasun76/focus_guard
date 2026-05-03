import { afterEach, describe, expect, it, vi } from "vitest";

import { getDashboard } from "./dashboard";

describe("dashboard api", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("builds query string for device and date range", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          device: { id: "default-device", name: "default-device", status: "online", enforcement_mode: "enforcing", last_seen: null },
          focus_score: 80,
          budget: { used_seconds: 600, total_seconds: 3600, percent: 16 },
          blocks_today: 1,
          overrides_today: 0,
          blocked_sites: [],
          total_blocks: 1,
          saved_links: { total: 0, unviewed: 0, top_domains: [], recent: [] },
          activity_summary: { total_events: 5, blocked_count: 1, distracting_count: 2, blocked_percentage: 20, distracting_percentage: 40 },
          open_tabs: [],
          recent_blocked_tabs: [],
          attention_items: [],
          recent_overrides: [],
          top_friction: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await getDashboard({
      deviceId: "kid-laptop",
      startDate: "2026-05-01",
      endDate: "2026-05-03",
    });

    const calledUrl = String(fetchSpy.mock.calls[0][0]);
    expect(calledUrl).toContain("/dashboard?");
    expect(calledUrl).toContain("device_id=kid-laptop");
    expect(calledUrl).toContain("start_date=2026-05-01");
    expect(calledUrl).toContain("end_date=2026-05-03");
  });
});

