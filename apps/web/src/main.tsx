import React, { useCallback, useEffect, useReducer, useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useQueryClient,
} from "@tanstack/react-query";
import { createRoot } from "react-dom/client";

import {
  api,
  isSessionRequiredError,
  subscribeToSessionExpiry,
  type AuthSession,
} from "./api";
import {
  SessionGate,
  authenticationReducer,
  initialAuthenticationState,
} from "./auth";
import { LandingPage, routeForPath, type AppRoute } from "./landing";
import { AppShell, type PageId } from "./components/AppShell";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { PredictionMapView } from "./components/NetworkMap";
import { AnalyticsView } from "./views/AnalyticsView";
import { CameraWorkspaceView } from "./views/CameraWorkspaceView";
import { TrajectoryView } from "./views/TrajectoryView";
import type { EvidenceSelection } from "./evidence";
import "./style.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  const cache = useQueryClient();
  const [authentication, dispatchAuthentication] = useReducer(
    authenticationReducer,
    initialAuthenticationState,
  );
  const [page, setPage] = useState<PageId>("Map");
  const [route, setRoute] = useState<AppRoute>(() =>
    routeForPath(window.location.hash || window.location.pathname),
  );
  const [selectedEvidence, setSelectedEvidence] =
    useState<EvidenceSelection | null>(null);
  const closeEvidence = useCallback(() => setSelectedEvidence(null), []);

  const changeRoute = useCallback(
    (nextRoute: AppRoute, replace = false) => {
      const nextPath =
        nextRoute === "landing" ? "/" : `/#/${nextRoute}`;
      window.history[replace ? "replaceState" : "pushState"]({}, "", nextPath);
      setRoute(nextRoute);
    },
    [],
  );

  const discoverSession = useCallback((signal?: AbortSignal) => {
    dispatchAuthentication({ type: "DISCOVERY_STARTED" });
    void api
      .me({ signal })
      .then((session) => {
        dispatchAuthentication({ type: "SESSION_FOUND", session });
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (isSessionRequiredError(error)) {
          dispatchAuthentication({ type: "SESSION_MISSING" });
          return;
        }
        dispatchAuthentication({
          type: "DISCOVERY_FAILED",
          message: "The local session could not be restored. You can retry or sign in again.",
        });
      });
  }, []);

  useEffect(() => {
    if (route === "landing" || authentication.status === "authenticated") {
      return;
    }
    const controller = new AbortController();
    discoverSession(controller.signal);
    return () => controller.abort();
  }, [discoverSession, route]);

  useEffect(() => {
    const syncRouteFromHistory = () =>
      setRoute(routeForPath(window.location.hash || window.location.pathname));
    window.addEventListener("popstate", syncRouteFromHistory);
    window.addEventListener("hashchange", syncRouteFromHistory);
    return () => {
      window.removeEventListener("popstate", syncRouteFromHistory);
      window.removeEventListener("hashchange", syncRouteFromHistory);
    };
  }, []);

  useEffect(
    () =>
      subscribeToSessionExpiry(() => {
        cache.clear();
        setSelectedEvidence(null);
        changeRoute("login", true);
        dispatchAuthentication({ type: "SESSION_EXPIRED" });
      }),
    [cache, changeRoute],
  );

  const handleAuthenticated = useCallback(
    (session: AuthSession) => {
      cache.clear();
      setPage("Map");
      setSelectedEvidence(null);
      changeRoute("dashboard", true);
      dispatchAuthentication({ type: "SESSION_FOUND", session });
    },
    [cache, changeRoute],
  );

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch (error) {
      if (!isSessionRequiredError(error)) return;
    }
    cache.clear();
    setPage("Map");
    setSelectedEvidence(null);
    changeRoute("login", true);
    dispatchAuthentication({ type: "SIGNED_OUT" });
  }, [cache, changeRoute]);

  const dashboard =
    authentication.status === "authenticated" ? (
      <AppShell
        currentPage={page}
        onNavigate={setPage}
        actor={authentication.session.actor}
        sourceMode="AUDITED PREDICTIONS · READ-ONLY"
        onSignOut={() => void signOut()}
      >
        {page === "Map" && (
          <PredictionMapView onSelectEvidence={setSelectedEvidence} />
        )}

        {page === "Trajectories" && (
          <TrajectoryView onSelectEvidence={setSelectedEvidence} />
        )}

        {page === "Analytics" && <AnalyticsView />}

        {page === "Evidence" && (
          <CameraWorkspaceView onSelectEvidence={setSelectedEvidence} />
        )}

        <EvidenceDrawer selection={selectedEvidence} onClose={closeEvidence} />
      </AppShell>
    ) : null;

  if (route === "landing") {
    return <LandingPage onOpenDashboard={() => changeRoute("login")} />;
  }

  return (
    <SessionGate
      state={authentication}
      onAuthenticated={handleAuthenticated}
      onRetryDiscovery={() => discoverSession()}
    >
      {dashboard}
    </SessionGate>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
