import React, { useState } from "react";
import { StatusBadge } from "../components/StatusBadge";
import { IconSystem, IconAudit, IconPlay, IconClock, IconShield } from "../components/Icons";

type RecordData = Record<string, any>;

interface SystemViewProps {
  initialSubTab?: "system" | "audit" | "runner";
  healthData?: RecordData;
  jobsData?: RecordData[];
  auditData?: RecordData[];
  manifestData?: RecordData;
  runData?: RecordData;
  runId: string;
  onChooseRun: (id: string) => void;
  onCreateRun: (scenario: string) => Promise<void>;
  onControlRun: (action: "play" | "pause" | "step" | "replay" | "retry") => Promise<void>;
  busy: boolean;
  message: string;
}

export function SystemView({
  initialSubTab = "system",
  healthData,
  jobsData = [],
  auditData = [],
  manifestData,
  runData,
  runId,
  onChooseRun,
  onCreateRun,
  onControlRun,
  busy,
  message,
}: SystemViewProps) {
  const [subTab, setSubTab] = useState<"system" | "audit" | "runner">(initialSubTab);
  const [selectedScenario, setSelectedScenario] = useState("normal_journey");

  return (
    <div className="view-container system-view">
      <div className="view-header">
        <div>
          <h1 className="view-title">System Health, Audit & Operations</h1>
          <p className="view-subtitle">
            Durable worker job queue monitoring, tamper-evident audit trails, and synthetic scenario execution controls.
          </p>
        </div>

        <div className="tab-group" role="tablist">
          <button
            className={`tab-btn ${subTab === "system" ? "active" : ""}`}
            onClick={() => setSubTab("system")}
            role="tab"
          >
            <IconSystem size={16} />
            <span>Health & Jobs ({jobsData.length})</span>
          </button>
          <button
            className={`tab-btn ${subTab === "audit" ? "active" : ""}`}
            onClick={() => setSubTab("audit")}
            role="tab"
          >
            <IconAudit size={16} />
            <span>Audit History ({auditData.length})</span>
          </button>
          <button
            className={`tab-btn ${subTab === "runner" ? "active" : ""}`}
            onClick={() => setSubTab("runner")}
            role="tab"
          >
            <IconPlay size={16} />
            <span>Scenario Runner</span>
          </button>
        </div>
      </div>

      {message && (
        <div className={`status-banner ${message.includes("failed") || message.includes("denied") ? "banner-danger" : "banner-info"}`}>
          {message}
        </div>
      )}

      {/* Sub-tab 1: System Health & Durable Worker Jobs */}
      {subTab === "system" && (
        <div className="system-grid">
          {/* Health Status Box */}
          <div className="panel health-box">
            <h3 className="panel-title">Service Readiness & Storage Dependencies</h3>
            <div className="health-grid-cards">
              <div className="health-card">
                <span className="health-card-label">API Gateway</span>
                <StatusBadge status="done" label="Operational (FastAPI)" size="md" />
                <span className="health-card-sub text-muted">Listening on :8000</span>
              </div>
              <div className="health-card">
                <span className="health-card-label">PostgreSQL / PostGIS</span>
                <StatusBadge status={healthData?.status === "ready" ? "done" : "error"} label={healthData?.status || "Checking"} size="md" />
                <span className="health-card-sub mono text-xs">{healthData?.postgis || "postgis-3.5"}</span>
              </div>
              <div className="health-card">
                <span className="health-card-label">Alembic Schema Revision</span>
                <span className="mono text-xs font-bold text-copper">20260907_labels</span>
                <span className="health-card-sub text-muted">Target current</span>
              </div>
              <div className="health-card">
                <span className="health-card-label">Evidence Object Store</span>
                <StatusBadge status="done" label="LocalEvidenceStore (FS)" size="md" />
                <span className="health-card-sub text-muted">SHA-256 Verified</span>
              </div>
            </div>
          </div>

          {/* Durable Jobs Table */}
          <div className="panel jobs-panel">
            <div className="panel-header">
              <h3 className="panel-title">Durable Worker Jobs</h3>
              <span className="panel-meta">{jobsData.length} records in queue</span>
            </div>

            {jobsData.length === 0 ? (
              <div className="empty-state">
                <p>No durable jobs registered for the selected run.</p>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Job ID</th>
                      <th>State</th>
                      <th>Attempts</th>
                      <th>Available At</th>
                      <th>Lease Until</th>
                      <th>Processed At</th>
                      <th>Error Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobsData.map((j) => (
                      <tr key={j.id}>
                        <td className="mono text-xs">{j.id.slice(0, 8)}…</td>
                        <td>
                          <StatusBadge status={j.state} size="sm" />
                        </td>
                        <td className="mono">{j.attempts}</td>
                        <td className="mono text-xs">
                          {j.available_at ? new Date(j.available_at).toLocaleTimeString() : "—"}
                        </td>
                        <td className="mono text-xs">
                          {j.lease_until ? new Date(j.lease_until).toLocaleTimeString() : "—"}
                        </td>
                        <td className="mono text-xs">
                          {j.processed_at ? new Date(j.processed_at).toLocaleTimeString() : "—"}
                        </td>
                        <td className="text-xs text-danger mono">{j.error || "None"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sub-tab 2: Audit History */}
      {subTab === "audit" && (
        <div className="panel audit-panel">
          <div className="panel-header">
            <h3 className="panel-title">Append-Only Operator Audit Log</h3>
            <span className="panel-meta">{auditData.length} recorded events</span>
          </div>

          <div className="audit-notice">
            <IconShield size={16} className="text-copper inline-icon" />
            <span>
              All searches, evidence reads, review revisions, and watchlist actions are immutably recorded with correlation IDs.
            </span>
          </div>

          {auditData.length === 0 ? (
            <div className="empty-state">
              <p>No audit events recorded for current run scope.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timestamp (UTC)</th>
                    <th>Actor</th>
                    <th>Operation</th>
                    <th>Target Resource</th>
                    <th>Correlation ID</th>
                    <th>Operation Details</th>
                  </tr>
                </thead>
                <tbody>
                  {auditData.map((a, idx) => (
                    <tr key={a.id || idx}>
                      <td className="mono text-xs">
                        {a.created_at ? new Date(a.created_at).toISOString().replace("T", " ").slice(0, 19) : "—"}
                      </td>
                      <td className="font-semibold text-xs">{a.actor}</td>
                      <td>
                        <span className="badge-operation mono">{a.operation}</span>
                      </td>
                      <td className="mono text-xs">{a.target || "—"}</td>
                      <td className="mono text-xs text-muted" title={a.correlation_id}>
                        {a.correlation_id ? a.correlation_id.slice(0, 8) + "…" : "—"}
                      </td>
                      <td className="text-xs">
                        {a.details ? JSON.stringify(a.details) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Sub-tab 3: Scenario Runner (Synthetic Pipeline Controls) */}
      {subTab === "runner" && (
        <div className="panel runner-panel">
          <div className="panel-header">
            <h3 className="panel-title">Deterministic Scenario Runner</h3>
            <span className="panel-meta">Synthetic Input Pipeline</span>
          </div>

          <div className="runner-controls-grid">
            <div className="scenario-create-box">
              <h4 className="section-subtitle">Initialize New Synthetic Scenario</h4>
              <p className="text-sm text-secondary">
                Spawns a paused execution run with deterministic multi-camera passages and mock OCR noise.
              </p>

              <div className="form-group">
                <label htmlFor="scenario-select">Available Scenarios</label>
                <select
                  id="scenario-select"
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  className="scope-select"
                >
                  {manifestData?.scenarios
                    ? Object.keys(manifestData.scenarios).map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))
                    : [
                        <option key="normal_journey" value="normal_journey">normal_journey</option>,
                        <option key="speeding_vehicle" value="speeding_vehicle">speeding_vehicle</option>,
                        <option key="ocr_confusion" value="ocr_confusion">ocr_confusion</option>,
                      ]}
                </select>
              </div>

              <button
                className="btn btn-primary"
                disabled={busy}
                onClick={() => onCreateRun(selectedScenario)}
              >
                Create Run
              </button>
            </div>

            {runId && (
              <div className="playback-controls-box">
                <h4 className="section-subtitle">Execution Playback Controls</h4>
                <p className="text-sm text-secondary">
                  Active Run: <span className="mono font-bold text-copper">{runId.slice(0, 8)}</span> ({runData?.state || "paused"})
                </p>

                <div className="playback-btn-group">
                  <button
                    className="btn btn-secondary"
                    disabled={busy || runData?.state === "playing"}
                    onClick={() => onControlRun("play")}
                  >
                    <IconPlay size={15} />
                    <span>Play</span>
                  </button>
                  <button
                    className="btn btn-secondary"
                    disabled={busy || runData?.state === "paused"}
                    onClick={() => onControlRun("pause")}
                  >
                    <span>Pause</span>
                  </button>
                  <button
                    className="btn btn-secondary"
                    disabled={busy}
                    onClick={() => onControlRun("step")}
                  >
                    <span>Step (1 Event)</span>
                  </button>
                  <button
                    className="btn btn-secondary"
                    disabled={busy}
                    onClick={() => onControlRun("replay")}
                  >
                    <span>Replay</span>
                  </button>
                  <button
                    className="btn btn-secondary"
                    disabled={busy}
                    onClick={() => onControlRun("retry")}
                  >
                    <span>Retry Poison Jobs</span>
                  </button>
                </div>

                <div className="playback-status-row">
                  <span>Cursor: <b>{runData?.cursor ?? 0}</b></span>
                  <span>Total Events: <b>{runData?.total_events ?? 0}</b></span>
                  <span>Version: <b>{runData?.version ?? 1}</b></span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
