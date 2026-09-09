import type { MouseEvent, ReactNode } from "react";

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
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function RoadEyeLogo() {
  return (
    <svg viewBox="0 0 44 44" role="img" aria-label="RoadEye">
      <path d="M14 4H5v9M30 4h9v9M14 40H5v-9M30 40h9v-9" />
      <path d="M12 21h20l-2.3-6.2a3 3 0 0 0-2.8-1.9h-9.8a3 3 0 0 0-2.8 1.9L12 21Zm2 0v9h16v-9M17 30v3M27 30v3" />
      <circle cx="17" cy="24.5" r="1.5" />
      <circle cx="27" cy="24.5" r="1.5" />
    </svg>
  );
}

function LineIcon({ children }: { readonly children: ReactNode }) {
  return (
    <svg className="landing-line-icon" viewBox="0 0 32 32" aria-hidden="true">
      {children}
    </svg>
  );
}

export function LandingPage({ onOpenDashboard }: LandingPageProps) {
  return (
    <main className="landing-page">
      <video
        className="landing-bg-video"
        autoPlay
        loop
        muted
        playsInline
        poster="/roadeye-login-bg.png"
        aria-hidden="true"
        tabIndex={-1}
      >
        <source src="/login-bg.mp4" type="video/mp4" />
      </video>
      <div className="landing-bg-overlay" aria-hidden="true" />

      <nav className="landing-nav" aria-label="Main navigation">
        <a className="landing-brand" href="/" onClick={preventNavigation}>
          <RoadEyeLogo />
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
          Request Demo
        </button>
      </nav>

      <section className="landing-hero" id="product">
        <h1>
          See Every Plate.
          <span>Track Every Move.</span>
        </h1>
        <p className="landing-intro">
          City-wide evidence engine for multi-camera ANPR, trajectory tracking,
          and transparent traffic intelligence.
        </p>
        <div className="landing-actions">
          <button className="landing-primary-action" type="button" onClick={onOpenDashboard}>
            <LineIcon>
              <path d="M5 27h22M8 24V14h4v10M15 24V8h4v16M22 24V11h4v13" />
            </LineIcon>
            Live Dashboard
          </button>
          <button className="landing-secondary-action" type="button" onClick={onOpenDashboard}>
            <LineIcon>
              <circle cx="14" cy="14" r="7" />
              <path d="m19 19 7 7" />
            </LineIcon>
            Track a Vehicle
          </button>
        </div>
      </section>

      <section className="landing-capabilities" id="features" aria-label="Capabilities">
        <article>
          <LineIcon>
            <path d="M5 19h13v8H5zM8 19l2-6h7l3 6M23 9h4v4M21 11h8M23 20l3-3 3 3v7h-6z" />
          </LineIcon>
          <div>
            <h2>Evidence-First ANPR</h2>
            <p>Measured OCR quality with source crops and confidence context.</p>
          </div>
        </article>
        <article id="solutions">
          <LineIcon>
            <path d="M7 25c5-8 9-13 18-18M8 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8ZM24 18a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z" />
          </LineIcon>
          <div>
            <h2>Trajectory Tracking</h2>
            <p>Follow time-ordered observations across connected cameras.</p>
          </div>
        </article>
        <article id="analytics">
          <LineIcon>
            <path d="M5 27V15h5v12M14 27V9h5v18M23 27V19h5v8M5 10l7-5 6 3 10-6" />
          </LineIcon>
          <div>
            <h2>Traffic Analytics</h2>
            <p>Review prediction-based movement and transition summaries.</p>
          </div>
        </article>
        <article id="about">
          <LineIcon>
            <path d="M9 14h14v12H9zM12 14v-3a4 4 0 0 1 8 0v3M16 18v4" />
          </LineIcon>
          <div>
            <h2>Audited Access</h2>
            <p>Session-protected, read-only evidence with visible provenance.</p>
          </div>
        </article>
      </section>
    </main>
  );
}
