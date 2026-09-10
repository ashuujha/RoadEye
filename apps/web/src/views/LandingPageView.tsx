import React from "react";

interface LandingPageViewProps {
  onOpenDashboard: () => void;
  onOpenLogin: () => void;
}

export function LandingPageView({
  onOpenDashboard,
  onOpenLogin,
}: LandingPageViewProps) {
  return (
    <div className="landing-root">
      {/* Fullscreen Background Video */}
      <video
        autoPlay
        loop
        muted
        playsInline
        className="landing-bg-video"
      >
        <source src="/just_extract_the_background.mp4" type="video/mp4" />
      </video>
      <div className="landing-bg-overlay" />

      {/* ── Top Navigation Bar ── */}
      <nav className="landing-nav" role="navigation" aria-label="Main Navigation">
        <div className="landing-nav-left">
          <div className="landing-brand">
            <svg className="landing-brand-icon" width="68" height="68" viewBox="0 0 64 64" fill="none" aria-hidden="true">
              <path d="M17 5H5V17M47 5H59V17M5 47V59H17M59 47V59H47" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M18 35L22 25H42L46 35M16 35H48V47H16V35Z" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M21 47V52M43 47V52M22 40H26M38 40H42" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round"/>
            </svg>
            <span className="landing-brand-name">RoadEye</span>
          </div>
          <div className="landing-nav-links">
            <button type="button" onClick={onOpenDashboard}>Product</button>
            <button type="button" onClick={onOpenDashboard}>Features</button>
            <button type="button" onClick={onOpenDashboard}>Analytics</button>
            <button type="button" onClick={onOpenDashboard}>Solutions</button>
            <button type="button" onClick={onOpenDashboard}>About</button>
          </div>
        </div>
        <button
          type="button"
          className="landing-nav-cta"
          onClick={onOpenLogin}
        >
          Request Demo
        </button>
      </nav>

      {/* ── Hero Content ── */}
      <main className="landing-hero">
        <h1 className="landing-hero-title">
          See Every Plate.<br />
          Track Every Move.
        </h1>
        <p className="landing-hero-subtitle">
          City-wide AI engine for multi-camera ANPR,<br />
          trajectory tracking and real-time traffic<br />
          intelligence.
        </p>
        <div className="landing-hero-actions">
          <button
            type="button"
            className="landing-btn-primary"
            onClick={onOpenDashboard}
          >
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
              <path d="M3 19H20M5 16V10H8V16M10 16V5H13V16M15 16V8H18V16" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M4 6L8 3L12 6L18 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Live Dashboard
          </button>
          <button
            type="button"
            className="landing-btn-outline"
            onClick={onOpenDashboard}
          >
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
              <circle cx="9" cy="9" r="6" stroke="currentColor" strokeWidth="1.7"/>
              <line x1="13.5" y1="13.5" x2="19" y2="19" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/>
            </svg>
            Track a Vehicle
          </button>
        </div>
      </main>

      {/* ── Bottom Feature Cards ── */}
      <section className="landing-features" aria-label="Key Product Pillars">
        <div className="landing-feature-card" onClick={onOpenDashboard} role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenDashboard(); }}>
          <div className="landing-feature-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
              <path d="M8 17H31L39 23V35H8V17Z" stroke="currentColor" strokeWidth="2.4" strokeLinejoin="round"/>
              <circle cx="22" cy="26" r="6" stroke="currentColor" strokeWidth="2.4"/>
              <path d="M39 25L44 22V31L39 28M12 35V41M28 35V41M7 41H33" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="landing-feature-text">
            <strong>AI-Powered ANPR</strong>
            <span>&gt;90% OCR accuracy<br />in all conditions</span>
          </div>
        </div>

        <div className="landing-feature-card" onClick={onOpenDashboard} role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenDashboard(); }}>
          <div className="landing-feature-icon icon-trajectory">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
              <path d="M18 20C18 27 10 34 10 34S2 27 2 20A8 8 0 1 1 18 20Z" stroke="currentColor" strokeWidth="2.4"/>
              <circle cx="10" cy="20" r="2.5" fill="currentColor"/>
              <path d="M18 20C18 27 10 34 10 34S2 27 2 20A8 8 0 1 1 18 20Z" stroke="currentColor" strokeWidth="2.4" transform="translate(26 -10)"/>
              <circle cx="36" cy="10" r="2.5" fill="currentColor"/>
              <path d="M7 39C18 34 25 42 37 35" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="landing-feature-text">
            <strong>Trajectory Tracking</strong>
            <span>Follow any plate across<br />the entire city</span>
          </div>
        </div>

        <div className="landing-feature-card" onClick={onOpenDashboard} role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenDashboard(); }}>
          <div className="landing-feature-icon icon-analytics">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
              <path d="M5 42H44M8 38V27H15V38M19 38V20H26V38M30 38V14H37V38" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M8 19L18 11L25 16L40 4M34 4H40V10" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="landing-feature-text">
            <strong>Traffic Analytics</strong>
            <span>Heatmaps, density,<br />speed &amp; congestion</span>
          </div>
        </div>

        <div className="landing-feature-card" onClick={onOpenDashboard} role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenDashboard(); }}>
          <div className="landing-feature-icon icon-alerts">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
              <path d="M11 34H37L33 29V20C33 14 29 10 24 10C19 10 15 14 15 20V29L11 34Z" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M20 39C21 42 27 42 28 39M24 5V9M37 10L34 13M11 10L14 13" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"/>
              <path d="M39 17L41 15M9 17L7 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="landing-feature-text">
            <strong>Smart Alerts</strong>
            <span>Blacklist detection &amp;<br />route anomaly alerts</span>
          </div>
        </div>
      </section>
    </div>
  );
}
