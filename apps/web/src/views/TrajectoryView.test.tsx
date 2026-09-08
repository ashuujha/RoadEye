import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { DemoStatus, Journey, PlateSearchStatus } from "../api.generated";
import { TrajectoryView } from "./TrajectoryView";
import { buildJourneyMapModel } from "../components/NetworkMap";

const plateSearchStatus = {
  status: "UNVERIFIED",
  availability: "READY",
  enabled: true,
  reason: null,
  index_entry_count: 200,
  minimum_query_length: 3,
  prediction_label: "predicted_plate_text_not_ground_truth",
  score_notice: "OCR scores are uncalibrated model scores, not probabilities.",
  claim_notice: "Predicted plate text is not ground truth.",
  source_prediction_sha256: "a".repeat(64),
  ocr_provenance: {},
} satisfies PlateSearchStatus;

const demoStatus = {
  status: "UNVERIFIED",
  disclosure: "Fixture disclosure",
  scope: "prediction_only",
  runtime_artifact_integrity: "PASS",
  scenario: "S02",
  vehicle_count: 1,
  predicted_link_count: 1,
  multi_camera_vehicle_count: 1,
  max_predicted_camera_count: 2,
  camera_count_distribution: { "2": 1 },
  camera_positions: {
    c1: { latitude: 28.6, longitude: 77.2, kind: "approximate" },
    c2: { latitude: 28.7, longitude: 77.4, kind: "approximate" },
  },
  position_status: "approximate_reference_positions",
  score_notice: "Scores are not probabilities.",
  geometry_notice: "Straight links are inferred.",
  evaluation_notice: "Ground truth is not exposed.",
  analytics_notice: "Prediction-only aggregates.",
  plate_search: plateSearchStatus,
} satisfies DemoStatus;

const journey = {
  global_id: "roadeye_fixture",
  camera_count: 2,
  visit_count: 2,
  prediction_status: "predicted_not_runtime_ground_truth",
  disclosure: "Fixture prediction disclosure",
  geometry_status: "approximate_reference_positions",
  visits: [
    {
      sequence: 1,
      tracklet_key: "validation/S02/c1/1",
      camera: "c1",
      first_observed_s: 1,
      identified_at_s: 1.5,
      last_observed_s: 2,
      position: demoStatus.camera_positions.c1,
      observation_status: "observed_camera_visit",
      evidence_samples: [],
      incoming_link: null,
      interpolation_from_previous: null,
    },
    {
      sequence: 2,
      tracklet_key: "validation/S02/c2/2",
      camera: "c2",
      first_observed_s: 8,
      identified_at_s: 8.5,
      last_observed_s: 9,
      position: demoStatus.camera_positions.c2,
      observation_status: "observed_camera_visit",
      evidence_samples: [],
      incoming_link: {
        from_tracklet: "validation/S02/c1/1",
        to_tracklet: "validation/S02/c2/2",
        appearance_similarity: 0.81,
        second_best_similarity: 0.74,
        ambiguity_margin: 0.07,
        distance_m: 100,
        temporal_gap_s: 6,
        temporal_topology_reason: "forward_time",
        decision_time_s: 8,
        score_kind: "uncalibrated_appearance_score_not_probability",
        is_probability: false,
        verification_status: "not_scored_in_runtime",
      },
      interpolation_from_previous: {
        status: "inferred_straight_line_not_observed_route",
        from_camera: "c1",
        to_camera: "c2",
        bearing_degrees: 45,
      },
    },
  ],
} satisfies Journey;

describe("TrajectoryView", () => {
  it("labels plate search as prediction-only and removes writable workflow controls", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Infinity } },
    });
    queryClient.setQueryData(["trajectory", "demo-status"], demoStatus);
    queryClient.setQueryData(["trajectory", "plate-search-status"], plateSearchStatus);

    const html = renderToStaticMarkup(
      <QueryClientProvider client={queryClient}>
        <TrajectoryView />
      </QueryClientProvider>,
    );

    expect(html).toContain("Plate Search &amp; Predicted Trajectories");
    expect(html).toContain("READY");
    expect(html).toContain("Predicted plate text is not ground truth");
    expect(html).not.toContain("Purpose Code");
    expect(html).not.toContain("Include Review Candidates");
    expect(html).not.toContain("/v1");
  });

  it("adapts typed journey visits into deterministic map records", () => {
    const model = buildJourneyMapModel(journey, demoStatus);

    expect(model.cameras).toHaveLength(2);
    expect(model.nodes.map((node) => node.camera_id)).toEqual(["c1", "c2"]);
    expect(model.links).toEqual([
      { source: "c1", target: "c2", elapsed_seconds: 6 },
    ]);
    expect(model.cameras.every((camera) => Number.isFinite(camera.x))).toBe(true);
    expect(model.cameras.every((camera) => Number.isFinite(camera.y))).toBe(true);
  });

  it("does not invent connectors when explicit interpolation evidence is absent", () => {
    const model = buildJourneyMapModel({
      ...journey,
      visits: journey.visits.map((visit) => ({ ...visit, interpolation_from_previous: null })),
    });
    expect(model.links).toEqual([]);
  });

  it("omits invalid camera coordinates and centers a single valid reference", () => {
    const model = buildJourneyMapModel(null, { camera_positions: {
      valid: { latitude: 0, longitude: 0, kind: "approximate" },
      invalid: { latitude: NaN, longitude: 0, kind: "approximate" },
    } });
    expect(model.omittedCameraIds).toEqual(["invalid"]);
    expect(model.cameras).toEqual([{ id: "valid", latitude: 0, longitude: 0, kind: "approximate", x: 300, y: 130 }]);
    expect(buildJourneyMapModel(null).cameras).toEqual([]);
  });
});
