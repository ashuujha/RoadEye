import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { client, unwrap } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { IconReview, IconCheckCircle, IconXCircle, IconAlertTriangle, IconClock } from "../components/Icons";

type RecordData = Record<string, any>;

interface ReviewWorkbenchViewProps {
  runId: string;
  observations: RecordData[];
  onSelectObservation: (id: string) => void;
  onSubmitReview: (obsId: string, review: { status: string; plate: string | null; reason: string }) => Promise<void>;
  busy: boolean;
  message: string;
}

export function ReviewWorkbenchView({
  runId,
  observations,
  onSelectObservation,
  onSubmitReview,
  busy,
  message,
}: ReviewWorkbenchViewProps) {
  const [selectedId, setSelectedId] = useState<string>(observations[0]?.id || "");
  const [revisedPlate, setRevisedPlate] = useState("");
  const [revisedStatus, setRevisedStatus] = useState<"accepted" | "review_required" | "rejected">("accepted");
  const [reviewReason, setReviewReason] = useState("Human verification of plate candidates");

  // Filter observations: prioritize review_required, or show all
  const queueItems = observations.filter((o) => o.status === "review_required" || o.status === "pending");
  const displayQueue = queueItems.length > 0 ? queueItems : observations;

  const currentObservation = observations.find((o) => o.id === selectedId) || displayQueue[0];

  const detail = useQuery({
    queryKey: ["review-detail", currentObservation?.id],
    enabled: !!currentObservation?.id,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/observations/{observation_id}", {
          params: { path: { observation_id: currentObservation!.id } },
        })
      ).data as RecordData,
  });

  const handleSelect = (obs: RecordData) => {
    setSelectedId(obs.id);
    setRevisedPlate(obs.plate || "");
    setRevisedStatus(obs.status === "rejected" ? "rejected" : "accepted");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentObservation) return;
    await onSubmitReview(currentObservation.id, {
      status: revisedStatus,
      plate: revisedStatus === "rejected" ? null : revisedPlate.trim(),
      reason: reviewReason,
    });
  };

  const activeData = detail.data || currentObservation;
  const evidenceId = activeData?.passage?.evidence_id || activeData?.evidence_id;

  return (
    <div className="view-container review-workbench-view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Human Review Workbench</h1>
          <p className="view-subtitle">
            Operational verification for uncertain OCR consensus, ambiguous readings, and contested detections. Human review does not alter machine scores.
          </p>
        </div>
        <div className="queue-stat-badge">
          <span className="queue-count mono">{queueItems.length}</span>
          <span>Items Pending Review</span>
        </div>
      </div>

      {/* 3-Column Layout */}
      <div className="workbench-grid">
        {/* Column 1: Review Queue (Left) */}
        <div className="panel queue-column">
          <div className="column-header">
            <h3 className="column-title">Review Queue</h3>
            <span className="column-meta">{displayQueue.length} items</span>
          </div>

          <div className="queue-items-list">
            {displayQueue.length === 0 ? (
              <div className="queue-empty">
                <IconCheckCircle size={24} className="text-success" />
                <p>No observations requiring immediate review in current scope.</p>
              </div>
            ) : (
              displayQueue.map((item) => (
                <div
                  key={item.id}
                  className={`queue-item ${currentObservation?.id === item.id ? "active" : ""}`}
                  onClick={() => handleSelect(item)}
                >
                  <div className="queue-item-top">
                    <span className="mono font-bold text-copper">{item.plate || "Unreadable"}</span>
                    <StatusBadge status={item.status} size="sm" />
                  </div>
                  <div className="queue-item-bottom">
                    <span className="text-xs">{item.camera_id}</span>
                    <span className="text-xs mono text-muted">
                      Score: {typeof item.score === "number" ? item.score.toFixed(2) : "—"}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Column 2: Evidence & Candidate Analysis (Center) */}
        <div className="panel evidence-column">
          <div className="column-header">
            <h3 className="column-title">Optical Crop & Candidates</h3>
            {activeData && <span className="column-meta mono">{activeData.id.slice(0, 8)}</span>}
          </div>

          {currentObservation ? (
            <div className="evidence-workbench-body">
              {/* Image Preview */}
              <div className="evidence-display-area">
                {evidenceId ? (
                  <div className="crop-inspection-card">
                    <img
                      src={`/v1/evidence/${evidenceId}`}
                      alt="Crop under review"
                      className="workbench-crop-img"
                    />
                    <div className="crop-meta-bar">
                      <span>Camera: <b>{activeData?.camera_id}</b></span>
                      <span>Captured: <b className="mono">{activeData?.captured_at ? new Date(activeData.captured_at).toLocaleTimeString() : ""}</b></span>
                    </div>
                  </div>
                ) : (
                  <div className="empty-crop-placeholder">
                    <span>No image crop available for this record</span>
                  </div>
                )}
              </div>

              {/* Machine Consensus Attribution */}
              {activeData?.machine && (
                <div className="machine-attribution-box">
                  <div className="section-subtitle">Multi-Frame Candidate Consensus</div>
                  <div className="contributions-table-wrapper">
                    <table className="data-table dense">
                      <thead>
                        <tr>
                          <th>Candidate Plate</th>
                          <th>Confidence</th>
                          <th>Quality</th>
                          <th>Score Bonus</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeData.machine.contributions?.map((c: RecordData, idx: number) => (
                          <tr key={idx}>
                            <td className="mono font-bold text-copper">{c.candidate || c.plate || "—"}</td>
                            <td className="mono">{typeof c.confidence === "number" ? c.confidence.toFixed(2) : "—"}</td>
                            <td className="mono">{typeof c.quality === "number" ? c.quality.toFixed(2) : "—"}</td>
                            <td className="mono">+{c.bonus || 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {activeData.machine.reasons && (
                    <div className="reasons-note">
                      <span className="text-muted text-xs">Flags: </span>
                      {activeData.machine.reasons.join(", ")}
                    </div>
                  )}
                </div>
              )}

              {/* Existing Revisions */}
              {activeData?.revisions && activeData.revisions.length > 0 && (
                <div className="prior-revisions-box">
                  <div className="section-subtitle">Prior Audit Revisions ({activeData.revisions.length})</div>
                  {activeData.revisions.map((r: RecordData) => (
                    <div key={r.number} className="revision-summary-row">
                      <span className="mono text-xs">Rev #{r.number}</span>
                      <span className="text-xs font-semibold">{r.actor}</span>
                      <StatusBadge status={r.status} size="sm" />
                      <span className="mono font-bold text-xs">{r.plate || "rejected"}</span>
                      <span className="text-xs text-muted">"{r.reason}"</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">
              <p>Select an observation from the queue to begin review.</p>
            </div>
          )}
        </div>

        {/* Column 3: Review Decision Form (Right) */}
        <div className="panel decision-column">
          <div className="column-header">
            <h3 className="column-title">Operator Decision</h3>
          </div>

          {currentObservation ? (
            <form onSubmit={handleSubmit} className="decision-form">
              <div className="form-group">
                <label htmlFor="review-status">Decision Determination</label>
                <select
                  id="review-status"
                  value={revisedStatus}
                  onChange={(e) => setRevisedStatus(e.target.value as any)}
                  className="scope-select"
                >
                  <option value="accepted">Accept / Correct Plate</option>
                  <option value="review_required">Keep in Review Queue</option>
                  <option value="rejected">Reject / Unreadable Plate</option>
                </select>
              </div>

              {revisedStatus !== "rejected" && (
                <div className="form-group">
                  <label htmlFor="review-plate">Verified Full Plate (Indian Registration)</label>
                  <input
                    id="review-plate"
                    type="text"
                    value={revisedPlate}
                    onChange={(e) => setRevisedPlate(e.target.value.toUpperCase())}
                    className="scope-input mono font-bold"
                    placeholder="e.g. DL01AA1234"
                    required={revisedStatus === "accepted"}
                  />
                  <small className="field-hint">
                    Requires normalized state/series format. Does not overwrite original OCR candidate logs.
                  </small>
                </div>
              )}

              <div className="form-group">
                <label htmlFor="review-reason">Verification Rationale (Audited)</label>
                <textarea
                  id="review-reason"
                  value={reviewReason}
                  onChange={(e) => setReviewReason(e.target.value)}
                  className="scope-textarea"
                  rows={3}
                  required
                />
              </div>

              <div className="decision-actions">
                <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
                  <IconCheckCircle size={16} />
                  <span>{busy ? "Saving Revision…" : "Commit Review Decision"}</span>
                </button>
              </div>

              {message && (
                <div className={`status-banner ${message.includes("failed") || message.includes("denied") ? "banner-danger" : "banner-info"}`}>
                  {message}
                </div>
              )}

              <div className="governance-box">
                <IconAlertTriangle size={14} className="text-warning inline-icon" />
                <span className="text-xs text-muted">
                  Decisions append an immutable revision record with your actor ID and correlation hash.
                </span>
              </div>
            </form>
          ) : (
            <div className="empty-state">
              <p>No active item selected.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
