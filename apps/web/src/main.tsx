import React, { useCallback, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";

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

function App() {
  const [page, setPage] = useState<PageId>("Map");
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceSelection | null>(null);
  const closeEvidence = useCallback(() => setSelectedEvidence(null), []);

  return (
    <AppShell
      currentPage={page}
      onNavigate={setPage}
      sourceMode="AUDITED PREDICTIONS · READ-ONLY"
    >
      {page === "Map" && <PredictionMapView onSelectEvidence={setSelectedEvidence} />}

      {page === "Trajectories" && <TrajectoryView onSelectEvidence={setSelectedEvidence} />}

      {page === "Analytics" && <AnalyticsView />}

      {page === "Evidence" && (
        <CameraWorkspaceView onSelectEvidence={setSelectedEvidence} />
      )}

      <EvidenceDrawer
        selection={selectedEvidence}
        onClose={closeEvidence}
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
