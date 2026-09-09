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

  it("renders the requested dashboard path and dedicated hero image", () => {
    const html = renderToStaticMarkup(
      <LandingPage onOpenDashboard={vi.fn()} />,
    );

    expect(html).toContain("See every plate.");
    expect(html).toContain("Live dashboard");
    expect(html).toContain('class="landing-bg-art"');
  });
});
