import React from "react";
import { NetworkMap } from "../components/NetworkMap";
import { MetricStrip } from "../components/MetricStrip";
import { ScopeBar } from "../components/ScopeBar";
import { StatusBadge } from "../components/StatusBadge";
import { IconSearch, IconReview, IconClock, IconCamera } from "../components/Icons";

type RecordData = Record<string, any>;

interface OverviewViewProps {
  runId: string;
  onRunChange: (id: string) => void;
  runs: RecordData[];
  start: string;
  end: string;
  onStartChange: (s: string) => void;
  onEndChange: (e: string) => void;
  cameras: RecordData[];
  graphEdges: RecordData[];
  healthData?: RecordData;
  runData?: RecordData;
  metricsData?: RecordData;
  observationsData?: RecordData;
  alertsData?: RecordData[];
  onSelectObservation: (obsId: string) => void;
  onNavigate: (page: any) => void;
  isFetching?: boolean;
}

export function OverviewView({
  runId,
  onRunChange,
  runs,
  start,
  end,
  onStartChange,
  onEndChange,
  cameras,
  graphEdges,
  healthData,
  runData,
  metricsData,
  observationsData,
  alertsData = [],
  onSelectObservation,
  onNavigate,
  isFetching,
}: OverviewViewProps) {
  const m = metricsData;
  const obsList: RecordData[] = observationsData?.items || [];
  const pendingAlerts = alertsData.filter((a) => a.status === "new" || a.status === "pending").length;

  return (
    <div className="view-container overview-view">
      {/* Title bar with primary actions */}
      <div className="view-header">
        <div>
          <h1 className="view-title">Traffic Overview</h1>
          <p className="view-subtitle">
            Real-time multi-camera ANPR observations, network camera topology, and evidence activity.
          </p>
        </div>

        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => onNavigate("Review")}>
            <IconReview size={16} />
            <span>Review Queue</span>
            {m?.review_required ? <span className="action-pill">{m.review_required}</span> : null}
          </button>
          <button className="btn btn-primary" onClick={() => onNavigate("Vehicles")}>
            <IconSearch size={16} />
            <span>Search Vehicle</span>
          </button>
        </div>
      </div>

      {/* Scope Bar */}
      <ScopeBar
        runId={runId}
        onRunChange={onRunChange}
        runs={runs}
        start={start}
        end={end}
        onStartChange={onStartChange}
        onEndChange={onEndChange}
        cameras={cameras}
        sourceMode={runData?.source_mode ? `SOURCE: ${runData.source_mode.toUpperCase()}` : undefined}
        lastUpdated={Date.now()}
        isFetching={isFetching}
      />

      {/* 4-Cell Metric Strip */}
      <MetricStrip
        acceptedCount={m?.accepted_plates}
        reviewCount={m?.review_required}
        sourcesInScope={{ active: cameras.length, total: cameras.length }}
        pendingAlerts={pendingAlerts}
      />

      {/* 70/30 Split: Network Map & Evidence Activity Rail */}
      <div className="overview-split">
        {/* Left 70%: Network / GIS Panel */}
        <div className="split-main">
          <div className="panel panel-map">
            <NetworkMap
              cameras={cameras}
              edges={graphEdges}
              nodes={obsList.slice(0, 10).map((o) => ({ camera_id: o.camera_id, id: o.id }))}
              onSelectNode={(id) => onSelectObservation(id)}
              height={380}
            />
          </div>
        </div>

        {/* Right 30%: Evidence Activity Rail */}
        <div className="split-rail">
          <div className="panel panel-rail">
            <div className="rail-header">
              <div className="rail-title-group">
                <span className="live-indicator-dot" />
                <h3 className="rail-title">Recent Evidence</h3>
              </div>
              <span className="rail-count">{obsList.length} records</span>
            </div>

            <div className="rail-list">
              {obsList.length === 0 ? (
                <div className="rail-empty">
                  <span>No recent observations in this scope.</span>
                  <small>Select or play a run to inspect crops.</small>
                </div>
              ) : (
                obsList.slice(0, 8).map((obs) => (
                  <div
                    key={obs.id}
                    className="rail-item"
                    onClick={() => onSelectObservation(obs.id)}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="rail-thumb-wrapper">
                      {obs.evidence_id || obs.passage_id ? (
                        <img
                          src={`/v1/evidence/${obs.evidence_id || obs.passage_id}`}
                          alt="Plate crop"
                          className="rail-thumb"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <div className="thumb-fallback">
                          <IconCamera size={14} />
                        </div>
                      )}
                    </div>

                    <div className="rail-info">
                      <div className="rail-top-row">
                        <span className="plate-text mono font-semibold">
                          {obs.plate || "Unreadable"}
                        </span>
                        <StatusBadge status={obs.status} size="sm" />
                      </div>
                      <div className="rail-bottom-row">
                        <span className="rail-cam">{obs.camera_id}</span>
                        <span className="rail-time mono">
                          {obs.captured_at ? new Date(obs.captured_at).toLocaleTimeString() : ""}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Dock: Traffic Volume & Source Health */}
      <div className="dock-grid">
        {/* Traffic Activity (Volume by Camera) */}
        <div className="panel dock-panel">
          <h3 className="panel-title">Traffic Activity (Passage Volume)</h3>
          {m?.counts && m.counts.length > 0 ? (
            <div className="volume-bars">
              {m.counts.map((c: RecordData) => {
                const maxPassages = Math.max(1, ...m.counts.map((x: RecordData) => x.passages || 0));
                const pct = Math.round(((c.passages || 0) / maxPassages) * 100);

                return (
                  <div key={c.camera_id} className="volume-row">
                    <span className="volume-cam mono">{c.camera_id}</span>
                    <div className="volume-bar-bg">
                      <div className="volume-bar-fill" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="volume-val mono">{c.passages || 0} passages</span>
                    <StatusBadge status={c.coverage_state || "observed"} size="sm" />
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="empty-text">No traffic counts recorded for the selected window.</p>
          )}
        </div>

        {/* Source Health & Worker Queues */}
        <div className="panel dock-panel">
          <h3 className="panel-title">Source Health & Processing Pipeline</h3>
          <div className="health-metrics">
            <div className="health-row">
              <span className="health-label">Database & PostGIS</span>
              <StatusBadge status={healthData?.status === "ready" ? "done" : "error"} label={healthData?.status || "offline"} size="sm" />
            </div>
            <div className="health-row">
              <span className="health-label">PostGIS Version</span>
              <span className="mono text-xs text-muted">{healthData?.postgis || "N/A"}</span>
            </div>
            <div className="health-row">
              <span className="health-label">Run Execution State</span>
              <StatusBadge status={runData?.state || "idle"} size="sm" />
            </div>
            <div className="health-row">
              <span className="health-label">Active Worker Jobs</span>
              <span className="mono text-xs">
                {runData?.jobs ? Object.entries(runData.jobs).map(([k, v]) => `${k}: ${v}`).join(" · ") : "No pending jobs"}
              </span>
            </div>
            <div className="health-row">
              <span className="health-label">Processing Lag</span>
              <span className="mono text-xs">
                {runData?.processing_lag_seconds !== undefined
                  ? `${runData.processing_lag_seconds.toFixed(2)}s`
                  : "0s"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Observations Table */}
      <div className="panel table-panel">
        <div className="table-header-group">
          <h3 className="panel-title">Recent In-Scope Observations</h3>
          <span className="table-meta">Click any observation to open the verified evidence drawer.</span>
        </div>

        {obsList.length === 0 ? (
          <div className="empty-state">
            <p>No observations recorded in this time scope. Select or start a run above.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time (UTC)</th>
                  <th>Camera</th>
                  <th>Normalized Plate</th>
                  <th>Decision Status</th>
                  <th>Consensus Score</th>
                  <th>Inference Origin</th>
                  <th>Evidence Action</th>
                </tr>
              </thead>
              <tbody>
                {obsList.slice(0, 15).map((o) => (
                  <tr key={o.id} onClick={() => onSelectObservation(o.id)} style={{ cursor: "pointer" }}>
                    <td className="mono text-xs">
                      {o.captured_at ? new Date(o.captured_at).toISOString().replace("T", " ").slice(0, 19) : "—"}
                    </td>
                    <td className="font-semibold">{o.camera_id}</td>
                    <td className="mono font-bold text-copper">{o.plate || "Unreadable"}</td>
                    <td>
                      <StatusBadge status={o.status} size="sm" />
                    </td>
                    <td className="mono text-xs">
                      {typeof o.score === "number" ? o.score.toFixed(3) : "—"}
                    </td>
                    <td className="text-xs text-muted">{o.inference_origin || "worker_onnx"}</td>
                    <td>
                      <button
                        className="btn btn-secondary btn-xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectObservation(o.id);
                        }}
                      >
                        Inspect Crop
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
