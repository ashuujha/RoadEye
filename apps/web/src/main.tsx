import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { client, key, unwrap } from "./api";
import { State } from "./components";
import type { components } from "./api.generated";
import "./style.css";

// Components
import { AppShell, type PageId } from "./components/AppShell";
import { EvidenceDrawer } from "./components/EvidenceDrawer";

// Workspace Views
import { OverviewView } from "./views/OverviewView";
import { CameraWorkspaceView } from "./views/CameraWorkspaceView";
import { TrajectoryView } from "./views/TrajectoryView";
import { ReviewWorkbenchView } from "./views/ReviewWorkbenchView";
import { AlertsView } from "./views/AlertsView";
import { AnalyticsView } from "./views/AnalyticsView";
import { SystemView } from "./views/SystemView";

type RecordData = Record<string, any>;

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchInterval: 3000 } },
});

function App() {
  const qc = useQueryClient();
  const [page, setPage] = useState<PageId>("Overview");
  const [actor, setActor] = useState<components["schemas"]["Role"]>("administrator");
  const [password, setPassword] = useState("");
  const [runId, setRunId] = useState("");
  const [start, setStart] = useState("2026-01-15T08:00:00Z");
  const [end, setEnd] = useState("2026-01-15T09:00:00Z");
  const [selectedObsId, setSelectedObsId] = useState<string | null>(null);
  const [journey, setJourney] = useState<RecordData | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  // Authentication query
  const me = useQuery({
    queryKey: ["me"],
    queryFn: async () => unwrap(await client.GET("/v1/auth/me")).data as RecordData,
  });
  const loggedIn = !!me.data;

  // Domain queries
  const runs = useQuery({
    queryKey: ["runs"],
    enabled: loggedIn,
    queryFn: async () => unwrap(await client.GET("/v1/demo/runs")).data as RecordData[],
  });

  const manifest = useQuery({
    queryKey: ["manifest"],
    enabled: loggedIn,
    queryFn: async () => unwrap(await client.GET("/v1/demo/scenarios")).data as RecordData,
  });

  const cameras = useQuery({
    queryKey: ["cameras"],
    enabled: loggedIn,
    queryFn: async () => unwrap(await client.GET("/v1/cameras")).data as RecordData[],
  });

  const graph = useQuery({
    queryKey: ["graph"],
    enabled: loggedIn,
    queryFn: async () => unwrap(await client.GET("/v1/graph")).data as RecordData,
  });

  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () => unwrap(await client.GET("/v1/health/ready")).data as RecordData,
  });

  const run = useQuery({
    queryKey: ["run", runId],
    enabled: loggedIn && !!runId,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/demo/runs/{run_id}", {
          params: { path: { run_id: runId } },
        }),
      ).data as RecordData,
  });

  const metrics = useQuery({
    queryKey: ["metrics", runId, start, end],
    enabled: loggedIn && !!runId,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/analytics/{metric}", {
          params: {
            path: { metric: "summary" },
            query: { run_id: runId, start, end },
          },
        }),
      ).data as RecordData,
  });

  const observations = useQuery({
    queryKey: ["observations", runId, start, end],
    enabled: loggedIn && !!runId,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/observations", {
          params: { query: { run_id: runId, start, end } },
        }),
      ).data as RecordData,
  });

  const alerts = useQuery({
    queryKey: ["alerts", runId],
    enabled: loggedIn && !!runId,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/alerts", {
          params: { query: { run_id: runId } },
        }),
      ).data as RecordData[],
  });

  const watches = useQuery({
    queryKey: ["watches", runId],
    enabled: loggedIn && !!runId,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/watchlists", {
          params: { query: { run_id: runId } },
        }),
      ).data as RecordData[],
  });

  const audit = useQuery({
    queryKey: ["audit", runId],
    enabled: loggedIn && !!runId,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/audit", { params: { query: { run_id: runId } } }),
      ).data as RecordData[],
  });

  const jobs = useQuery({
    queryKey: ["jobs", runId],
    enabled: loggedIn && !!runId,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/jobs", { params: { query: { run_id: runId } } }),
      ).data as RecordData[],
  });

  // Action wrapper with error tracking and query invalidation
  async function action(work: () => Promise<unknown>) {
    setBusy(true);
    setMessage("");
    try {
      await work();
      await qc.invalidateQueries();
      setMessage("Backend operation completed successfully.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  // Trajectory Query Handler
  async function handleQueryTrajectory({ plate, includeReview }: { plate: string; includeReview: boolean }) {
    if (!runId) {
      setMessage("Please choose an execution run before querying trajectories.");
      return;
    }
    await action(async () => {
      const res = unwrap(
        await client.POST("/v1/trajectories", {
          body: {
            run_id: runId,
            start,
            end,
            plate,
            include_review: includeReview,
            limit: 100,
          },
        }),
      ).data as RecordData;
      setJourney(res);
    });
  }

  // Review Workbench Handler
  async function handleSubmitReview(
    obsId: string,
    rev: { status: string; plate: string | null; reason: string },
  ) {
    await action(async () => {
      unwrap(
        await client.POST("/v1/observations/{observation_id}/reviews", {
          params: {
            path: { observation_id: obsId },
            header: key(),
          },
          body: {
            plate: rev.status === "rejected" ? null : rev.plate,
            status: rev.status as any,
            reason: rev.reason,
          },
        }),
      );
    });
  }

  // Alert Acknowledgment Handler
  async function handleAcknowledgeAlert(
    alertId: string,
    classification: string,
    notes: string,
  ) {
    await action(async () => {
      unwrap(
        await client.POST("/v1/alerts/{alert_id}/acknowledge", {
          params: {
            path: { alert_id: alertId },
            header: key(),
          },
          body: {
            classification: classification as any,
            notes,
          },
        }),
      );
    });
  }

  // Watchlist Creation Handler
  async function handleCreateWatchlist(watch: {
    plate: string;
    reason: string;
    severity: string;
    start: string;
    end: string;
  }) {
    if (!runId) return;
    await action(async () => {
      unwrap(
        await client.POST("/v1/watchlists", {
          params: { header: key() },
          body: {
            run_id: runId,
            plate: watch.plate,
            reason: watch.reason,
            severity: watch.severity as any,
            valid_from: watch.start,
            valid_until: watch.end,
          },
        }),
      );
    });
  }

  // Watchlist Action Handler
  async function handleWatchlistAction(watchId: string, actionName: "approve" | "revoke") {
    await action(async () => {
      unwrap(
        await client.POST("/v1/watchlists/{watch_id}/{action}", {
          params: {
            header: key(),
            path: { watch_id: watchId, action: actionName },
          },
        }),
      );
    });
  }

  // Scenario Runner Handlers
  async function handleCreateRun(scenario: string) {
    await action(async () => {
      const created = unwrap(
        await client.POST("/v1/demo/runs", {
          params: { header: key() },
          body: { scenario },
        }),
      ).data as RecordData;
      setRunId(created.id);
      setJourney(null);
    });
  }

  async function handleControlRun(actionName: "play" | "pause" | "step" | "replay" | "retry") {
    if (!runId) return;
    await action(async () => {
      unwrap(
        await client.POST("/v1/demo/runs/{run_id}/control", {
          params: {
            path: { run_id: runId },
            header: key(),
          },
          body: { action: actionName },
        }),
      );
    });
  }

  // Auto-select first run if none selected
  if (loggedIn && !runId && runs.data && runs.data.length > 0) {
    setRunId(runs.data[0].id);
  }

  /* =========================================================================
     1. UNMODIFIED LOGIN PAGE (Explicitly Preserved & Out of Scope)
     ========================================================================= */
  if (!loggedIn) {
    return (
      <>
        <header className="login-header">
          <div>
            <strong>RoadEye</strong>
            <span>Engineering console · SIH2026172</span>
          </div>
          <span className="synthetic-banner-unauth">
            SYNTHETIC INPUT · MOCK OCR CANDIDATES
          </span>
        </header>

        <main className="login">
          <h1>Local demonstration sign in</h1>
          <p>
            Processing and persistence are real. Recognition accuracy is unmeasured.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              action(async () => {
                unwrap(
                  await client.POST("/v1/auth/login", {
                    body: { actor, password },
                  }),
                );
                setPassword("");
              });
            }}
          >
            <label>
              Local actor
              <select
                value={actor}
                onChange={(e) => setActor(e.target.value as typeof actor)}
              >
                {["administrator", "investigator", "viewer", "approver"].map((a) => (
                  <option key={a}>{a}</option>
                ))}
              </select>
            </label>

            <label>
              Local password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>

            <button disabled={busy}>Sign in</button>
          </form>

          <p role="alert">{message}</p>
          <p>
            Use the local password from your ignored .env file. Each actor has separate
            server-enforced permissions.
          </p>
          <State query={health} />
        </main>
      </>
    );
  }

  /* =========================================================================
     2. AUTHENTICATED ROADEYE AFTERGLOW OPERATIONS WORKSPACE
     ========================================================================= */
  const pendingReviewCount = metrics.data?.review_required || 0;
  const pendingAlertsCount = alerts.data?.filter((a) => a.status === "new" || a.status === "pending").length || 0;
  const sourceModeLabel = page === "Cameras"
    ? "RECORDED FOOTAGE · REAL MODEL INFERENCE"
    : "SYNTHETIC INPUT · MOCK OCR";

  return (
    <AppShell
      currentPage={page}
      onNavigate={(p) => setPage(p)}
      actor={me.data.actor}
      sourceMode={sourceModeLabel}
      pendingReviewCount={pendingReviewCount}
      pendingAlertsCount={pendingAlertsCount}
      onSignOut={() =>
        action(async () => {
          unwrap(await client.POST("/v1/auth/logout"));
          qc.clear();
        })
      }
    >
      {/* 1. Overview Workspace */}
      {page === "Overview" && (
        <OverviewView
          runId={runId}
          onRunChange={(id) => {
            setRunId(id);
            setJourney(null);
          }}
          runs={runs.data || []}
          start={start}
          end={end}
          onStartChange={setStart}
          onEndChange={setEnd}
          cameras={cameras.data || []}
          graphEdges={graph.data?.edges || []}
          healthData={health.data}
          runData={run.data}
          metricsData={metrics.data}
          observationsData={observations.data}
          alertsData={alerts.data || []}
          onSelectObservation={(id) => setSelectedObsId(id)}
          onNavigate={(p) => setPage(p)}
          isFetching={observations.isFetching}
        />
      )}

      {/* 2. Cameras & Recorded Video Workspace */}
      {page === "Cameras" && (
        <CameraWorkspaceView
          actor={me.data.actor}
          cameras={cameras.data || []}
          onSelectObservation={(id) => setSelectedObsId(id)}
        />
      )}

      {/* 3. Vehicles & Trajectory Explorer */}
      {page === "Vehicles" && (
        <TrajectoryView
          runId={runId}
          start={start}
          end={end}
          cameras={cameras.data || []}
          graphEdges={graph.data?.edges || []}
          journeyData={journey}
          onQueryTrajectory={handleQueryTrajectory}
          onSelectObservation={(id) => setSelectedObsId(id)}
          busy={busy}
          message={message}
        />
      )}

      {/* 4. Analytics Workspace */}
      {page === "Analytics" && (
        <AnalyticsView
          runId={runId}
          metricsData={metrics.data}
        />
      )}

      {/* 5. Alerts & Watchlists Workspace */}
      {page === "Alerts" && (
        <AlertsView
          runId={runId}
          actor={me.data.actor}
          alerts={alerts.data || []}
          watchlists={watches.data || []}
          onAcknowledgeAlert={handleAcknowledgeAlert}
          onCreateWatchlist={handleCreateWatchlist}
          onWatchlistAction={handleWatchlistAction}
          onSelectObservation={(id) => setSelectedObsId(id)}
          busy={busy}
          message={message}
        />
      )}

      {/* 6. Review Workbench */}
      {page === "Review" && (
        <ReviewWorkbenchView
          runId={runId}
          observations={observations.data?.items || []}
          onSelectObservation={(id) => setSelectedObsId(id)}
          onSubmitReview={handleSubmitReview}
          busy={busy}
          message={message}
        />
      )}

      {/* 7. System, Audit & Scenario Runner (Utility Pages) */}
      {(page === "System" || page === "Audit" || page === "Scenario runner") && (
        <SystemView
          initialSubTab={page === "Audit" ? "audit" : page === "Scenario runner" ? "runner" : "system"}
          healthData={health.data}
          jobsData={jobs.data || []}
          auditData={audit.data || []}
          manifestData={manifest.data}
          runData={run.data}
          runId={runId}
          onChooseRun={(id) => {
            setRunId(id);
            setJourney(null);
          }}
          onCreateRun={handleCreateRun}
          onControlRun={handleControlRun}
          busy={busy}
          message={message}
        />
      )}

      {/* Reusable Evidence Drawer (Accessible from any observation) */}
      <EvidenceDrawer
        observationId={selectedObsId}
        onClose={() => setSelectedObsId(null)}
        onOpenReview={(id) => {
          setSelectedObsId(null);
          setPage("Review");
        }}
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
