import { afterEach, describe, expect, it, vi } from "vitest";

import { listDevices, setDeviceEnforcement } from "./devices";

describe("devices api", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls list devices endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ devices: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await listDevices();
    expect(String(fetchSpy.mock.calls[0][0])).toContain("/devices");
  });

  it("calls set enforcement endpoint with encoded device id", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ updated: true, device_id: "kid-laptop", mode: "advisory" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await setDeviceEnforcement("kid laptop", { mode: "advisory" });
    expect(String(fetchSpy.mock.calls[0][0])).toContain("/devices/kid%20laptop/enforcement");

    const [, init] = fetchSpy.mock.calls[0];
    expect(init?.method).toBe("PUT");
    expect(JSON.parse(String(init?.body))).toMatchObject({ mode: "advisory" });
  });
});

