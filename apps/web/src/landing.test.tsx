import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { LandingPage, routeForPath } from "./landing";

describe("public landing page", () => {
  it("keeps the landing, login, and dashboard entry points distinct", () => {
    expect(routeForPath("/")).toBe("landing");
    expect(routeForPath("/login")).toBe("login");
    expect(routeForPath("/dashboard")).toBe("dashboard");
    expect(routeForPath("#/login")).toBe("login");
    expect(routeForPath("#/dashboard")).toBe("dashboard");
    expect(routeForPath("/anything-else")).toBe("landing");
  });

  it("renders the requested actions over Karman's video background", () => {
    const html = renderToStaticMarkup(
      <LandingPage onOpenDashboard={vi.fn()} />,
    );

    expect(html).toContain("See Every Plate.");
    expect(html).toContain("Live Dashboard");
    expect(html).toContain('poster="/roadeye-login-bg.png"');
    expect(html).toContain('src="/login-bg.mp4"');
  });
});
