import { expect, test } from "@playwright/test";

test.describe("P4-06 performance sanity", () => {
  test("login and dashboard render latency snapshot", async ({ page }) => {
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
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            device: { id: "perf-pc", name: "perf-pc", status: "online", enforcement_mode: "enforcing", last_seen: "2026-02-14T21:50:00Z" },
            focus_score: 82,
            budget: { used_seconds: 1800, total_seconds: 2700, percent: 66.7 },
            blocks_today: 15,
            overrides_today: 1,
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
          body: JSON.stringify({ devices: [{ id: "perf-pc", name: "perf-pc", status: "online", enforcement_mode: "enforcing", last_seen: null, browser_status: { connected_browsers: 1 } }] }),
        });
        return;
      }

      if (method === "POST" && path.endsWith("/auth/logout")) {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true }) });
        return;
      }

      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "NOT_FOUND", message: "Not found" } }),
      });
    });

    const navStart = Date.now();
    await page.goto("/login");
    await expect(page.getByRole("button", { name: "Continue" })).toBeVisible();
    const loginUiReadyMs = Date.now() - navStart;

    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Admin Password").fill("secret123");

    const submitStart = Date.now();
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    const dashboardVisibleMs = Date.now() - submitStart;

    // Sanity thresholds for local/dev environment.
    expect(loginUiReadyMs).toBeLessThan(3500);
    expect(dashboardVisibleMs).toBeLessThan(4500);

    console.log(
      "P4-06_UI_RENDER_SNAPSHOT=" +
        JSON.stringify(
          {
            project: test.info().project.name,
            login_ui_ready_ms: loginUiReadyMs,
            dashboard_visible_after_submit_ms: dashboardVisibleMs,
          },
          null,
          0
        )
    );
  });
});
