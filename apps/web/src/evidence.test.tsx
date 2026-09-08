import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { EvidenceSample, Journey, PlateSearchResult } from "./api.generated";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { plateEvidenceSelection, resolveEvidence } from "./evidence";

const sample: EvidenceSample = {
  frame: 20, time_s: 2, bbox_xywh: [10, 20, 30, 40], crop_sha256: "b".repeat(64),
  crop_url: "/api/fixture/crop", source_frame_url: "/api/fixture/frame",
  baseline_score: { value: 0, kind: "uncalibrated_baseline_score", is_probability: false },
  plate_prediction: {
    predicted_plate_text: "KA01AB1234", normalized_plate_text: "KA01AB1234",
    ocr_score: 0, score_kind: "uncalibrated_ocr_model_score_not_probability",
    is_probability: false, prediction_status: "predicted_plate_text_not_ground_truth",
  },
};
const journey: Journey = {
  global_id: "roadeye_fixture", camera_count: 1, visit_count: 1,
  prediction_status: "predicted_not_runtime_ground_truth",
  disclosure: "Fixture prediction disclosure", geometry_status: "approximate",
  visits: [{
    sequence: 1, tracklet_key: "fixture/c1/track", camera: "c1",
    first_observed_s: 0, identified_at_s: 2, last_observed_s: 3,
    position: { latitude: 0, longitude: 0, kind: "approximate" },
    observation_status: "observed_camera_visit", incoming_link: null,
    interpolation_from_previous: null,
    evidence_samples: [{ ...sample, frame: 10, crop_sha256: "a".repeat(64), plate_prediction: null }, sample],
  }],
};
const match: PlateSearchResult = {
  global_id: journey.global_id, journey_url: "/api/vehicles/roadeye_fixture",
  visit_index: 0, sample_index: 1, tracklet_key: "fixture/c1/track", camera: "c1",
  observed_s: sample.time_s, crop_sha256: sample.crop_sha256, crop_url: sample.crop_url,
  predicted_plate_text: "KA01AB1234", normalized_plate_text: "KA01AB1234",
  match_kind: "exact", ocr_score: 0,
  score_kind: "uncalibrated_ocr_model_score_not_probability",
  is_probability: false, prediction_status: "predicted_plate_text_not_ground_truth",
};
const selection = plateEvidenceSelection(match);

describe("exact evidence selection", () => {
  it("opens the matched nonzero OCR sample instead of falling back to the first crop", () => {
    const result = resolveEvidence(journey, selection);
    expect(selection.sampleIndex).toBe(1);
    expect(result.sample.frame).toBe(20);
    expect(result.sample.crop_sha256).toBe(match.crop_sha256);
  });

  it("rejects invalid, missing, wrong-journey and hash-mismatched evidence", () => {
    expect(() => resolveEvidence(journey, { ...selection, visitIndex: -1 })).toThrow("Invalid evidence selection");
    expect(() => resolveEvidence(journey, { ...selection, sampleIndex: 0.5 })).toThrow("Invalid evidence selection");
    expect(() => resolveEvidence(journey, { ...selection, visitIndex: 8 })).toThrow("visit is unavailable");
    expect(() => resolveEvidence(journey, { ...selection, sampleIndex: 8 })).toThrow("sample is unavailable");
    expect(() => resolveEvidence(journey, { ...selection, globalId: "wrong" })).toThrow("journey ID does not match");
    expect(() => resolveEvidence(journey, { ...selection, cropSha256: "c".repeat(64) })).toThrow("SHA-256 does not match");
  });

  it("renders the exact evidence URLs, zero scores, provenance and prediction labels", () => {
    const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
    client.setQueryData(["drawer-evidence", selection.globalId, 0, 1, selection.cropSha256], resolveEvidence(journey, selection));
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <EvidenceDrawer selection={selection} onClose={() => {}} />
      </QueryClientProvider>,
    );
    expect(html).toContain("/api/vehicles/roadeye_fixture/visits/0/samples/1/crop");
    expect(html).toContain("/api/vehicles/roadeye_fixture/visits/0/samples/1/frame");
    expect(html).toContain(sample.crop_sha256);
    expect(html).toContain("KA01AB1234");
    expect(html).toContain("0.000");
    expect(html).toContain("UNVERIFIED / NOT GROUND TRUTH");
    expect(html).toContain("not a probability");
    expect(html).not.toContain("/v1");
    expect(html).not.toContain("Review Workbench");
    expect(html).not.toContain("Calibrated Score");
  });

  it("keeps a closed drawer empty and invalid selection explicit", () => {
    const client = new QueryClient();
    const render = (selected: typeof selection | null) => renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <EvidenceDrawer selection={selected} onClose={() => {}} />
      </QueryClientProvider>,
    );
    expect(render(null)).toBe("");
    expect(render({ ...selection, sampleIndex: -1 })).toContain("Invalid evidence selection.");
  });
});
