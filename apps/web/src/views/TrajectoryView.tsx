import React, { useState } from "react";
import { NetworkMap } from "../components/NetworkMap";
import { StatusBadge } from "../components/StatusBadge";
import { IconSearch, IconClock, IconAlertTriangle } from "../components/Icons";

type RecordData = Record<string, any>;

interface TrajectoryViewProps {
  runId: string;
  start: string;
  end: string;
  cameras: RecordData[];
  graphEdges: RecordData[];
  journeyData: RecordData | null;
  onQueryTrajectory: (query: { plate: string; includeReview: boolean }) => Promise<void>;
  onSelectObservation: (obsId: string) => void;
  busy: boolean;
  message: string;
}

export function TrajectoryView({
  runId,
  start,
  end,
  cameras,
  graphEdges,
  journeyData,
  onQueryTrajectory,
  onSelectObservation,
  busy,
  message,
}: TrajectoryViewProps) {
  const [plate, setPlate] = useState("ZZ01AA0001");
  const [includeReview, setIncludeReview] = useState(false);
  const [purpose, setPurpose] = useState("Authorized incident investigation");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!plate.trim()) return;
    onQueryTrajectory({ plate: plate.trim(), includeReview });
  };

  const journey = journeyData;

  return (
    <div className="view-container trajectory-view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Vehicle Search & Trajectory Reconstruction</h1>
          <p className="view-subtitle">
            Audited multi-camera journey reconstruction based on temporal bounds, speed gates, and directed road network topology.
          </p>
        </div>
      </div>

      {/* Query Form Panel */}
      <div className="panel search-panel">
        <form onSubmit={handleSubmit} className="trajectory-form">
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="traj-plate">Registration Plate (Exact or Normalized)</label>
              <input
                id="traj-plate"
                type="text"
                value={plate}
                onChange={(e) => setPlate(e.target.value.toUpperCase())}
                placeholder="e.g. DL01AA1234"
                className="scope-input mono"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="traj-purpose">Investigation Purpose Code (Audited)</label>
              <input
                id="traj-purpose"
                type="text"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                placeholder="Case ID / Official Purpose"
                className="scope-input"
                required
              />
            </div>

            <div className="form-group form-check-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={includeReview}
                  onChange={(e) => setIncludeReview(e.target.checked)}
                />
                <span>Include Review Candidates (score 0.50–0.70)</span>
              </label>
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={busy || !runId}>
              <IconSearch size={16} />
              <span>{busy ? "Reconstructing…" : "Reconstruct Journey"}</span>
            </button>
          </div>
        </form>

        {message && (
          <div className={`status-banner ${message.includes("failed") || message.includes("denied") ? "banner-danger" : "banner-info"}`}>
            {message}
          </div>
        )}
      </div>

      {/* Journey Results */}
      {journey ? (
        <div className="trajectory-results">
          {/* Result Version & Policy Banner */}
          <div className="panel version-banner">
            <div className="version-info">
              <span className="version-tag mono">Result Version: {journey.result_version}</span>
              <span className="policy-tag text-muted">Policy: {journey.scoring_policy}</span>
            </div>
            <div className="disclaimer-tag">
              <IconAlertTriangle size={14} />
              <span>Straight connectors are schematic inferences, not proven continuous GPS tracks.</span>
            </div>
          </div>

          {/* Map & Timeline Split */}
          <div className="trajectory-split">
            {/* Left: Journey Network Map */}
            <div className="panel map-panel">
              <NetworkMap
                cameras={cameras}
                edges={graphEdges}
                nodes={journey.observed_nodes || []}
                links={journey.inferred_links || []}
                rejectedLinks={journey.rejected_links || []}
                reviewCandidates={journey.review_candidates || []}
                onSelectNode={(id) => onSelectObservation(id)}
                height={400}
              />
            </div>

            {/* Right: Chronological Sightings Timeline */}
            <div className="panel timeline-panel">
              <h3 className="panel-title">Chronological Sightings Timeline</h3>
              <div className="timeline-list">
                {journey.observed_nodes?.map((node: RecordData, idx: number) => (
                  <div
                    key={node.id || idx}
                    className="timeline-item"
                    onClick={() => onSelectObservation(node.id)}
                  >
                    <div className="timeline-marker">
                      <span className="marker-ordinal mono">{idx + 1}</span>
                    </div>

                    <div className="timeline-content">
                      <div className="timeline-top">
                        <span className="timeline-cam font-bold">{node.camera_id}</span>
                        <StatusBadge status={node.status} size="sm" />
                      </div>
                      <div className="timeline-time mono text-xs text-muted">
                        <IconClock size={12} />
                        {node.captured_at ? new Date(node.captured_at).toISOString().replace("T", " ").slice(0, 19) : "—"}
                      </div>
                      <div className="timeline-meta">
                        <span>Plate: <b className="mono text-copper">{node.plate}</b></span>
                      </div>
                      <button
                        className="btn btn-secondary btn-xs timeline-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectObservation(node.id);
                        }}
                      >
                        Inspect Evidence Crop
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Inferred Links Table */}
          <div className="panel table-panel">
            <h3 className="panel-title">Accepted Inferred Route Segments</h3>
            {journey.inferred_links?.length === 0 ? (
              <p className="empty-text">No plausible multi-camera links formed for this journey.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>From Camera</th>
                    <th>To Camera</th>
                    <th>Elapsed Time</th>
                    <th>Estimated Speed</th>
                    <th>Inference Status</th>
                  </tr>
                </thead>
                <tbody>
                  {journey.inferred_links?.map((l: RecordData, idx: number) => (
                    <tr key={idx}>
                      <td className="font-semibold mono">{l.source}</td>
                      <td className="font-semibold mono">{l.target}</td>
                      <td className="mono">{l.elapsed_seconds ? `${Math.round(l.elapsed_seconds)}s` : "—"}</td>
                      <td className="mono">{l.speed_kph ? `${l.speed_kph.toFixed(1)} km/h` : "—"}</td>
                      <td>
                        <StatusBadge status="inferred" label="Inferred Connection" size="sm" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Rejected & Ambiguous Links Table */}
          {journey.rejected_links && journey.rejected_links.length > 0 && (
            <div className="panel table-panel">
              <h3 className="panel-title">Rejected Link Candidates (Impossible Speed / Reversed Time)</h3>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Target</th>
                    <th>Elapsed Time</th>
                    <th>Rejection Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {journey.rejected_links.map((r: RecordData, idx: number) => (
                    <tr key={idx}>
                      <td className="mono">{r.source}</td>
                      <td className="mono">{r.target}</td>
                      <td className="mono">{r.elapsed_seconds ? `${Math.round(r.elapsed_seconds)}s` : "—"}</td>
                      <td>
                        <StatusBadge status="rejected" label={r.reason || "Impossible movement"} size="sm" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Missing Coverage & Limitations Disclosure */}
          {journey.limitations && (
            <div className="panel limitations-panel">
              <h4 className="limitations-title">Operational Limitations & Missing Coverage</h4>
              <p className="text-sm text-secondary">{journey.limitations}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="panel empty-state-panel">
          <p>Enter a vehicle registration plate number above to query the evidence-backed trajectory.</p>
        </div>
      )}
    </div>
  );
}
