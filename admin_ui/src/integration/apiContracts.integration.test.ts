import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import { ApiClientError, authApi, dashboardApi, exceptionsApi, getAuthToken, setAuthToken } from "../api";

const apiBase = "/admin/api/v1";
const apiRoute = (path: string): string => `*${apiBase}${path}`;

const server = setupServer(
  http.post(apiRoute("/auth/login"), async () =>
    HttpResponse.json({ token: "token-1", expires_at: "2026-02-14T22:00:00Z", role: "admin" })
  ),
  http.get(apiRoute("/auth/me"), async ({ request }) => {
    const auth = request.headers.get("authorization");
    if (!auth) {
      return HttpResponse.json({ error: { code: "UNAUTHORIZED", message: "missing token" } }, { status: 401 });
    }
    return HttpResponse.json({ username: "admin", role: "admin", created_at: "2026-02-10T19:15:00Z" });
  }),
  http.get(apiRoute("/dashboard"), async () =>
    HttpResponse.json(
      {
        error: { code: "DEVICE_OFFLINE", message: "device offline" },
      },
      { status: 409 }
    )
  )
);

describe("API contracts via MSW", () => {
  beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
  beforeEach(() => {
    localStorage.clear();
    (import.meta as ImportMeta & { env: Record<string, string> }).env.VITE_ADMIN_API_BASE_URL = apiBase;
  });

  it("logs in and persists token from auth contract", async () => {
    const result = await authApi.login("admin", "secret");
    expect(result.role).toBe("admin");
    expect(getAuthToken()).toBe("token-1");
  });

  it("maps structured service error from dashboard contract", async () => {
    await expect(dashboardApi.getDashboard("prasun-pc")).rejects.toMatchObject({
      code: "DEVICE_OFFLINE",
      status: 409,
    } satisfies Partial<ApiClientError>);
  });

  it("clears token on unauthorized API response", async () => {
    server.use(
      http.get(apiRoute("/dashboard"), async () =>
        HttpResponse.json(
          {
            error: { code: "UNAUTHORIZED", message: "expired token" },
          },
          { status: 401 }
        )
      )
    );

    setAuthToken("stale-token");
    await expect(dashboardApi.getDashboard("prasun-pc")).rejects.toMatchObject({
      code: "UNAUTHORIZED",
      status: 401,
    } satisfies Partial<ApiClientError>);
    expect(getAuthToken()).toBeNull();
  });

  it("sends x-request-id header on API requests", async () => {
    let seenRequestId: string | null = null;
    server.use(
      http.get(apiRoute("/dashboard"), async ({ request }) => {
        seenRequestId = request.headers.get("x-request-id");
        return HttpResponse.json({
          device: { id: "prasun-pc", name: "prasun-pc", status: "online", enforcement_mode: "enforcing", last_seen: null },
          focus_score: 80,
          budget: { used_seconds: 1200, total_seconds: 2400, percent: 50 },
          blocks_today: 2,
          overrides_today: 1,
          attention_items: [],
          recent_overrides: [],
          top_friction: [],
        });
      })
    );

    await dashboardApi.getDashboard("prasun-pc");
    expect(seenRequestId).toBeTruthy();
    expect(typeof seenRequestId).toBe("string");
    expect((seenRequestId ?? "").length).toBeGreaterThan(8);
  });

  it("extracts request_id from structured error envelope", async () => {
    server.use(
      http.get(apiRoute("/dashboard"), async () =>
        HttpResponse.json(
          {
            error: {
              code: "UPSTREAM_ERROR",
              message: "tab server timeout",
              details: { request_id: "req-msw-123" },
            },
          },
          { status: 502 }
        )
      )
    );

    await expect(dashboardApi.getDashboard("prasun-pc")).rejects.toMatchObject({
      code: "UPSTREAM_ERROR",
      status: 502,
      requestId: "req-msw-123",
    } satisfies Partial<ApiClientError>);
  });

  it("supports exceptions create/list/revoke contract flow", async () => {
    const exceptions = [
      {
        id: "exc_1",
        domain: "youtube.com",
        type: "temporary",
        status: "active",
        created_at: "2026-02-14T22:00:00Z",
        expires_at: "2026-02-14T22:05:00Z",
        remaining_seconds: 240,
        reason: "homework video",
        emergency: false,
      },
    ];

    server.use(
      http.post(apiRoute("/exceptions"), async () =>
        HttpResponse.json({
          id: "exc_2",
          status: "active",
          type: "temporary",
          domain: "reddit.com",
          expires_at: "2026-02-14T22:10:00Z",
          audit_event_id: null,
        })
      ),
      http.get(apiRoute("/exceptions"), async () =>
        HttpResponse.json({ exceptions, total: exceptions.length, limit: 50, offset: 0 })
      ),
      http.delete(apiRoute("/exceptions/:id"), async ({ params }) => {
        const id = String(params.id);
        const index = exceptions.findIndex((x) => x.id === id);
        if (index >= 0) {
          exceptions.splice(index, 1);
        }
        return HttpResponse.json({ revoked: true, id });
      })
    );

    const created = await exceptionsApi.createException({ domain: "reddit.com", type: "temporary", duration_seconds: 300 });
    expect(created.id).toBe("exc_2");

    const listed = await exceptionsApi.listExceptions({ status: "active" });
    expect(listed.total).toBe(1);
    expect(listed.exceptions[0].id).toBe("exc_1");

    const revoked = await exceptionsApi.revokeException("exc_1");
    expect(revoked).toEqual({ revoked: true, id: "exc_1" });
  });
});
