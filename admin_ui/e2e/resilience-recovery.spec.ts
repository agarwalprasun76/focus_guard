import { expect, test } from "@playwright/test";

test.describe("I3 resilience recovery", () => {
  test("keeps stale dashboard snapshot during transient failure and recovers without reload", async ({ page }) => {
    let dashboardCallCount = 0;
    let recoveryEnabled = false;

    await page.addInitScript(() => {
      (globalThis as Record<string, unknown>).__FG_TEST_DASHBOARD_REFETCH_MS__ = 500;
      (globalThis as Record<string, unknown>).__FG_TEST_META_REFETCH_MS__ = 500;
    });

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
            readiness: { gateway: "online", tab_server: "online", enforcement: "active" },
          }),
        });
        return;
      }

      if (method === "GET" && path.endsWith("/dashboard")) {
        dashboardCallCount += 1;

        if (recoveryEnabled || dashboardCallCount <= 1) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              device: {
                id: "resilience-pc",
                name: "resilience-pc",
                status: "online",
                enforcement_mode: "enforcing",
                last_seen: "2026-02-14T21:50:00Z",
              },
              focus_score: 81,
              budget: { used_seconds: 800, total_seconds: 2700, percent: 29.6 },
              blocks_today: 7,
              overrides_today: 1,
              attention_items: [],
              recent_overrides: [],
              top_friction: [],
            }),
          });
          return;
        }

        await route.fulfill({
          status: 502,
          contentType: "application/json",
          headers: { "x-request-id": "resilience-req-1" },
          body: JSON.stringify({
            error: {
              code: "UPSTREAM_ERROR",
              message: "simulated transient timeout",
              details: { request_id: "resilience-req-1" },
            },
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
                id: "resilience-pc",
                name: "resilience-pc",
                status: "online",
                enforcement_mode: "enforcing",
                last_seen: null,
                browser_status: { connected_browsers: 1 },
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

    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("Focus Score")).toBeVisible();

    await expect(page.getByText(/Showing last known dashboard snapshot/i)).toBeVisible();

    recoveryEnabled = true;

    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText(/Showing last known dashboard snapshot/i)).not.toBeVisible();
  });
});
