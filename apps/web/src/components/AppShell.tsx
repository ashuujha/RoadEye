import React, { useState } from "react";
import {
  IconOverview,
  IconCamera,
  IconRoute,
  IconAnalytics,
  IconAlert,
  IconReview,
  IconSystem,
  IconChevronDown,
} from "./Icons";

export type PageId =
  | "Overview"
  | "Cameras"
  | "Vehicles"
  | "Analytics"
  | "Alerts"
  | "Review"
  | "System"
  | "Audit"
  | "Scenario runner";

interface AppShellProps {
  currentPage: PageId;
  onNavigate: (page: PageId) => void;
  actor: string;
  sourceMode?: string;
  pendingReviewCount?: number;
  pendingAlertsCount?: number;
  onSignOut: () => void;
  children: React.ReactNode;
}

export function AppShell({
  currentPage,
  onNavigate,
  actor,
  sourceMode = "SYNTHETIC INPUT · MOCK OCR",
  pendingReviewCount = 0,
  pendingAlertsCount = 0,
  onSignOut,
  children,
}: AppShellProps) {
  const [utilityOpen, setUtilityOpen] = useState(false);

  const navItems: Array<{ id: PageId; label: string; icon: React.ReactNode; badge?: number }> = [
    { id: "Overview", label: "Overview", icon: <IconOverview size={16} /> },
    { id: "Cameras", label: "Cameras & Video", icon: <IconCamera size={16} /> },
    { id: "Vehicles", label: "Vehicles & Trajectory", icon: <IconRoute size={16} /> },
    { id: "Analytics", label: "Analytics", icon: <IconAnalytics size={16} /> },
    {
      id: "Alerts",
      label: "Alerts & Watchlists",
      icon: <IconAlert size={16} />,
      badge: pendingAlertsCount > 0 ? pendingAlertsCount : undefined,
    },
    {
      id: "Review",
      label: "Review",
      icon: <IconReview size={16} />,
      badge: pendingReviewCount > 0 ? pendingReviewCount : undefined,
    },
  ];

  return (
    <div className="app-shell-root">
      {/* Top Bar (approx 60px) */}
      <header className="top-nav-bar" role="banner">
        <div className="nav-left">
          <div className="brand-lockup" onClick={() => onNavigate("Overview")} style={{ cursor: "pointer" }}>
            <div className="brand-mark">
              <span className="brand-dot" />
            </div>
            <div className="brand-text">
              <span className="brand-name">ROADEYE</span>
              <span className="brand-tag">OPERATIONS</span>
            </div>
          </div>

          <nav className="primary-nav" aria-label="Primary destinations">
            {navItems.map((item) => {
              const isActive =
                currentPage === item.id ||
                (item.id === "Alerts" && currentPage === "Alerts") ||
                (item.id === "Cameras" && currentPage === "Cameras");

              return (
                <button
                  key={item.id}
                  className={`nav-tab ${isActive ? "active" : ""}`}
                  onClick={() => onNavigate(item.id)}
                  aria-current={isActive ? "page" : undefined}
                >
                  {item.icon}
                  <span>{item.label}</span>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="nav-badge">{item.badge}</span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="nav-right">
          {/* Source mode pill */}
          <div className="mode-indicator" title="Current data pipeline provenance">
            <span className="mode-pulse" />
            <span className="mode-label">{sourceMode}</span>
          </div>

          {/* Utility Menu (System, Audit, Scenario runner) */}
          <div className="utility-menu-container">
            <button
              className={`btn-utility ${["System", "Audit", "Scenario runner"].includes(currentPage) ? "active" : ""}`}
              onClick={() => setUtilityOpen(!utilityOpen)}
              aria-expanded={utilityOpen}
              aria-haspopup="true"
            >
              <IconSystem size={15} />
              <span>Admin & System</span>
              <IconChevronDown size={14} />
            </button>

            {utilityOpen && (
              <div className="utility-dropdown" onMouseLeave={() => setUtilityOpen(false)}>
                <button
                  className={currentPage === "System" ? "active" : ""}
                  onClick={() => {
                    onNavigate("System");
                    setUtilityOpen(false);
                  }}
                >
                  System Readiness & Jobs
                </button>
                <button
                  className={currentPage === "Audit" ? "active" : ""}
                  onClick={() => {
                    onNavigate("Audit");
                    setUtilityOpen(false);
                  }}
                >
                  Audit History Log
                </button>
                <button
                  className={currentPage === "Scenario runner" ? "active" : ""}
                  onClick={() => {
                    onNavigate("Scenario runner");
                    setUtilityOpen(false);
                  }}
                >
                  Scenario Runner (Synthetic)
                </button>
              </div>
            )}
          </div>

          {/* User / Role & Sign Out */}
          <div className="user-profile">
            <span className="actor-badge" title="Authenticated local role">
              {actor}
            </span>
            <button className="btn-signout" onClick={onSignOut} title="Sign out / switch actor">
              Exit
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Workspace */}
      <main className="workspace-main" role="main">
        {children}
      </main>

      {/* Footer */}
      <footer className="workspace-footer">
        <div className="footer-content">
          <span>RoadEye · Bharat Electronics Limited SIH 26127 · Evidence-First ANPR Operations</span>
          <span className="footer-disclaimer">
            Camera points are observations; road segments are algorithmic inferences. Ground truth requires human verification.
          </span>
        </div>
      </footer>
    </div>
  );
}
