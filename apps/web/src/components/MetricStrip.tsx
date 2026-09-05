import React from "react";

interface MetricStripProps {
  acceptedCount: number | null | undefined;
  reviewCount: number | null | undefined;
  sourcesInScope: { active: number; total: number } | number | null | undefined;
  pendingAlerts: number | null | undefined;
  caption?: string;
}

export function MetricStrip({
  acceptedCount,
  reviewCount,
  sourcesInScope,
  pendingAlerts,
  caption,
}: MetricStripProps) {
  const renderSourceCount = () => {
    if (sourcesInScope === null || sourcesInScope === undefined) {
      return <span className="metric-val unavailable">N/A</span>;
    }
    if (typeof sourcesInScope === "object") {
      return (
        <span className="metric-val">
          {sourcesInScope.active} <span className="metric-sub">/ {sourcesInScope.total}</span>
        </span>
      );
    }
    return <span className="metric-val">{sourcesInScope}</span>;
  };

  return (
    <div className="metric-strip" role="region" aria-label="Key traffic operations metrics">
      <div className="metric-cell metric-accepted">
        <div className="metric-header">
          <span className="metric-dot dot-success" />
          <span className="metric-label">Accepted Observations</span>
        </div>
        <div className="metric-val">
          {acceptedCount !== null && acceptedCount !== undefined ? (
            acceptedCount.toLocaleString()
          ) : (
            <span className="unavailable">Unavailable</span>
          )}
        </div>
        <div className="metric-hint">Passage-deduplicated plates</div>
      </div>

      <div className="metric-cell metric-review">
        <div className="metric-header">
          <span className="metric-dot dot-warning" />
          <span className="metric-label">Review Required</span>
        </div>
        <div className="metric-val">
          {reviewCount !== null && reviewCount !== undefined ? (
            reviewCount.toLocaleString()
          ) : (
            <span className="unavailable">0</span>
          )}
        </div>
        <div className="metric-hint">Low consensus or ambiguous</div>
      </div>

      <div className="metric-cell metric-sources">
        <div className="metric-header">
          <span className="metric-dot dot-info" />
          <span className="metric-label">Sources In Scope</span>
        </div>
        {renderSourceCount()}
        <div className="metric-hint">Active enrolled cameras</div>
      </div>

      <div className="metric-cell metric-alerts">
        <div className="metric-header">
          <span className="metric-dot dot-danger" />
          <span className="metric-label">Pending Alerts</span>
        </div>
        <div className="metric-val">
          {pendingAlerts !== null && pendingAlerts !== undefined ? (
            pendingAlerts.toLocaleString()
          ) : (
            <span className="unavailable">0</span>
          )}
        </div>
        <div className="metric-hint">Unacknowledged watchlist hits</div>
      </div>
    </div>
  );
}
