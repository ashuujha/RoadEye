import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";

import { AppShell, type PageId } from "./components/AppShell";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { NetworkMap } from "./components/NetworkMap";
import { AnalyticsView } from "./views/AnalyticsView";
import { CameraWorkspaceView } from "./views/CameraWorkspaceView";
import { TrajectoryView } from "./views/TrajectoryView";
import "./style.css";

type RecordData = Record<string, unknown>;

const emptyRecords: RecordData[] = [];

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

async function pendingTrajectorySearch(): Promise<void> {
  // TrajectoryView is remapped to the audited read-only client in step 6.4.
}

function App() {
  const [page, setPage] = useState<PageId>("Map");
  const [selectedObservationId, setSelectedObservationId] = useState<string | null>(null);

  return (
    <AppShell
      currentPage={page}
      onNavigate={setPage}
      sourceMode="AUDITED PREDICTIONS · READ-ONLY"
    >
      {page === "Map" && (
        <div className="view-container map-view">
          <div className="view-header">
            <div>
              <h1 className="view-title">Prediction Network Map</h1>
              <p className="view-subtitle">
                Observed camera visits and explicitly labelled inferred links from the audited
                prediction artifacts.
              </p>
            </div>
          </div>
          <div className="panel map-panel">
            <NetworkMap cameras={emptyRecords} edges={emptyRecords} height={560} />
          </div>
        </div>
      )}

      {page === "Trajectories" && (
        <TrajectoryView
          runId=""
          start=""
          end=""
          cameras={emptyRecords}
          graphEdges={emptyRecords}
          journeyData={null}
          onQueryTrajectory={pendingTrajectorySearch}
          onSelectObservation={setSelectedObservationId}
          busy={false}
          message=""
        />
      )}

      {page === "Analytics" && <AnalyticsView runId="" />}

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
