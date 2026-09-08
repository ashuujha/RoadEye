import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import type { AnalyticsResponse } from "../api.generated";
import { StatusBadge } from "../components/StatusBadge";

function seconds(value: number | null): string {
  return value === null ? "Unavailable" : value.toFixed(2) + " s";
}

function share(value: number): string {
  return (value * 100).toFixed(1) + "%";
}

export function AnalyticsSummary({ data }: { data: AnalyticsResponse }) {
  const { summary } = data;
  const maximumVisits = Math.max(1, ...data.camera_density.map((row) => row.observed_runtime_visit_count));

  return (
    <div className="analytics-content">
      <div className="panel analytics-provenance">
        <StatusBadge status="uncertain" label="UNVERIFIED / PREDICTION-ONLY" />
        <p>{data.disclosure ?? "Aggregates of frozen runtime predictions."}</p>
        <p>Scenario: <strong>{data.scenario}</strong> / observed interval: {seconds(summary.first_observed_s)} to {seconds(summary.last_observed_s)}</p>
        <details>
          <summary>Prediction source provenance</summary>
          <p className="mono evidence-hash">SHA-256 {data.source_prediction_sha256}</p>
        </details>
      </div>

      <div className="analytics-metric-grid">
        {[
          ["Predicted vehicle IDs", summary.predicted_global_vehicle_ids],
          ["Multi-camera predicted IDs", summary.multi_camera_predicted_vehicle_ids],
          ["Observed runtime visits", summary.observed_runtime_visits],
          ["Predicted transitions", summary.predicted_transitions],
        ].map(([label, value]) => (
          <div key={label} className="panel analytics-metric">
            <span>{label}</span>
            <strong className="mono">{value}</strong>
          </div>
        ))}
      </div>

      <section className="panel analytics-panel">
        <h2 className="panel-title">Camera visit counts</h2>
        <p className="text-muted">Observed runtime visits and model-predicted identities. These counts are not traffic density or total traffic volume.</p>
        {data.camera_density.length === 0 ? <p className="empty-text">No camera visit rows are available.</p> : (
          <div className="analytics-table-scroll">
            <table className="data-table">
              <thead><tr><th>Camera</th><th>Observed visits</th><th>Predicted IDs</th><th>Multi-camera IDs</th><th>Share of runtime visits</th></tr></thead>
              <tbody>
                {data.camera_density.map((row) => (
                  <tr key={row.camera}>
                    <td className="mono">{row.camera}</td>
                    <td>
                      <span className="mono">{row.observed_runtime_visit_count}</span>
                      <div className="volume-bar-bg" aria-hidden="true">
                        <div className="volume-bar-fill" style={{ width: (row.observed_runtime_visit_count / maximumVisits) * 100 + "%" }} />
                      </div>
                    </td>
                    <td className="mono">{row.predicted_unique_vehicle_count}</td>
                    <td className="mono">{row.multi_camera_predicted_vehicle_count}</td>
                    <td className="mono">{share(row.share_of_observed_runtime_visits)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel analytics-panel">
        <h2 className="panel-title">Predicted origin-destination endpoints</h2>
        <p className="text-muted">First and last cameras of multi-camera predictions; not verified OD flow or complete trips.</p>
        {data.origin_destination_pairs.length === 0 ? <p className="empty-text">No predicted OD pairs are available.</p> : (
          <div className="analytics-table-scroll">
            <table className="data-table">
              <thead><tr><th>Origin camera</th><th>Destination camera</th><th>Predicted IDs</th><th>Share of multi-camera predictions</th></tr></thead>
              <tbody>
                {data.origin_destination_pairs.map((row) => (
                  <tr key={row.origin_camera + ":" + row.destination_camera}>
                    <td className="mono">{row.origin_camera}</td>
                    <td className="mono">{row.destination_camera}</td>
                    <td className="mono">{row.predicted_vehicle_count}</td>
                    <td className="mono">{share(row.share_of_multi_camera_predictions)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel analytics-panel">
        <h2 className="panel-title">Transition-support proxies</h2>
        <p className="text-muted">Ranked predicted transition counts; not congestion measurements. Observed boundary gaps are not route travel times and can be negative when camera visits overlap.</p>
        {data.bottleneck_proxies.length === 0 ? <p className="empty-text">No predicted transition proxies are available.</p> : (
          <div className="analytics-table-scroll">
            <table className="data-table">
              <thead><tr><th>Rank</th><th>From</th><th>To</th><th>Predicted transitions</th><th>Transition share</th><th>Median boundary gap</th><th>Maximum boundary gap</th></tr></thead>
              <tbody>
                {data.bottleneck_proxies.map((row) => (
                  <tr key={row.from_camera + ":" + row.to_camera}>
                    <td>{row.rank}</td>
                    <td className="mono">{row.from_camera}</td>
                    <td className="mono">{row.to_camera}</td>
                    <td className="mono">{row.predicted_transition_count}</td>
                    <td className="mono">{share(row.share_of_predicted_transitions)}</td>
                    <td className="mono">{seconds(row.median_observed_boundary_gap_s)}</td>
                    <td className="mono">{seconds(row.maximum_observed_boundary_gap_s)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <p className="text-muted">Prediction counts do not establish identity accuracy. Runtime analytics use no ground-truth identities, plate strings, or owner data.</p>
    </div>
  );
}

export function AnalyticsView() {
  const result = useQuery({
    queryKey: ["analytics"],
    queryFn: ({ signal }) => api.analytics({ signal }),
    staleTime: 60_000,
  });

  return (
    <div className="view-container analytics-view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Prediction Analytics</h1>
          <p className="view-subtitle">Camera visits, predicted endpoints, and transition support from the audited runtime artifacts.</p>
        </div>
        <StatusBadge status="uncertain" label="UNVERIFIED" />
      </div>
      {result.isPending ? (
        <div className="panel" role="status">Loading prediction aggregates...</div>
      ) : result.isError ? (
        <div className="panel status-banner banner-danger" role="alert">
          <p>{result.error.message}</p>
          <button type="button" className="btn btn-secondary" onClick={() => void result.refetch()}>Retry analytics</button>
        </div>
      ) : <AnalyticsSummary data={result.data} />}
    </div>
  );
}
