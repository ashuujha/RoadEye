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
        <source src="/login-bg.mp4" type="video/mp4" />
      </video>
      <div className="landing-bg-overlay" />

      {/* ── Top Navigation Bar ── */}
      <nav className="landing-nav" role="navigation" aria-label="Main Navigation">
        <div className="landing-nav-left">
          <div className="landing-brand">
            <svg className="landing-brand-icon" width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="6" fill="rgba(255,255,255,0.1)" stroke="rgba(255,255,255,0.2)" strokeWidth="1"/>
              <circle cx="10" cy="10" r="3" fill="#D69A72"/>
              <circle cx="18" cy="10" r="3" fill="#8BAFC8"/>
              <rect x="8" y="16" width="12" height="3" rx="1.5" fill="rgba(255,255,255,0.5)"/>
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
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5"/>
              <rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5"/>
              <rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5"/>
              <rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
            Live Dashboard
          </button>
          <button
            type="button"
            className="landing-btn-outline"
            onClick={onOpenDashboard}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5"/>
              <line x1="11" y1="11" x2="14.5" y2="14.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
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
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <rect x="2" y="2" width="18" height="14" rx="2" stroke="#D69A72" strokeWidth="1.5"/>
              <circle cx="11" cy="9" r="3" stroke="#D69A72" strokeWidth="1.5"/>
              <line x1="4" y1="19" x2="18" y2="19" stroke="#D69A72" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="landing-feature-text">
            <strong>AI-Powered ANPR</strong>
            <span>&gt;90% OCR accuracy across all lighting and weather conditions</span>
          </div>
        </div>

        <div className="landing-feature-card" onClick={onOpenDashboard} role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenDashboard(); }}>
          <div className="landing-feature-icon icon-trajectory">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <circle cx="5" cy="5" r="3" stroke="#8BAFC8" strokeWidth="1.5"/>
              <circle cx="17" cy="17" r="3" stroke="#8BAFC8" strokeWidth="1.5"/>
              <path d="M7.5 7.5L14.5 14.5" stroke="#8BAFC8" strokeWidth="1.5" strokeDasharray="3 2" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="landing-feature-text">
            <strong>Trajectory Tracking</strong>
            <span>Follow any plate across the entire city camera network</span>
          </div>
        </div>

        <div className="landing-feature-card" onClick={onOpenDashboard} role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenDashboard(); }}>
          <div className="landing-feature-icon icon-analytics">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <rect x="3" y="12" width="4" height="7" rx="1" stroke="#82B095" strokeWidth="1.5"/>
              <rect x="9" y="8" width="4" height="11" rx="1" stroke="#82B095" strokeWidth="1.5"/>
              <rect x="15" y="3" width="4" height="16" rx="1" stroke="#82B095" strokeWidth="1.5"/>
            </svg>
          </div>
          <div className="landing-feature-text">
            <strong>Traffic Analytics</strong>
            <span>Heatmaps, density, speed &amp; congestion insights</span>
          </div>
        </div>

        <div className="landing-feature-card" onClick={onOpenDashboard} role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenDashboard(); }}>
          <div className="landing-feature-icon icon-alerts">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <path d="M11 3L3 18H19L11 3Z" stroke="#D2B477" strokeWidth="1.5" strokeLinejoin="round"/>
              <line x1="11" y1="10" x2="11" y2="13" stroke="#D2B477" strokeWidth="1.5" strokeLinecap="round"/>
              <circle cx="11" cy="15.5" r="0.75" fill="#D2B477"/>
            </svg>
          </div>
          <div className="landing-feature-text">
            <strong>Smart Alerts</strong>
            <span>Blacklist detection &amp; route anomaly alerts in real-time</span>
          </div>
        </div>
      </section>
    </div>
  );
}
