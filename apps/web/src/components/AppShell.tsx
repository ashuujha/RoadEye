import type { ReactNode } from "react";

import { IconAnalytics, IconCamera, IconOverview, IconRoute } from "./Icons";

export type PageId = "Map" | "Trajectories" | "Analytics" | "Evidence";

interface AppShellProps {
  currentPage: PageId;
  onNavigate: (page: PageId) => void;
  actor: string;
  sourceMode?: string;
  onSignOut: () => void;
  children: ReactNode;
}

const navItems: Array<{
  id: PageId;
  label: string;
  icon: ReactNode;
}> = [
  { id: "Map", label: "Map", icon: <IconOverview size={16} /> },
  { id: "Trajectories", label: "Trajectories", icon: <IconRoute size={16} /> },
  { id: "Analytics", label: "Analytics", icon: <IconAnalytics size={16} /> },
  { id: "Evidence", label: "Evidence", icon: <IconCamera size={16} /> },
];

export function AppShell({
  currentPage,
  onNavigate,
  actor,
  sourceMode = "AUDITED PREDICTIONS · READ-ONLY",
  onSignOut,
  children,
}: AppShellProps) {
  return (
    <div className="app-shell-root">
      <header className="top-nav-bar" role="banner">
        <div className="nav-left">
          <button
            type="button"
            className="brand-lockup"
            onClick={() => onNavigate("Map")}
            aria-label="Open prediction network map"
          >
            <span className="brand-mark" aria-hidden="true">
              <span className="brand-dot" />
            </span>
            <span className="brand-text">
              <span className="brand-name">ROADEYE</span>
              <span className="brand-tag">OPERATIONS</span>
            </span>
          </button>

          <nav className="primary-nav" aria-label="Primary destinations">
            {navItems.map((item) => {
              const isActive = currentPage === item.id;

              return (
                <button
                  type="button"
                  key={item.id}
                  className={`nav-tab ${isActive ? "active" : ""}`}
                  onClick={() => onNavigate(item.id)}
                  aria-current={isActive ? "page" : undefined}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        <div className="nav-right">
          <div className="mode-indicator" title="Current data pipeline provenance">
            <span className="mode-pulse" />
            <span className="mode-label">{sourceMode}</span>
          </div>
          <div className="user-profile">
            <span className="actor-badge" title="Authenticated local actor">
              {actor}
            </span>
            <button
              type="button"
              className="btn-signout"
              onClick={onSignOut}
              title="Sign out or switch actor"
            >
              Exit
            </button>
          </div>
        </div>
      </header>

      <main className="workspace-main" role="main">
        {children}
      </main>

      <footer className="workspace-footer">
        <div className="footer-content">
          <span>RoadEye · Bharat Electronics Limited SIH 26127 · Evidence-First ANPR Operations</span>
          <span className="footer-disclaimer">
            Camera points are observations; road segments are algorithmic inferences. Ground
            truth requires human verification.
          </span>
        </div>
      </footer>
    </div>
  );
}
