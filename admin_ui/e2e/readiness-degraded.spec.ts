import { expect, test } from "@playwright/test";

test.describe("I1 readiness degraded states", () => {
  test("shows degraded runtime message when tab server is offline", async ({ page }) => {
    await page.route("**/admin/api/v1/**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname;
      const method = request.method();

      if (method === "POST" && path.endsWith("/auth/login")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ token: "token-1", expires_at: "2026-02-14T22:00:00Z", role: "admin" }),
        });
        return;
      }

      if (method === "GET" && path.endsWith("/auth/me")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ username: "admin", role: "admin", created_at: "2026-02-10T19:15:00Z" }),
        });
        return;
      }

      if (method === "GET" && path.endsWith("/meta")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            service: "admin_gateway",
            version: "0.1.0",
            capabilities: {
              auth: ["login", "refresh", "logout", "me"],
              dashboard: true,
              exceptions: ["create", "list", "revoke"],
              devices: ["list", "set_enforcement"],
              origin_protection: true,
              request_id: true,
            },
            readiness: { gateway: "online", tab_server: "offline", enforcement: "degraded" },
          }),
        });
        return;
      }

      if (method === "GET" && path.endsWith("/dashboard")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            device: {
              id: "prasun-pc",
              name: "prasun-pc",
              status: "offline",
              enforcement_mode: "tracking",
              last_seen: "2026-02-14T21:50:00Z",
            },
            focus_score: 68,
            budget: { used_seconds: 900, total_seconds: 2700, percent: 33.3 },
            blocks_today: 5,
            overrides_today: 0,
            attention_items: [],
            recent_overrides: [],
            top_friction: [],
          }),
        });
        return;
      }

      if (method === "GET" && path.endsWith("/exceptions")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ exceptions: [], total: 0, limit: 50, offset: 0 }),
        });
        return;
      }

      if (method === "GET" && path.endsWith("/devices")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            devices: [
              {
                id: "prasun-pc",
                name: "prasun-pc",
                status: "offline",
                enforcement_mode: "tracking",
                last_seen: null,
                browser_status: { connected_browsers: 0 },
              },
            ],
          }),
        });
        return;
      }

      if (method === "POST" && path.endsWith("/auth/logout")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
        return;
      }

      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "NOT_FOUND", message: "Not found" } }),
      });
    });

    await page.goto("/login");
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Admin Password").fill("secret123");
    await page.getByRole("button", { name: "Continue" }).click();

    // Dashboard.tsx: OfflineState when meta.readiness.tab_server === "offline"
    await expect(
      page.getByText("Tab server is offline. Data may be stale.", { exact: true })
    ).toBeVisible();
  });
});
