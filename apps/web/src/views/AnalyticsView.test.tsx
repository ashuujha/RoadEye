import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AnalyticsResponse } from "../api.generated";
import { AnalyticsSummary } from "./AnalyticsView";

const data: AnalyticsResponse = {
  schema_version: 1,
  status: "UNVERIFIED",
  scope: "prediction_only_aggregate_runtime_analytics",
  scenario: "fixture",
  disclosure: "Fixture prediction disclosure",
  source_prediction_sha256: "a".repeat(64),
  summary: {
    predicted_global_vehicle_ids: 1,
    multi_camera_predicted_vehicle_ids: 1,
    observed_runtime_visits: 2,
    predicted_transitions: 1,
    camera_count: 2,
    first_observed_s: 0,
    last_observed_s: 12,
  },
  camera_density: [{
    camera: "c0", observed_runtime_visit_count: 0, predicted_unique_vehicle_count: 0,
    multi_camera_predicted_vehicle_count: 0, share_of_observed_runtime_visits: 0,
    position: { latitude: 0, longitude: 0, kind: "approximate" },
    measurement_status: "runtime_prediction_visit_count_not_traffic_density",
  }],
  origin_destination_pairs: [{
    origin_camera: "c1", destination_camera: "c2", predicted_vehicle_count: 1,
    share_of_multi_camera_predictions: 1,
    measurement_status: "predicted_endpoints_not_verified_od_flow",
  }],
  bottleneck_proxies: [{
    rank: 1, from_camera: "c1", to_camera: "c2", predicted_transition_count: 1,
    share_of_predicted_transitions: 1, median_observed_boundary_gap_s: -2,
    maximum_observed_boundary_gap_s: 0,
    measurement_status: "predicted_transition_support_not_congestion_or_route_time",
  }],
  claim_boundaries: {
    uses_runtime_ground_truth: false, counts_model_predicted_identities: true,
    camera_density_is_traffic_volume: false, origin_destination_is_verified_flow: false,
    bottleneck_proxy_is_congestion: false, boundary_gap_is_route_travel_time: false,
    plate_or_owner_data_used: false,
  },
};

describe("analytics claim boundaries", () => {
  it("preserves zero, overlapping boundary gaps and unsuppressed small prediction counts", () => {
    const html = renderToStaticMarkup(<AnalyticsSummary data={data} />);
    expect(html).toContain("UNVERIFIED / PREDICTION-ONLY");
    expect(html).toContain("-2.00 s");
    expect(html).toContain("0.00 s");
    expect(html).toContain("0.0%");
    expect(html).toContain("not verified OD flow");
    expect(html).toContain("not congestion measurements");
    expect(html).not.toContain("Suppressed");
    expect(html).not.toContain("Accepted Plates");
  });

  it("distinguishes missing time bounds and empty aggregates from measured zero", () => {
    const html = renderToStaticMarkup(<AnalyticsSummary data={{
      ...data, summary: { ...data.summary, first_observed_s: null, last_observed_s: null },
      camera_density: [], origin_destination_pairs: [], bottleneck_proxies: [],
    }} />);
    expect(html).toContain("Unavailable to Unavailable");
    expect(html).toContain("No camera visit rows");
    expect(html).toContain("No predicted OD pairs");
    expect(html).toContain("No predicted transition proxies");
  });
});
