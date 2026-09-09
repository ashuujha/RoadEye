import React, { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { client, unwrap } from "../api";
import { IconClose, IconExternalLink, IconShield, IconClock } from "./Icons";
import { StatusBadge } from "./StatusBadge";

interface EvidenceDrawerProps {
  observationId: string | null;
  onClose: () => void;
  onOpenReview?: (obsId: string) => void;
}

type RecordData = Record<string, any>;

export function EvidenceDrawer({ observationId, onClose, onOpenReview }: EvidenceDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && observationId) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [observationId, onClose]);

  const detail = useQuery({
    queryKey: ["drawer-observation", observationId],
    enabled: !!observationId,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/observations/{observation_id}", {
          params: { path: { observation_id: observationId! } },
        })
      ).data as RecordData,
  });

  if (!observationId) return null;

  const data = detail.data;
  const evidenceId = data?.passage?.evidence_id || data?.evidence_id;

  return (
    <div className="drawer-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <div className="drawer-panel" ref={drawerRef} onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <div className="drawer-kicker">EVIDENCE RECORD</div>
            <h2 id="drawer-title" className="drawer-title">
              {data ? `${data.camera_id} · ${data.plate || "Unreadable"}` : "Loading evidence…"}
            </h2>
          </div>
          <button className="btn-icon" onClick={onClose} aria-label="Close evidence drawer">
            <IconClose size={20} />
          </button>
        </div>

        <div className="drawer-body">
          {detail.isPending && (
            <div className="drawer-loading">
              <div className="spinner" />
              <p>Fetching immutable observation record & evidence hashes…</p>
            </div>
          )}

          {detail.error && (
            <div className="alert-box alert-danger">
              <p>Failed to load evidence record: {detail.error.message}</p>
            </div>
          )}

          {data && (
            <>
              {/* Evidence Crop and Imagery */}
              <section className="drawer-section">
                <div className="section-title">Optical Evidence Crop</div>
                <div className="evidence-preview-wrapper">
                  {evidenceId ? (
                    <div className="crop-container">
                      <img
                        src={`/v1/evidence/${evidenceId}`}
                        alt={`Optical crop for observation ${data.id}`}
                        className="crop-image"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                      <div className="crop-actions">
                        <a
                          href={`/v1/evidence/${evidenceId}`}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-secondary btn-sm"
                        >
                          <IconExternalLink size={14} />
                          <span>View Full Res Crop</span>
                        </a>
                      </div>
                    </div>
                  ) : (
                    <div className="crop-placeholder">
                      <span>No direct crop asset referenced</span>
                    </div>
                  )}

                  <div className="crop-metadata">
                    <div className="meta-row">
                      <span className="meta-label">Capture Time</span>
                      <span className="meta-val mono">
                        {data.captured_at ? new Date(data.captured_at).toISOString() : "Unknown"}
                      </span>
                    </div>
                    <div className="meta-row">
                      <span className="meta-label">Camera / Lane</span>
                      <span className="meta-val">
                        {data.camera_id} {data.lane ? `· Lane ${data.lane}` : ""}
                      </span>
                    </div>
                    <div className="meta-row">
                      <span className="meta-label">Decision Status</span>
                      <span className="meta-val">
                        <StatusBadge status={data.status} />
                      </span>
                    </div>
                    <div className="meta-row">
                      <span className="meta-label">Calibrated Score</span>
                      <span className="meta-val mono">
                        {typeof data.score === "number" ? data.score.toFixed(3) : "N/A"}
                        <span className="meta-sub"> (algorithmic consensus)</span>
                      </span>
                    </div>
                    {data.evidence_sha256 && (
                      <div className="meta-row">
                        <span className="meta-label">SHA-256 Digest</span>
                        <span className="meta-val mono text-xs" title={data.evidence_sha256}>
                          <IconShield size={12} className="inline-icon" />
                          {data.evidence_sha256.slice(0, 16)}…
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </section>

              {/* Machine Decision Breakdown */}
              {data.machine && (
                <section className="drawer-section">
                  <div className="section-title">Consensus & Model Attribution</div>
                  <div className="consensus-summary">
                    <div className="consensus-meta">
                      <span>Policy: <b>{data.policy || "v1-baseline"}</b></span>
                      <span>Origin: <b>{data.inference_origin || "worker_onnx"}</b></span>
                    </div>
                    {data.machine.reasons && data.machine.reasons.length > 0 && (
                      <div className="reasons-list">
                        <span className="meta-label">Decision Reasons:</span>
                        <div className="badge-group">
                          {data.machine.reasons.map((r: string) => (
                            <span key={r} className="reason-tag">{r}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {data.machine.contributions && data.machine.contributions.length > 0 && (
                    <div className="contributions-table-wrapper">
                      <table className="data-table dense">
                        <thead>
                          <tr>
                            <th>Candidate</th>
                            <th>Conf</th>
                            <th>Quality</th>
                            <th>Bonus</th>
                            <th>Weight</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.machine.contributions.map((c: RecordData, idx: number) => (
                            <tr key={idx}>
                              <td className="mono font-semibold">{c.candidate || c.plate || "—"}</td>
                              <td className="mono">{typeof c.confidence === "number" ? c.confidence.toFixed(2) : "—"}</td>
                              <td className="mono">{typeof c.quality === "number" ? c.quality.toFixed(2) : "—"}</td>
                              <td className="mono">{c.bonus ? `+${c.bonus}` : "0"}</td>
                              <td className="mono">{typeof c.weight === "number" ? c.weight.toFixed(2) : "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              )}

              {/* Append-Only Revision History */}
              {data.revisions && data.revisions.length > 0 && (
                <section className="drawer-section">
                  <div className="section-title">Human Revision Audit Trail</div>
                  <div className="revisions-list">
                    {data.revisions.map((rev: RecordData) => (
                      <div key={rev.id || rev.number} className="revision-item">
                        <div className="revision-header">
                          <span className="revision-num">Rev #{rev.number}</span>
                          <span className="revision-actor">{rev.actor}</span>
                          <span className="revision-time">
                            <IconClock size={12} />
                            {rev.created_at ? new Date(rev.created_at).toLocaleTimeString() : ""}
                          </span>
                        </div>
                        <div className="revision-body">
                          <div>Revised Status: <StatusBadge status={rev.status} size="sm" /></div>
                          {rev.plate && <div>Corrected Plate: <span className="mono font-bold">{rev.plate}</span></div>}
                          {rev.reason && <div className="revision-reason">"{rev.reason}"</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Raw Record JSON Inspector */}
              <section className="drawer-section">
                <details className="raw-details">
                  <summary className="raw-summary">Technical Provenance & Event Data</summary>
                  <pre className="code-block">{JSON.stringify(data, null, 2)}</pre>
                </details>
              </section>

              {onOpenReview && (
                <div className="drawer-footer">
                  <button
                    className="btn btn-primary btn-block"
                    onClick={() => {
                      onOpenReview(data.id);
                      onClose();
                    }}
                  >
                    Open in Review Workbench
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
