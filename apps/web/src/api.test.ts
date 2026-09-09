import { describe, expect, it, vi } from "vitest";

import { RoadEyeApiError, createRoadEyeApi } from "./api";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("RoadEye auth client", () => {
  it("posts the typed login body with same-origin credentials", async () => {
    const fetchRequest = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        jsonResponse({ actor: "administrator", mode: "local_demo" }),
    );
    const client = createRoadEyeApi({ fetch: fetchRequest });

    await expect(
      client.login({ actor: "administrator", password: "local secret" }),
    ).resolves.toEqual({ actor: "administrator", mode: "local_demo" });

    expect(fetchRequest).toHaveBeenCalledWith("/api/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        actor: "administrator",
        password: "local secret",
      }),
      signal: undefined,
    });
  });

  it("discovers health and session and logs out without v1 requests", async () => {
    const payloads = [
      { status: "ready" },
      { actor: "viewer", mode: "local_demo" },
      { logged_out: true },
    ];
    const fetchRequest = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        jsonResponse(payloads.shift()),
    );
    const client = createRoadEyeApi({ fetch: fetchRequest });

    await client.health();
    await client.me();
    await client.logout();

    const calls = fetchRequest.mock.calls.map(([path, init]) => ({ path, init }));
    expect(calls.map(({ path }) => path)).toEqual([
      "/api/health",
      "/api/auth/me",
      "/api/auth/logout",
    ]);
    expect(calls.every(({ path }) => !String(path).includes("/v1"))).toBe(true);
    expect(calls.every(({ init }) => init?.credentials === "same-origin")).toBe(
      true,
    );
  });

  it("centralizes session-expiry handling without treating bad login as expiry", async () => {
    const onSessionExpired = vi.fn();
    const expiredClient = createRoadEyeApi({
      fetch: async () => jsonResponse({ detail: "SESSION_REQUIRED" }, 401),
      onSessionExpired,
    });

    await expect(expiredClient.status()).rejects.toMatchObject({
      status: 401,
      detail: "SESSION_REQUIRED",
    } satisfies Partial<RoadEyeApiError>);
    expect(onSessionExpired).toHaveBeenCalledOnce();

    const invalidClient = createRoadEyeApi({
      fetch: async () => jsonResponse({ detail: "INVALID_CREDENTIALS" }, 401),
      onSessionExpired,
    });
    await expect(
      invalidClient.login({ actor: "viewer", password: "wrong" }),
    ).rejects.toBeInstanceOf(RoadEyeApiError);
    expect(onSessionExpired).toHaveBeenCalledOnce();
  });
});
