import { afterEach, describe, expect, it, vi } from "vitest";

import { createException, listExceptions, revokeException } from "./exceptions";

describe("exceptions api", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps temporary create payload shape", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ id: "1", status: "active", type: "temporary", domain: "youtube.com", expires_at: null, audit_event_id: null }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    await createException({ domain: "YouTube.com", type: "temporary", duration_seconds: 300, emergency: true, reason: "class" });

    const [, requestInit] = fetchSpy.mock.calls[0];
    const body = JSON.parse(String(requestInit?.body));
    expect(body).toMatchObject({ domain: "youtube.com", type: "temporary", duration_seconds: 300, emergency: true });
  });

  it("maps budgeted create payload shape", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ id: "2", status: "active", type: "budgeted", domain: "reddit.com", expires_at: null, audit_event_id: null }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    await createException({ domain: "reddit.com", type: "budgeted", budget_seconds_per_day: 1200 });

    const [, requestInit] = fetchSpy.mock.calls[0];
    const body = JSON.parse(String(requestInit?.body));
    expect(body).toMatchObject({ type: "budgeted", budget_seconds_per_day: 1200 });
  });

  it("builds list and revoke endpoints", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ exceptions: [], total: 0, limit: 50, offset: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    await listExceptions({ status: "all", domain: "youtube.com", limit: 10, offset: 5 });
    expect(String(fetchSpy.mock.calls[0][0])).toContain("/exceptions?status=all");
    expect(String(fetchSpy.mock.calls[0][0])).toContain("domain=youtube.com");

    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ revoked: true, id: "abc" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    await revokeException("abc");
    expect(String(fetchSpy.mock.calls[1][0])).toContain("/exceptions/abc");
  });
});
