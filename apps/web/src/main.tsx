import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { client, key, unwrap } from "./api";
import { Table, Json, State, Network } from "./components";
import type { components } from "./api.generated";
import "./style.css";

type RecordData = Record<string, any>;
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchInterval: 3000 } },
});
const pages = [
  "Overview",
  "Scenario runner",
  "Observation inspector",
  "Trajectory explorer",
  "Analytics",
  "Alerts and review",
  "Audit and system",
];

function App() {
  const qc = useQueryClient();
  const [page, setPage] = useState(pages[0]);
  const [actor, setActor] =
    useState<components["schemas"]["Role"]>("administrator");
  const [password, setPassword] = useState("");
  const [runId, setRunId] = useState("");
  const [scenario, setScenario] = useState("normal_journey");
  const [plate, setPlate] = useState("ZZ01AA0001");
  const [start, setStart] = useState("2026-01-15T08:00:00Z");
  const [end, setEnd] = useState("2026-01-15T09:00:00Z");
  const [selected, setSelected] = useState("");
  const [journey, setJourney] = useState<RecordData | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("Synthetic scenario review");
  const [classification, setClassification] = useState<
    "true" | "false" | "uncertain"
  >("uncertain");
  const [reviewStatus, setReviewStatus] = useState<
    "accepted" | "review_required" | "rejected"
  >("review_required");
  const [includeReview, setIncludeReview] = useState(false);
  const me = useQuery({
    queryKey: ["me"],
    queryFn: async () =>
      unwrap(await client.GET("/v1/auth/me")).data as RecordData,
  });
  const loggedIn = !!me.data;
  const runs = useQuery({
    queryKey: ["runs"],
    enabled: loggedIn,
    queryFn: async () =>
      unwrap(await client.GET("/v1/demo/runs")).data as RecordData[],
  });
  const manifest = useQuery({
    queryKey: ["manifest"],
    enabled: loggedIn,
    queryFn: async () =>
      unwrap(await client.GET("/v1/demo/scenarios")).data as RecordData,
  });
  const cameras = useQuery({
    queryKey: ["cameras"],
    enabled: loggedIn,
    queryFn: async () =>
      unwrap(await client.GET("/v1/cameras")).data as RecordData[],
  });
  const graph = useQuery({
    queryKey: ["graph"],
    enabled: loggedIn,
    queryFn: async () =>
      unwrap(await client.GET("/v1/graph")).data as RecordData,
  });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () =>
      unwrap(await client.GET("/v1/health/ready")).data as RecordData,
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
    enabled:
      loggedIn &&
      !!runId &&
      ["Observation inspector", "Alerts and review"].includes(page),
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/observations", {
          params: { query: { run_id: runId, start, end } },
        }),
      ).data as RecordData,
  });
  const detail = useQuery({
    queryKey: ["detail", selected],
    enabled: !!selected && loggedIn,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/observations/{observation_id}", {
          params: { path: { observation_id: selected } },
        }),
      ).data as RecordData,
  });
  const alerts = useQuery({
    queryKey: ["alerts", runId],
    enabled: loggedIn && !!runId && page === "Alerts and review",
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/alerts", {
          params: { query: { run_id: runId } },
        }),
      ).data as RecordData[],
  });
  const watches = useQuery({
    queryKey: ["watches", runId],
    enabled: loggedIn && !!runId && page === "Alerts and review",
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/watchlists", {
          params: { query: { run_id: runId } },
        }),
      ).data as RecordData[],
  });
  const audit = useQuery({
    queryKey: ["audit", runId],
    enabled: loggedIn && !!runId && page === "Audit and system",
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/audit", { params: { query: { run_id: runId } } }),
      ).data as RecordData[],
  });
  const jobs = useQuery({
    queryKey: ["jobs", runId],
    enabled: loggedIn && !!runId && page === "Audit and system",
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/jobs", { params: { query: { run_id: runId } } }),
      ).data as RecordData[],
  });
  async function action(work: () => Promise<unknown>) {
    setBusy(true);
    setMessage("");
    try {
      await work();
      await qc.invalidateQueries();
      setMessage("Backend operation completed.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  function chooseRun(id: string) {
    setRunId(id);
    setSelected("");
    setJourney(null);
  }
  const m = metrics.data;
  return (
    <>
      <header>
        <div>
          <strong>RoadEye</strong>
          <span>Engineering console · SIH2026172</span>
        </div>
        <span className="synthetic">SYNTHETIC INPUT · MOCK OCR CANDIDATES</span>
      </header>
      {!loggedIn ? (
        <main className="login">
          <h1>Local demonstration sign in</h1>
          <p>
            Processing and persistence are real. Recognition accuracy is
            unmeasured.
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
                {["administrator", "investigator", "viewer", "approver"].map(
                  (a) => (
                    <option key={a}>{a}</option>
                  ),
                )}
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
            Use the local password from your ignored .env file. Each actor has
            separate server-enforced permissions.
          </p>
          <State query={health} />
        </main>
      ) : (
        <div className="layout">
          <aside>
            <nav aria-label="Console views">
              {pages.map((p) => (
                <button
                  key={p}
                  className={page === p ? "active" : ""}
                  onClick={() => setPage(p)}
                >
                  {p}
                </button>
              ))}
            </nav>
            <p>
              Actor: <b>{me.data.actor}</b>
            </p>
            <button
              onClick={() =>
                action(async () => {
                  unwrap(await client.POST("/v1/auth/logout"));
                  qc.clear();
                })
              }
            >
              Sign out / switch actor
            </button>
            <p className="meta">
              Fictional network · no real vehicle attribution · no live feeds
            </p>
          </aside>
          <main>
            <div className="scope">
              <label>
                Selected run
                <select
                  aria-label="Selected run"
                  value={runId}
                  onChange={(e) => chooseRun(e.target.value)}
                >
                  <option value="">Choose a run</option>
                  {runs.data?.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.scenario} · {r.id.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                UTC window start
                <input
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                />
              </label>
              <label>
                UTC window end
                <input value={end} onChange={(e) => setEnd(e.target.value)} />
              </label>
            </div>
            <h1>{page}</h1>
            <p className="meta">
              Half-open capture-time window · Historical synthetic replay ·{" "}
              {runId
                ? `Run ${runId}`
                : "Select or create a run to inspect results."}
            </p>
            <p
              role="status"
              className={
                message.includes("failed") || message.includes("denied")
                  ? "error"
                  : ""
              }
            >
              {busy ? "Waiting for backend…" : message}
            </p>
            {page === "Scenario runner" && (
              <>
                <h2>Run deterministic inputs</h2>
                <State query={manifest} />
                <label>
                  Scenario
                  <select
                    aria-label="Scenario"
                    value={scenario}
                    onChange={(e) => setScenario(e.target.value)}
                  >
                    {Object.keys(manifest.data?.scenarios || {}).map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  disabled={busy}
                  onClick={() =>
                    action(async () => {
                      const created = unwrap(
                        await client.POST("/v1/demo/runs", {
                          params: { header: key() },
                          body: { scenario },
                        }),
                      ).data as RecordData;
                      chooseRun(created.id);
                    })
                  }
                >
                  Create run
                </button>
                <p>
                  Creation stores a paused run. Play delivers fixed events; the
                  separate worker processes durable jobs. Pause stops delivery,
                  while received work drains.
                </p>
                {runId && (
                  <div className="controls">
                    {(
                      ["play", "pause", "step", "replay", "retry"] as const
                    ).map((a) => (
                      <button
                        key={a}
                        disabled={busy}
                        onClick={() =>
                          action(async () =>
                            unwrap(
                              await client.POST(
                                "/v1/demo/runs/{run_id}/control",
                                {
                                  params: {
                                    path: { run_id: runId },
                                    header: key(),
                                  },
                                  body: { action: a },
                                },
                              ),
                            ),
                          )
                        }
                      >
                        {a}
                      </button>
                    ))}
                  </div>
                )}
                {runId && <State query={run} />}
                {run.data && (
                  <>
                    <Table
                      rows={[run.data]}
                      columns={[
                        "scenario",
                        "state",
                        "cursor",
                        "total_events",
                        "version",
                        "jobs",
                        "clock",
                      ]}
                    />
                    <p>
                      Replay redelivers original event IDs into this run; counts
                      should remain unchanged. Create a new run for a clean
                      reset.
                    </p>
                  </>
                )}
              </>
            )}
            {page === "Overview" && (
              <>
                <State query={health} />
                <Table rows={health.data ? [health.data] : []} />
                {runId && (
                  <>
                    <State query={run} />
                    <Table
                      rows={run.data ? [run.data] : []}
                      columns={[
                        "source_mode",
                        "scenario",
                        "state",
                        "jobs",
                        "version",
                        "processing_lag_seconds",
                        "clock",
                      ]}
                    />
                    <State query={metrics} />
                    {m && (
                      <>
                        <Table
                          rows={[m]}
                          columns={[
                            "vehicle_passages",
                            "accepted_plates",
                            "recognition_coverage",
                            "review_required",
                            "rejected",
                            "ocr_pending",
                          ]}
                        />
                        <h2>Camera coverage</h2>
                        <Table rows={m.camera_health} />
                      </>
                    )}
                  </>
                )}
                <Network
                  cameras={cameras.data || []}
                  edges={graph.data?.edges || []}
                />
              </>
            )}
            {page === "Observation inspector" && runId && (
              <>
                <State query={observations} />
                <Table
                  rows={observations.data?.items}
                  columns={[
                    "id",
                    "camera_id",
                    "captured_at",
                    "plate",
                    "status",
                    "score",
                    "inference_origin",
                  ]}
                />
                <label>
                  Inspect observation
                  <select
                    value={selected}
                    onChange={(e) => setSelected(e.target.value)}
                  >
                    <option value="">Choose an observation</option>
                    {observations.data?.items.map((o: RecordData) => (
                      <option key={o.id} value={o.id}>
                        {o.camera_id} · {o.plate || "unreadable"} ·{" "}
                        {o.id.slice(0, 8)}
                      </option>
                    ))}
                  </select>
                </label>
                {selected && (
                  <>
                    <State query={detail} />
                    {detail.data && (
                      <>
                        <h2>Machine decision: {detail.data.status}</h2>
                        <p>
                          Reasons: {detail.data.machine.reasons.join(", ")} ·
                          Policy: {detail.data.policy}
                        </p>
                        <p>
                          Score: {detail.data.machine.score} — heuristic, not
                          accuracy.
                        </p>
                        <Table rows={detail.data.machine.contributions} />
                        <a
                          target="_blank"
                          rel="noreferrer"
                          href={`/v1/evidence/${detail.data.passage.evidence_id}`}
                        >
                          Open supporting synthetic evidence
                        </a>
                        <img
                          className="evidence"
                          alt="Synthetic evidence illustration; candidates supplied separately"
                          src={`/v1/evidence/${detail.data.passage.evidence_id}`}
                        />
                        <Json
                          value={detail.data.original_input}
                          label="Original input, receipt time and provenance"
                        />
                        <Json
                          value={detail.data.revisions}
                          label="Append-only review revisions"
                        />
                      </>
                    )}
                  </>
                )}
              </>
            )}
            {page === "Trajectory explorer" && runId && (
              <>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    action(async () =>
                      setJourney(
                        unwrap(
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
                        ).data as RecordData,
                      ),
                    );
                  }}
                >
                  <label>
                    Plate query
                    <input
                      value={plate}
                      onChange={(e) => setPlate(e.target.value)}
                    />
                  </label>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={includeReview}
                      onChange={(e) => setIncludeReview(e.target.checked)}
                    />
                    Include review candidates
                  </label>
                  <button disabled={busy}>Reconstruct journey</button>
                </form>
                {journey ? (
                  <>
                    <p
                      className={
                        run.data?.version !== journey.result_version
                          ? "error"
                          : "meta"
                      }
                    >
                      Result version {journey.result_version} ·{" "}
                      {run.data?.version !== journey.result_version
                        ? "STALE — run changed; query again"
                        : "Current run version"}{" "}
                      · {journey.scoring_policy}
                    </p>
                    <Network
                      cameras={cameras.data || []}
                      edges={run.data?.graph || []}
                      links={journey.inferred_links}
                      nodes={journey.observed_nodes}
                    />
                    <h2>Observed camera sightings</h2>
                    <Table
                      rows={journey.observed_nodes}
                      columns={[
                        "camera_id",
                        "captured_at",
                        "plate",
                        "status",
                        "id",
                      ]}
                    />
                    {journey.observed_nodes.map((o: RecordData) => (
                      <a
                        className="evidence-link"
                        key={o.id}
                        target="_blank"
                        href={`/v1/evidence/${o.evidence_id}`}
                      >
                        Evidence at {o.camera_id}
                      </a>
                    ))}
                    <h2>Inferred links</h2>
                    <Table
                      rows={journey.inferred_links}
                      columns={[
                        "source",
                        "target",
                        "elapsed_seconds",
                        "status",
                        "routes",
                      ]}
                    />
                    <h2>Ambiguous alternatives</h2>
                    <Table rows={journey.alternatives} />
                    <h2>Rejected links</h2>
                    <Table
                      rows={journey.rejected_links}
                      columns={[
                        "source",
                        "target",
                        "elapsed_seconds",
                        "reason",
                      ]}
                    />
                    <h2>Review candidates</h2>
                    <Table rows={journey.review_candidates} />
                    <Json
                      value={journey.missing_coverage}
                      label="Missing coverage"
                    />
                    <p>{journey.limitations}</p>
                  </>
                ) : (
                  <p className="empty">
                    Submit a query to reconstruct stored sightings.
                  </p>
                )}
              </>
            )}
            {page === "Analytics" && runId && (
              <>
                <State query={metrics} />
                {m && (
                  <>
                    <Table
                      rows={[m]}
                      columns={[
                        "vehicle_passages",
                        "accepted_plates",
                        "recognition_coverage",
                        "sample_size",
                        "status",
                        "result_version",
                      ]}
                    />
                    <h2>Observed passage counts and recognition</h2>
                    <Table rows={m.counts} />
                    <div className="bars">
                      {m.counts.map((c: RecordData) => (
                        <div key={c.camera_id}>
                          <span>
                            {c.camera_id} · {c.coverage_state}
                          </span>
                          <meter
                            min="0"
                            max={Math.max(
                              1,
                              ...m.counts.map((x: RecordData) => x.passages),
                            )}
                            value={c.passages}
                          />
                          <span>{c.passages} passages</span>
                        </div>
                      ))}
                    </div>
                    <h2>Camera flow</h2>
                    <Table rows={m.flow} />
                    <h2>Enrolled-camera origin / destination</h2>
                    <Table rows={m.od} />
                    <h2>Travel time and congestion proxy</h2>
                    <Table rows={m.travel_times} />
                    <ul>
                      {m.limitations.map((l: string) => (
                        <li key={l}>{l}</li>
                      ))}
                    </ul>
                  </>
                )}
              </>
            )}
            {page === "Alerts and review" && runId && (
              <>
                <h2>Watchlist lifecycle</h2>
                <p>
                  Create as investigator/administrator; sign in as the separate
                  approver to approve. Approval scans existing accepted
                  observations as well as future ones.
                </p>
                <label>
                  Synthetic plate
                  <input
                    value={plate}
                    onChange={(e) => setPlate(e.target.value)}
                  />
                </label>
                <label>
                  Reason / resolution notes
                  <input
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </label>
                <button
                  disabled={busy}
                  onClick={() =>
                    action(async () =>
                      unwrap(
                        await client.POST("/v1/watchlists", {
                          params: { header: key() },
                          body: {
                            run_id: runId,
                            plate,
                            reason,
                            severity: "medium",
                            valid_from: start,
                            valid_until: end,
                          },
                        }),
                      ),
                    )
                  }
                >
                  Create watchlist draft
                </button>
                <State query={watches} />
                <Table rows={watches.data} />
                {watches.data?.map((w) => (
                  <div key={w.id}>
                    {w.plate} · {w.status}{" "}
                    {(["approve", "revoke"] as const).map((a) => (
                      <button
                        key={a}
                        disabled={busy}
                        onClick={() =>
                          action(async () =>
                            unwrap(
                              await client.POST(
                                "/v1/watchlists/{watch_id}/{action}",
                                {
                                  params: {
                                    header: key(),
                                    path: { watch_id: w.id, action: a },
                                  },
                                },
                              ),
                            ),
                          )
                        }
                      >
                        {a} {w.id.slice(0, 8)}
                      </button>
                    ))}
                  </div>
                ))}
                <h2>Evidence-linked alerts</h2>
                <State query={alerts} />
                <Table rows={alerts.data} />
                <label>
                  Scenario classification
                  <select
                    value={classification}
                    onChange={(e) =>
                      setClassification(e.target.value as typeof classification)
                    }
                  >
                    {["true", "false", "uncertain"].map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </label>
                {alerts.data?.map((a) => (
                  <div key={a.id}>
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(async () =>
                          unwrap(
                            await client.POST(
                              "/v1/alerts/{alert_id}/acknowledge",
                              {
                                params: {
                                  path: { alert_id: a.id },
                                  header: key(),
                                },
                                body: { classification, notes: reason },
                              },
                            ),
                          ),
                        )
                      }
                    >
                      Acknowledge {a.kind}
                    </button>
                    {a.evidence_id && (
                      <a target="_blank" href={`/v1/evidence/${a.evidence_id}`}>
                        Supporting evidence
                      </a>
                    )}
                  </div>
                ))}
                <h2>Observation review</h2>
                <State query={observations} />
                <label>
                  Observation
                  <select
                    value={selected}
                    onChange={(e) => setSelected(e.target.value)}
                  >
                    <option value="">Choose observation</option>
                    {observations.data?.items.map((o: RecordData) => (
                      <option key={o.id} value={o.id}>
                        {o.camera_id} · {o.plate} · {o.status}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Revised status
                  <select
                    value={reviewStatus}
                    onChange={(e) =>
                      setReviewStatus(e.target.value as typeof reviewStatus)
                    }
                  >
                    {["accepted", "review_required", "rejected"].map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <button
                  disabled={busy || !selected}
                  onClick={() =>
                    action(async () =>
                      unwrap(
                        await client.POST(
                          "/v1/observations/{observation_id}/reviews",
                          {
                            params: {
                              path: { observation_id: selected },
                              header: key(),
                            },
                            body: {
                              plate: reviewStatus === "rejected" ? null : plate,
                              status: reviewStatus,
                              reason,
                            },
                          },
                        ),
                      ),
                    )
                  }
                >
                  Save review revision
                </button>
              </>
            )}
            {page === "Audit and system" && runId && (
              <>
                <h2>Durable worker jobs</h2>
                <State query={jobs} />
                <Table
                  rows={jobs.data}
                  columns={[
                    "id",
                    "state",
                    "attempts",
                    "available_at",
                    "lease_until",
                    "processed_at",
                    "error",
                  ]}
                />
                <h2>Audit history</h2>
                <State query={audit} />
                <Table
                  rows={audit.data}
                  columns={[
                    "actor",
                    "operation",
                    "target",
                    "created_at",
                    "correlation_id",
                    "details",
                  ]}
                />
              </>
            )}
            {!runId && !["Scenario runner", "Overview"].includes(page) && (
              <p className="empty">
                No run selected. Create one in Scenario runner.
              </p>
            )}
          </main>
        </div>
      )}
      <footer>
        RoadEye · Bharat Electronics Limited problem statement SIH2026172 ·
        Synthetic inputs validate software behavior, not real-world recognition
        or tracking.
      </footer>
    </>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
