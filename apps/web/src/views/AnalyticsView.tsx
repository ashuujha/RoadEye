import React, { useState } from "react";
import { StatusBadge } from "../components/StatusBadge";
import { IconAnalytics, IconAlertTriangle } from "../components/Icons";

type RecordData = Record<string, any>;

interface AnalyticsViewProps {
  runId: string;
  metricsData?: RecordData;
}

export function AnalyticsView({ runId, metricsData }: AnalyticsViewProps) {
  const [tab, setTab] = useState<"volume" | "flow" | "od" | "travel">("volume");
  const m = metricsData;

  return (
    <div className="view-container analytics-view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Urban Traffic Analytics & Flows</h1>
          <p className="view-subtitle">
            Privacy-preserving aggregate traffic metrics, enrolled camera flows, and origin-destination matrices.
          </p>
        </div>

        <div className="tab-group" role="tablist">
          <button
            className={`tab-btn ${tab === "volume" ? "active" : ""}`}
            onClick={() => setTab("volume")}
            role="tab"
          >
            Volume & Recognition
          </button>
          <button
            className={`tab-btn ${tab === "flow" ? "active" : ""}`}
            onClick={() => setTab("flow")}
            role="tab"
          >
            Camera Flows (A→B)
          </button>
          <button
            className={`tab-btn ${tab === "od" ? "active" : ""}`}
            onClick={() => setTab("od")}
            role="tab"
          >
            Origin-Destination (OD)
          </button>
          <button
            className={`tab-btn ${tab === "travel" ? "active" : ""}`}
            onClick={() => setTab("travel")}
            role="tab"
          >
            Travel Time & Congestion
          </button>
        </div>
      </div>

      {!runId ? (
        <div className="panel empty-state-panel">
          <p>Please select an active run in the scope bar to view computed traffic analytics.</p>
        </div>
      ) : !m ? (
        <div className="panel loading-panel">
          <div className="spinner" />
          <p>Aggregating 5-minute event windows and calculating flow matrices…</p>
        </div>
      ) : (
        <div className="analytics-content">
          {/* Summary KPIs */}
          <div className="analytics-summary-grid">
            <div className="panel kpi-box">
              <span className="kpi-label">Total Vehicle Passages</span>
              <span className="kpi-value mono">{m.vehicle_passages ?? "—"}</span>
              <span className="kpi-hint">Deduped crossings</span>
            </div>
            <div className="panel kpi-box">
              <span className="kpi-label">Accepted Plates</span>
              <span className="kpi-value mono text-success">{m.accepted_plates ?? "—"}</span>
              <span className="kpi-hint">High confidence readings</span>
            </div>
            <div className="panel kpi-box">
              <span className="kpi-label">Recognition Coverage</span>
              <span className="kpi-value mono text-copper">
                {m.recognition_coverage !== undefined ? `${(m.recognition_coverage * 100).toFixed(1)}%` : "—"}
              </span>
              <span className="kpi-hint">Accepted / total passages</span>
            </div>
            <div className="panel kpi-box">
              <span className="kpi-label">Sample Size</span>
              <span className="kpi-value mono">{m.sample_size ?? "—"}</span>
              <span className="kpi-hint">Observations in window</span>
            </div>
          </div>

          {/* Tab 1: Volume & Recognition */}
          {tab === "volume" && (
            <div className="panel analytics-panel">
              <div className="panel-header">
                <h3 className="panel-title">Passage Volumes & Recognition Coverage by Camera</h3>
                <span className="panel-meta">Enrolled Sensor Coverage</span>
              </div>

              <div className="volume-bars-detailed">
                {m.counts?.map((c: RecordData) => {
                  const max = Math.max(1, ...m.counts.map((x: RecordData) => x.passages || 0));
                  const pct = Math.round(((c.passages || 0) / max) * 100);

                  return (
                    <div key={c.camera_id} className="volume-detail-row">
                      <div className="vol-cam-col">
                        <span className="mono font-bold text-base">{c.camera_id}</span>
                        <StatusBadge status={c.coverage_state} size="sm" />
                      </div>
                      <div className="vol-bar-col">
                        <div className="vol-meter-bg">
                          <div className="vol-meter-fill" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                      <div className="vol-stats-col mono">
                        <span><b>{c.passages}</b> passages</span>
                        <span className="text-xs text-muted">
                          {c.accepted_plates} accepted · {c.review_required || 0} review
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Tab 2: Camera Flows (A -> B) */}
          {tab === "flow" && (
            <div className="panel analytics-panel">
              <div className="panel-header">
                <h3 className="panel-title">Directional Link Flows Between Adjacent Cameras</h3>
                <span className="panel-meta">A → B Traversal Counts</span>
              </div>

              {m.flow && m.flow.length > 0 ? (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Source Camera (A)</th>
                      <th>Target Camera (B)</th>
                      <th>Observed Link Volume</th>
                      <th>Median Travel Time</th>
                      <th>Flow Direction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {m.flow.map((f: RecordData, idx: number) => (
                      <tr key={idx}>
                        <td className="mono font-bold">{f.source}</td>
                        <td className="mono font-bold">{f.target}</td>
                        <td className="mono text-copper font-semibold">{f.count || f.volume || 0} vehicles</td>
                        <td className="mono">{f.median_seconds ? `${Math.round(f.median_seconds)}s` : "—"}</td>
                        <td>
                          <span className="flow-badge">Directed Route</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="empty-text">No multi-camera directional flows formed in this window.</p>
              )}
            </div>
          )}

          {/* Tab 3: Origin-Destination (OD) Matrix with Cell Suppression */}
          {tab === "od" && (
            <div className="panel analytics-panel">
              <div className="panel-header">
                <h3 className="panel-title">Origin-Destination (OD) Matrix</h3>
                <span className="panel-meta">Privacy-Preserving Cell Suppression</span>
              </div>

              <div className="privacy-notice">
                <IconAlertTriangle size={14} className="text-warning inline-icon" />
                <span>
                  Cells with counts below the privacy threshold are marked <b>&lt;Suppressed&gt;</b> to prevent re-identification.
                </span>
              </div>

              {m.od && m.od.length > 0 ? (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Origin Zone / Camera</th>
                      <th>Destination Zone / Camera</th>
                      <th>Trip Volume</th>
                      <th>Suppression Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {m.od.map((row: RecordData, idx: number) => (
                      <tr key={idx}>
                        <td className="mono font-semibold">{row.origin || row.source}</td>
                        <td className="mono font-semibold">{row.destination || row.target}</td>
                        <td className="mono">
                          {row.count !== undefined && row.count !== null ? (
                            row.count < 3 ? (
                              <span className="suppressed-cell">&lt;Suppressed&gt;</span>
                            ) : (
                              row.count
                            )
                          ) : (
                            <span className="suppressed-cell">&lt;Suppressed&gt;</span>
                          )}
                        </td>
                        <td>
                          {row.count !== undefined && row.count < 3 ? (
                            <span className="tag-suppressed">Protected</span>
                          ) : (
                            <span className="tag-published">Published</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="empty-text">No origin-destination trips completed within this time range.</p>
              )}
            </div>
          )}

          {/* Tab 4: Travel Time & Congestion */}
          {tab === "travel" && (
            <div className="panel analytics-panel">
              <div className="panel-header">
                <h3 className="panel-title">Corridor Travel Time & Congestion Proxies</h3>
                <span className="panel-meta">Algorithmic Travel Time Estimates</span>
              </div>

              {m.travel_times && m.travel_times.length > 0 ? (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Corridor Segment</th>
                      <th>Sample Count</th>
                      <th>Median Travel Time</th>
                      <th>p95 Travel Time</th>
                      <th>Congestion Proxy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {m.travel_times.map((t: RecordData, idx: number) => (
                      <tr key={idx}>
                        <td className="mono font-bold">{t.segment || `${t.source} → ${t.target}`}</td>
                        <td className="mono">{t.samples || 0}</td>
                        <td className="mono">{t.median_seconds ? `${Math.round(t.median_seconds)}s` : "—"}</td>
                        <td className="mono">{t.p95_seconds ? `${Math.round(t.p95_seconds)}s` : "—"}</td>
                        <td>
                          <StatusBadge
                            status={t.congestion_index > 1.3 ? "review_required" : "accepted"}
                            label={t.congestion_index > 1.3 ? "Elevated Delay" : "Nominal Flow"}
                            size="sm"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="empty-text">No travel time segments calculated for this interval.</p>
              )}
            </div>
          )}

          {/* Limitations Disclosure */}
          {m.limitations && m.limitations.length > 0 && (
            <div className="panel limitations-panel">
              <h4 className="limitations-title">Analytics Truth & Governance Notes</h4>
              <ul className="limitations-list">
                {m.limitations.map((l: string, idx: number) => (
                  <li key={idx}>{l}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
