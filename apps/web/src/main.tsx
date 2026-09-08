import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";

import { AppShell, type PageId } from "./components/AppShell";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { PredictionMapView } from "./components/NetworkMap";
import { AnalyticsView } from "./views/AnalyticsView";
import { CameraWorkspaceView } from "./views/CameraWorkspaceView";
import { TrajectoryView } from "./views/TrajectoryView";
import "./style.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  const [page, setPage] = useState<PageId>("Map");
  const [selectedObservationId, setSelectedObservationId] = useState<string | null>(null);

  return (
    <AppShell
      currentPage={page}
      onNavigate={setPage}
      sourceMode="AUDITED PREDICTIONS · READ-ONLY"
    >
      {page === "Map" && <PredictionMapView />}

      {page === "Trajectories" && <TrajectoryView />}

      {page === "Analytics" && <AnalyticsView />}

      {page === "Evidence" && (
        <CameraWorkspaceView />
      )}

      <EvidenceDrawer
        observationId={selectedObservationId}
        onClose={() => setSelectedObservationId(null)}
      />
    </AppShell>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
