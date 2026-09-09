import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { RoadEyeApiError } from "./api";
import {
  LoginPage,
  SessionGate,
  authenticationReducer,
  initialAuthenticationState,
  loginErrorMessage,
} from "./auth";
import { AppShell } from "./components/AppShell";

function renderWithQueries(element: React.ReactNode): string {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return renderToStaticMarkup(
    <QueryClientProvider client={client}>{element}</QueryClientProvider>,
  );
}

describe("authentication state and login gate", () => {
  it("renders Karman's video shell, poster, actors, and administrator default", () => {
    const html = renderWithQueries(
      <LoginPage onAuthenticated={vi.fn()} />,
    );

    expect(html).toContain('class="login-page-wrapper"');
    expect(html).toContain('poster="/roadeye-login-bg.png"');
    expect(html).toContain('src="/login-bg.mp4"');
    for (const actor of ["viewer", "investigator", "administrator", "approver"]) {
      expect(html).toContain(`value="${actor}"`);
    }
    expect(html).toContain('value="administrator" selected=""');
    expect(html).toContain("identical read-only access");
  });

  it("shows a distinct session-discovery state and mounts only authenticated content", () => {
    const loading = renderWithQueries(
      <SessionGate
        state={initialAuthenticationState}
        onAuthenticated={vi.fn()}
        onRetryDiscovery={vi.fn()}
      >
        <div>dashboard content</div>
      </SessionGate>,
    );
    expect(loading).toContain("Restoring your session");
    expect(loading).not.toContain("dashboard content");

    const authenticated = renderWithQueries(
      <SessionGate
        state={{
          status: "authenticated",
          session: { actor: "approver", mode: "local_demo" },
        }}
        onAuthenticated={vi.fn()}
        onRetryDiscovery={vi.fn()}
      >
        <div>dashboard content</div>
      </SessionGate>,
    );
    expect(authenticated).toContain("dashboard content");
    expect(authenticated).not.toContain("Local demonstration sign in");
  });

  it("handles successful login, logout, and expiry as explicit transitions", () => {
    const session = { actor: "investigator", mode: "local_demo" } as const;
    const authenticated = authenticationReducer(initialAuthenticationState, {
      type: "SESSION_FOUND",
      session,
    });
    expect(authenticated).toEqual({ status: "authenticated", session });
    expect(
      authenticationReducer(authenticated, { type: "SIGNED_OUT" }),
    ).toEqual({ status: "anonymous" });
    expect(
      authenticationReducer(authenticated, { type: "SESSION_EXPIRED" }),
    ).toEqual({ status: "anonymous" });
  });

  it("turns invalid credentials into concise form feedback", () => {
    expect(
      loginErrorMessage(
        new RoadEyeApiError(401, "Unauthorized", "INVALID_CREDENTIALS"),
      ),
    ).toBe("Invalid actor or password.");
  });

  it("restores the authenticated actor badge and Exit control", () => {
    const html = renderWithQueries(
      <AppShell
        currentPage="Map"
        onNavigate={vi.fn()}
        actor="viewer"
        onSignOut={vi.fn()}
      >
        <div>map workspace</div>
      </AppShell>,
    );
    expect(html).toContain('class="actor-badge"');
    expect(html).toContain(">viewer</span>");
    expect(html).toContain(">Exit</button>");
    expect(html).toContain("map workspace");
    expect(html).not.toContain("Alerts &amp; Watchlists");
  });
});
