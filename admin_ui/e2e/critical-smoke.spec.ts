import { expect, test } from "@playwright/test";

import { expectDashboardHeroVisible } from "./helpers";

type ExceptionItem = {
  id: string;
  domain: string;
  status: string;
  type: string;
  created_at: string | null;
  expires_at: string | null;
  remaining_seconds: number;
  reason: string | null;
  emergency: boolean;
};

test.describe("Critical Phase1 smoke", () => {
  test("login, allow temp, revoke override", async ({ page }) => {
    const exceptions: ExceptionItem[] = [];

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

      if (method === "GET" && path.endsWith("/auth/me")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ username: "admin", role: "admin", created_at: "2026-02-10T19:15:00Z" }),
        });
        return;
      }

      if (method === "POST" && path.endsWith("/auth/logout")) {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true }) });
        return;
      }

      if (method === "GET" && path.endsWith("/dashboard")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            device: { id: "prasun-pc", name: "prasun-pc", status: "online", enforcement_mode: "enforcing", last_seen: "2026-02-14T21:50:00Z" },
            focus_score: 82,
            budget: { used_seconds: 1800, total_seconds: 2700, percent: 66.7 },
            blocks_today: 15,
            overrides_today: exceptions.length,
            saved_links: {
              total: 2,
              unviewed: 1,
              top_domains: [
                { domain: "youtube.com", count: 1 },
                { domain: "reddit.com", count: 1 },
              ],
              recent: [
                {
                  id: 1,
                  url: "https://www.youtube.com/watch?v=abc",
                  domain: "youtube.com",
                  title: "Focus video",
                  category: "entertainment",
                  comment: "Watch later",
                  saved_at: "2026-02-14T21:45:00Z",
                  viewed: false,
                  viewed_at: null,
                },
              ],
            },
            attention_items: [],
            recent_overrides: [],
            top_friction: [],
          }),
        });
        return;
      }

      if (method === "POST" && path.endsWith("/exceptions")) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        const item: ExceptionItem = {
          id: "exc_1",
          domain: String(payload.domain ?? ""),
          status: "active",
          type: String(payload.type ?? "temporary"),
          created_at: "2026-02-14T22:00:00Z",
          expires_at: "2026-02-14T22:05:00Z",
          remaining_seconds: 240,
          reason: String(payload.reason ?? ""),
          emergency: Boolean(payload.emergency),
        };
        exceptions.push(item);
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ id: item.id, status: item.status, type: item.type, domain: item.domain, expires_at: item.expires_at, audit_event_id: null }),
        });
        return;
      }

      if (method === "GET" && path.endsWith("/exceptions")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ exceptions, total: exceptions.length, limit: 50, offset: 0 }),
        });
        return;
      }

      if (method === "DELETE" && path.includes("/exceptions/")) {
        const id = path.split("/").pop();
        const idx = exceptions.findIndex((x) => x.id === id);
        if (idx >= 0) {
          exceptions.splice(idx, 1);
        }
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ revoked: true, id }) });
        return;
      }

      if (method === "GET" && path.endsWith("/devices")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ devices: [{ id: "prasun-pc", name: "prasun-pc", status: "online", enforcement_mode: "enforcing", last_seen: null, browser_status: { connected_browsers: 1 } }] }),
        });
        return;
      }

      await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: { code: "NOT_FOUND", message: "Not found" } }) });
    });

    await page.goto("/login");
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Admin Password").fill("secret123");
    await page.getByRole("button", { name: "Continue" }).click();

    await expectDashboardHeroVisible(page);

    await page.goto("/overrides");
    await page.getByRole("button", { name: "New Rule" }).click();
    await page.getByLabel("Domain").fill("youtube.com");
    await page.getByLabel("Type").selectOption("temporary");
    await page.locator("#create-exception-dialog").locator("#duration_seconds").fill("300");
    // Mobile layout: bottom nav can overlap the modal footer; force avoids flaky pointer interception.
    await page.locator("#create-exception-dialog").getByRole("button", { name: "Create" }).click({ force: true });

    await expect(page.getByText(/Created temporary rule for youtube\.com/i)).toBeVisible();
    const revokeButton = page.getByRole("button", { name: /Revoke exception for youtube.com/i });
    await expect(revokeButton).toBeVisible();

    await revokeButton.click();
    await expect(page.getByText("No exceptions found for this filter.")).toBeVisible();

    await page.goto("/saved-links");
    await expect(page.getByRole("heading", { name: "Saved Links", exact: true })).toBeVisible();
    const savedLink = page.getByRole("link", { name: "https://www.youtube.com/watch?v=abc", exact: true });
    await expect(savedLink).toBeVisible();
    await expect(savedLink).toHaveAttribute("href", "https://www.youtube.com/watch?v=abc");
  });
});
