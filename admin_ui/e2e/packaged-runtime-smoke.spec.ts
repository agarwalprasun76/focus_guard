import { expect, test } from "@playwright/test";

const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {};
const packagedAdminUsername = env.PACKAGED_ADMIN_USERNAME ?? "admin";
const packagedAdminPassword = env.PACKAGED_ADMIN_PASSWORD ?? "secret123";

test.describe("I2 packaged runtime smoke", () => {
  test("serves admin shell and core admin API endpoints", async ({ page, request }) => {
    const adminPage = await page.goto("/admin");
    expect(adminPage).not.toBeNull();
    expect(adminPage?.status()).toBe(200);

    const html = await page.content();
    expect(html.toLowerCase()).toContain("<html");

    const health = await request.get("/admin/health");
    expect(health.status()).toBe(200);
    const healthJson = await health.json();
    expect(healthJson.service).toBe("admin_gateway");

    const meta = await request.get("/admin/api/v1/meta");
    expect(meta.status()).toBe(200);
    const metaJson = await meta.json();
    expect(metaJson.service).toBe("admin_gateway");
    expect(metaJson.capabilities.request_id).toBeTruthy();

    const dashboard = await request.get("/admin/api/v1/dashboard?device_id=packaged-smoke");
    expect(dashboard.status()).toBe(200);
    const dashboardJson = await dashboard.json();
    expect(dashboardJson).toHaveProperty("device");
    expect(dashboardJson).toHaveProperty("budget");

    // Ensure SPA fallback serves the dedicated saved-links entry route in packaged lane.
    const savedLinksRoute = await request.get("/admin/saved-links");
    expect(savedLinksRoute.status()).toBe(200);
    expect(savedLinksRoute.headers()["content-type"] ?? "").toContain("text/html");
  });

  test("validates packaged exceptions mutation flow (create/list/revoke)", async ({ request }) => {
    const login = await request.post("/admin/api/v1/auth/login", {
      data: {
        username: packagedAdminUsername,
        password: packagedAdminPassword,
      },
    });

    expect(
      login.status(),
      [
        "401 login failed — set PACKAGED_ADMIN_USERNAME/PACKAGED_ADMIN_PASSWORD.",
        "PowerShell example:",
        '$env:PACKAGED_ADMIN_PASSWORD = "<your-actual-admin-password>"',
      ].join(" ")
    ).toBe(200);
    const loginJson = await login.json();
    const token = String(loginJson.token ?? "");
    expect(token).not.toEqual("");

    const domain = `packaged-smoke-${Date.now()}.example`;
    const created = await request.post("/admin/api/v1/exceptions", {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        domain,
        type: "temporary",
        duration_seconds: 120,
        reason: "packaged mutation smoke",
        emergency: false,
      },
    });

    expect(created.status()).toBe(200);
    const createdJson = await created.json();
    expect(createdJson.status).toBe("active");
    const exceptionId = String(createdJson.id ?? "");
    expect(exceptionId).not.toEqual("");

    const listed = await request.get(
      `/admin/api/v1/exceptions?status=active&domain=${encodeURIComponent(domain)}&limit=50&offset=0`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    expect(listed.status()).toBe(200);
    const listedJson = await listed.json();
    expect(Array.isArray(listedJson.exceptions)).toBeTruthy();
    expect(listedJson.exceptions.some((item: { id?: string }) => item.id === exceptionId)).toBeTruthy();

    const revoked = await request.delete(`/admin/api/v1/exceptions/${encodeURIComponent(exceptionId)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    expect(revoked.status()).toBe(200);
    const revokedJson = await revoked.json();
    expect(revokedJson).toEqual({ revoked: true, id: exceptionId });

    const listedAfterRevoke = await request.get(
      `/admin/api/v1/exceptions?status=active&domain=${encodeURIComponent(domain)}&limit=50&offset=0`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    expect(listedAfterRevoke.status()).toBe(200);
    const listedAfterRevokeJson = await listedAfterRevoke.json();
    expect(
      listedAfterRevokeJson.exceptions.some((item: { id?: string }) => item.id === exceptionId)
    ).toBeFalsy();
  });
});
