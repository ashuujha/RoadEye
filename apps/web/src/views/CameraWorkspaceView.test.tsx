import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { Journey, VehicleSummary } from "../api.generated";
import { CameraWorkspaceView } from "./CameraWorkspaceView";

const vehicles = [
  {
    global_id: "roadeye_fixture",
    camera_count: 2,
    cameras: ["c1", "c2"],
    visit_count: 1,
    first_observed_s: 1,
    last_observed_s: 2,
    representative_crop_url: "/api/representative.jpg",
    representative_tracklet: "validation/S02/c1/1",
    prediction_status: "predicted_not_runtime_ground_truth",
    disclosure: "Fixture prediction disclosure",
  },
] satisfies readonly VehicleSummary[];

const journey = {
  global_id: "roadeye_fixture",
  camera_count: 2,
  visit_count: 1,
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
      position: { latitude: 28.6, longitude: 77.2, kind: "approximate" },
      observation_status: "observed_camera_visit",
      evidence_samples: [
        {
          frame: 17,
          time_s: 1.5,
          bbox_xywh: [1, 2, 30, 40],
          crop_sha256: "a".repeat(64),
          crop_url: "/api/crop",
          source_frame_url: "/api/frame",
          baseline_score: {
            value: 0.82,
            kind: "uncalibrated_appearance_score_not_probability",
            is_probability: false,
          },
          plate_prediction: {
            predicted_plate_text: "KA01AB1234",
            normalized_plate_text: "KA01AB1234",
            ocr_score: 0.73,
            score_kind: "uncalibrated_ocr_model_score_not_probability",
            is_probability: false,
            prediction_status: "predicted_plate_text_not_ground_truth",
          },
        },
      ],
      incoming_link: null,
      interpolation_from_previous: null,
    },
  ],
} satisfies Journey;

describe("CameraWorkspaceView", () => {
  it("renders audited journey evidence without recorded-job controls", () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(["vehicles", "evidence", ""], vehicles);
    queryClient.setQueryData(["journey", "evidence", "roadeye_fixture"], journey);

    const html = renderToStaticMarkup(
      <QueryClientProvider client={queryClient}>
        <CameraWorkspaceView />
      </QueryClientProvider>,
    );

    expect(html).toContain("Audited Evidence Workspace");
    expect(html).toContain("roadeye_fixture");
    expect(html).toContain("KA01AB1234");
    expect(html).toContain("PREDICTED PLATE TEXT · NOT GROUND TRUTH");
    expect(html).not.toContain("Recorded Footage");
    expect(html).not.toContain("Upload");
  });
});
