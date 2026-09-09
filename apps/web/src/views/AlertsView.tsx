import React, { useState } from "react";
import { StatusBadge } from "../components/StatusBadge";
import { IconAlert, IconShield, IconCheckCircle, IconClock, IconAlertTriangle } from "../components/Icons";

type RecordData = Record<string, any>;

interface AlertsViewProps {
  runId: string;
  actor: string;
  alerts: RecordData[];
  watchlists: RecordData[];
  onAcknowledgeAlert: (alertId: string, classification: string, notes: string) => Promise<void>;
  onCreateWatchlist: (watch: { plate: string; reason: string; severity: string; start: string; end: string }) => Promise<void>;
  onWatchlistAction: (watchId: string, action: "approve" | "revoke") => Promise<void>;
  onSelectObservation: (obsId: string) => void;
  busy: boolean;
  message: string;
}

export function AlertsView({
  runId,
  actor,
  alerts,
  watchlists,
  onAcknowledgeAlert,
  onCreateWatchlist,
  onWatchlistAction,
  onSelectObservation,
  busy,
  message,
}: AlertsViewProps) {
  const [activeTab, setActiveTab] = useState<"alerts" | "watchlists">("alerts");

  // Alert acknowledgment state
  const [selectedAlert, setSelectedAlert] = useState<RecordData | null>(alerts[0] || null);
  const [classification, setClassification] = useState<"true" | "false" | "uncertain">("uncertain");
  const [ackNotes, setAckNotes] = useState("Investigative assessment of optical sighting match");

  // Watchlist creation state
  const [newPlate, setNewPlate] = useState("ZZ01AA0001");
  const [newReason, setNewReason] = useState("Stolen vehicle report - Section 379 IPC");
  const [newSeverity, setNewSeverity] = useState<"low" | "medium" | "high">("high");
  const [validFrom, setValidFrom] = useState("2026-01-15T00:00:00Z");
  const [validUntil, setValidUntil] = useState("2026-01-20T23:59:59Z");

  const handleAcknowledge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAlert) return;
    await onAcknowledgeAlert(selectedAlert.id, classification, ackNotes);
  };

  const handleCreateWatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlate.trim()) return;
    await onCreateWatchlist({
      plate: newPlate.trim().toUpperCase(),
      reason: newReason,
      severity: newSeverity,
      start: validFrom,
      end: validUntil,
    });
    setNewPlate("");
  };

  return (
    <div className="view-container alerts-view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Alerts & Watchlist Operations</h1>
          <p className="view-subtitle">
            Evidence-linked alert classification, two-person watchlist governance, and optical match triage.
          </p>
        </div>

        <div className="tab-group" role="tablist">
          <button
            className={`tab-btn ${activeTab === "alerts" ? "active" : ""}`}
            onClick={() => setActiveTab("alerts")}
            role="tab"
          >
            <IconAlert size={16} />
            <span>Active Alerts ({alerts.length})</span>
          </button>
          <button
            className={`tab-btn ${activeTab === "watchlists" ? "active" : ""}`}
            onClick={() => setActiveTab("watchlists")}
            role="tab"
          >
            <IconShield size={16} />
            <span>Watchlists Governance ({watchlists.length})</span>
          </button>
        </div>
      </div>

      {message && (
        <div className={`status-banner ${message.includes("failed") || message.includes("denied") ? "banner-danger" : "banner-info"}`}>
          {message}
        </div>
      )}

      {activeTab === "alerts" ? (
        <div className="alerts-workspace-grid">
          {/* Alerts Feed (Left) */}
          <div className="panel alerts-feed-panel">
            <div className="panel-header">
              <h3 className="panel-title">Evidence-Linked Alert Feed</h3>
              <span className="panel-meta">{alerts.length} total hits</span>
            </div>

            {alerts.length === 0 ? (
              <div className="empty-state">
                <IconCheckCircle size={24} className="text-success" />
                <p>No active alerts triggered for current run window.</p>
              </div>
            ) : (
              <div className="alerts-list">
                {alerts.map((a) => (
                  <div
                    key={a.id}
                    className={`alert-card ${selectedAlert?.id === a.id ? "selected" : ""}`}
                    onClick={() => setSelectedAlert(a)}
                  >
                    <div className="alert-card-top">
                      <span className={`severity-tag severity-${a.severity || "high"}`}>
                        {a.severity || "ALERT"}
                      </span>
                      <StatusBadge status={a.status} size="sm" />
                    </div>

                    <div className="alert-card-mid">
                      <span className="mono font-bold text-copper">{a.plate || "Target Plate"}</span>
                      <span className="alert-kind text-xs text-muted">{a.kind || "watchlist_match"}</span>
                    </div>

                    <div className="alert-card-bottom">
                      <span className="text-xs">{a.camera_id}</span>
                      <span className="text-xs mono text-muted">
                        {a.created_at ? new Date(a.created_at).toLocaleTimeString() : ""}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Alert Triage & Evidence Detail (Right) */}
          <div className="panel alert-detail-panel">
            <div className="panel-header">
              <h3 className="panel-title">Alert Triage & Investigation</h3>
              {selectedAlert && <span className="mono text-xs">{selectedAlert.id.slice(0, 8)}</span>}
            </div>

            {selectedAlert ? (
              <div className="alert-detail-body">
                <div className="alert-summary-card">
                  <div className="summary-row">
                    <span className="label">Matched Plate:</span>
                    <span className="val mono font-bold text-copper">{selectedAlert.plate}</span>
                  </div>
                  <div className="summary-row">
                    <span className="label">Detection Camera:</span>
                    <span className="val font-semibold">{selectedAlert.camera_id}</span>
                  </div>
                  <div className="summary-row">
                    <span className="label">Trigger Time:</span>
                    <span className="val mono text-xs">
                      {selectedAlert.created_at ? new Date(selectedAlert.created_at).toISOString() : "—"}
                    </span>
                  </div>
                  <div className="summary-row">
                    <span className="label">Current Status:</span>
                    <span className="val">
                      <StatusBadge status={selectedAlert.status} />
                    </span>
                  </div>
                </div>

                {/* Evidence Link */}
                {selectedAlert.evidence_id && (
                  <div className="alert-evidence-box">
                    <div className="section-subtitle">Supporting Optical Crop</div>
                    <img
                      src={`/v1/evidence/${selectedAlert.evidence_id}`}
                      alt="Supporting alert crop"
                      className="alert-crop-img"
                    />
                    <button
                      className="btn btn-secondary btn-xs"
                      onClick={() => onSelectObservation(selectedAlert.observation_id || selectedAlert.evidence_id)}
                    >
                      Open in Full Evidence Drawer
                    </button>
                  </div>
                )}

                {/* Acknowledgment / Classification Form */}
                <form onSubmit={handleAcknowledge} className="ack-form">
                  <div className="form-group">
                    <label htmlFor="ack-classification">Investigative Classification</label>
                    <select
                      id="ack-classification"
                      value={classification}
                      onChange={(e) => setClassification(e.target.value as any)}
                      className="scope-select"
                    >
                      <option value="true">True Positive (Confirmed Match)</option>
                      <option value="false">False Positive (Misread / OCR Error)</option>
                      <option value="uncertain">Uncertain / Contested</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="ack-notes">Officer Resolution Notes (Audited)</label>
                    <textarea
                      id="ack-notes"
                      value={ackNotes}
                      onChange={(e) => setAckNotes(e.target.value)}
                      className="scope-textarea"
                      rows={3}
                      required
                    />
                  </div>

                  <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
                    <IconCheckCircle size={16} />
                    <span>Acknowledge & Record Assessment</span>
                  </button>
                </form>
              </div>
            ) : (
              <div className="empty-state">
                <p>Select an alert from the feed on the left to review details.</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Watchlists Management */
        <div className="watchlists-workspace-grid">
          {/* Create Draft Form (Left) */}
          <div className="panel watchlist-create-panel">
            <div className="panel-header">
              <h3 className="panel-title">Draft New Watchlist Entry</h3>
              <span className="panel-meta">Investigator / Admin</span>
            </div>

            <form onSubmit={handleCreateWatch} className="watch-create-form">
              <div className="form-group">
                <label htmlFor="watch-plate">Target Registration Plate</label>
                <input
                  id="watch-plate"
                  type="text"
                  value={newPlate}
                  onChange={(e) => setNewPlate(e.target.value.toUpperCase())}
                  placeholder="e.g. DL01AA1234"
                  className="scope-input mono font-bold"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="watch-reason">Lawful Purpose / FIR Reference</label>
                <input
                  id="watch-reason"
                  type="text"
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  placeholder="Official case reference"
                  className="scope-input"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="watch-severity">Severity Level</label>
                <select
                  id="watch-severity"
                  value={newSeverity}
                  onChange={(e) => setNewSeverity(e.target.value as any)}
                  className="scope-select"
                >
                  <option value="low">Low (Information Only)</option>
                  <option value="medium">Medium (Priority Tracking)</option>
                  <option value="high">High (Immediate Alert)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="watch-start">Valid From (UTC)</label>
                <input
                  id="watch-start"
                  type="text"
                  value={validFrom}
                  onChange={(e) => setValidFrom(e.target.value)}
                  className="scope-input mono text-xs"
                />
              </div>

              <div className="form-group">
                <label htmlFor="watch-end">Valid Until (UTC)</label>
                <input
                  id="watch-end"
                  type="text"
                  value={validUntil}
                  onChange={(e) => setValidUntil(e.target.value)}
                  className="scope-input mono text-xs"
                />
              </div>

              <button type="submit" className="btn btn-primary btn-block" disabled={busy || !runId}>
                <IconShield size={16} />
                <span>Create Watchlist Draft</span>
              </button>

              <div className="governance-box">
                <IconAlertTriangle size={14} className="text-warning inline-icon" />
                <span className="text-xs text-muted">
                  <b>Two-Person Rule:</b> Created entries enter <i>draft</i> state and require separate <i>approver</i> sign-in to activate.
                </span>
              </div>
            </form>
          </div>

          {/* Active Watchlists List (Right) */}
          <div className="panel watchlists-list-panel">
            <div className="panel-header">
              <h3 className="panel-title">Configured Watchlists</h3>
              <span className="panel-meta">{watchlists.length} entries</span>
            </div>

            {watchlists.length === 0 ? (
              <div className="empty-state">
                <p>No watchlists configured for this run scope.</p>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Target Plate</th>
                    <th>Reason / FIR</th>
                    <th>Status</th>
                    <th>Creator</th>
                    <th>Approver</th>
                    <th>Governance Action</th>
                  </tr>
                </thead>
                <tbody>
                  {watchlists.map((w) => (
                    <tr key={w.id}>
                      <td className="mono font-bold text-copper">{w.plate}</td>
                      <td className="text-sm">{w.reason}</td>
                      <td>
                        <StatusBadge status={w.status} size="sm" />
                      </td>
                      <td className="text-xs">{w.creator}</td>
                      <td className="text-xs">{w.approver || "Pending"}</td>
                      <td>
                        <div className="btn-group">
                          {w.status === "draft" && (
                            <button
                              className="btn btn-secondary btn-xs"
                              disabled={busy || actor === w.creator}
                              title={actor === w.creator ? "Two-person rule: Cannot self-approve" : "Approve watchlist"}
                              onClick={() => onWatchlistAction(w.id, "approve")}
                            >
                              Approve
                            </button>
                          )}
                          {w.status === "approved" && (
                            <button
                              className="btn btn-danger btn-xs"
                              disabled={busy}
                              onClick={() => onWatchlistAction(w.id, "revoke")}
                            >
                              Revoke
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
