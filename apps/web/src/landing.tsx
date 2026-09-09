import type { MouseEvent } from "react";

export type AppRoute = "landing" | "login" | "dashboard";

export function routeForPath(pathnameOrHash: string): AppRoute {
  const routePath = pathnameOrHash.startsWith("#")
    ? pathnameOrHash.slice(1)
    : pathnameOrHash;
  if (routePath === "/login") return "login";
  if (routePath === "/dashboard") return "dashboard";
  return "landing";
}

interface LandingPageProps {
  readonly onOpenDashboard: () => void;
}

function preventNavigation(event: MouseEvent<HTMLAnchorElement>) {
  event.preventDefault();
}

export function LandingPage({ onOpenDashboard }: LandingPageProps) {
  return (
    <main className="landing-page">
      <div className="landing-bg-art" aria-hidden="true" />
      <div className="landing-bg-overlay" aria-hidden="true" />

      <nav className="landing-nav" aria-label="Main navigation">
        <a className="landing-brand" href="/" onClick={preventNavigation}>
          <span className="landing-brand-mark" aria-hidden="true">
            <i />
          </span>
          <span>RoadEye</span>
        </a>
        <div className="landing-nav-links">
          <a href="#product">Product</a>
          <a href="#features">Features</a>
          <a href="#analytics">Analytics</a>
          <a href="#solutions">Solutions</a>
          <a href="#about">About</a>
        </div>
        <button className="landing-demo-link" type="button" onClick={onOpenDashboard}>
          Request demo
        </button>
      </nav>

      <section className="landing-hero" id="product">
        <p className="landing-eyebrow">CITY-WIDE VEHICLE INTELLIGENCE</p>
        <h1>
          See every plate.
          <span>Track every move.</span>
        </h1>
        <p className="landing-intro">
          A connected evidence workspace for multi-camera vehicle observations,
          trajectory review, and transparent traffic intelligence.
        </p>
        <div className="landing-actions">
          <button className="landing-primary-action" type="button" onClick={onOpenDashboard}>
            <span aria-hidden="true">▣</span>
            Live dashboard
          </button>
          <button className="landing-secondary-action" type="button" onClick={onOpenDashboard}>
            <span aria-hidden="true">⌕</span>
            Track a vehicle
          </button>
        </div>
      </section>

      <section className="landing-capabilities" id="features" aria-label="Capabilities">
        <article>
          <span className="landing-capability-icon" aria-hidden="true">⌁</span>
          <div>
            <h2>Evidence-first review</h2>
            <p>Inspect source frames, crop provenance, and prediction context.</p>
          </div>
        </article>
        <article id="solutions">
          <span className="landing-capability-icon" aria-hidden="true">⌖</span>
          <div>
            <h2>Trajectory tracking</h2>
            <p>Follow time-ordered observations across connected cameras.</p>
          </div>
        </article>
        <article id="analytics">
          <span className="landing-capability-icon" aria-hidden="true">▥</span>
          <div>
            <h2>Traffic analytics</h2>
            <p>Review prediction-based movement and transition summaries.</p>
          </div>
        </article>
        <article id="about">
          <span className="landing-capability-icon" aria-hidden="true">✦</span>
          <div>
            <h2>Read-only by design</h2>
            <p>Local access is session-protected and evidence remains auditable.</p>
          </div>
        </article>
      </section>
    </main>
  );
}
