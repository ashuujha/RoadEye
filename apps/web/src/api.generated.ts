/**
 * Read-only TypeScript projection of the audited RoadEye demo API.
 *
 * Source of truth: the response builders and GET routes in
 * src/roadeye/demo.py, src/roadeye/analytics.py, and
 * src/roadeye/plate_search.py at backend checkpoint ff3a618.
 *
 * This deliberately excludes the discarded /v1 service, jobs, alerts,
 * watchlists, and writable review contracts. The small local /api auth and
 * health contract is declared directly in api.ts.
 */

export type ClaimStatus = "PASS" | "FAIL" | "UNVERIFIED";

export interface CameraPosition {
  readonly latitude: number;
  readonly longitude: number;
  readonly kind: string;
}

export interface OcrProvenance {
  readonly ocr_selection_report_sha256?: string;
  readonly sealed_ocr_test_report_sha256?: string;
  readonly runtime_ocr_manifest_sha256?: string;
  readonly [key: string]: unknown;
}

export interface PlateSearchStatus {
  readonly status: "UNVERIFIED";
  readonly availability: "READY" | "BLOCKED_PENDING_SEALED_OCR";
  readonly enabled: boolean;
  readonly reason: string | null;
  readonly index_entry_count: number;
  readonly minimum_query_length: number;
  readonly prediction_label: "predicted_plate_text_not_ground_truth";
  readonly score_notice: string;
  readonly claim_notice: string;
  readonly source_prediction_sha256: string;
  readonly ocr_provenance: OcrProvenance;
}

export interface DemoStatus {
  readonly status: ClaimStatus;
  readonly disclosure: string | null;
  readonly scope: string;
  readonly runtime_artifact_integrity: "PASS";
  readonly scenario: string;
  readonly vehicle_count: number;
  readonly predicted_link_count: number;
  readonly multi_camera_vehicle_count: number;
  readonly max_predicted_camera_count: number;
  readonly camera_count_distribution: Readonly<Record<string, number>>;
  readonly camera_positions: Readonly<Record<string, CameraPosition>>;
  readonly position_status: string;
  readonly score_notice: string;
  readonly geometry_notice: string;
  readonly evaluation_notice: string;
  readonly analytics_notice: string;
  readonly plate_search: PlateSearchStatus;
}

export interface VehicleSummary {
  readonly global_id: string;
  readonly camera_count: number;
  readonly cameras: readonly string[];
  readonly visit_count: number;
  readonly first_observed_s: number;
  readonly last_observed_s: number;
  readonly representative_crop_url: string;
  readonly representative_tracklet: string;
  readonly prediction_status: "predicted_not_runtime_ground_truth";
  readonly disclosure: string | null;
}

export interface BaselineScore {
  readonly value: number;
  readonly kind: string;
  readonly is_probability: false;
}

export interface PlatePrediction {
  readonly predicted_plate_text: string;
  readonly normalized_plate_text: string;
  readonly ocr_score: number;
  readonly score_kind: "uncalibrated_ocr_model_score_not_probability";
  readonly is_probability: false;
  readonly prediction_status: "predicted_plate_text_not_ground_truth";
}

export interface LinkEvidence {
  readonly from_tracklet: string;
  readonly to_tracklet: string;
  readonly appearance_similarity: number;
  readonly second_best_similarity: number | null;
  readonly ambiguity_margin: number | null;
  readonly distance_m: number;
  readonly temporal_gap_s: number;
  readonly temporal_topology_reason: string;
  readonly decision_time_s: number;
  readonly score_kind: string;
  readonly is_probability: false;
  readonly verification_status: "not_scored_in_runtime";
}

export interface EvidenceSample {
  readonly frame: number;
  readonly time_s: number;
  readonly bbox_xywh: readonly [number, number, number, number];
  readonly crop_sha256: string;
  readonly crop_url: string;
  readonly source_frame_url: string;
  readonly baseline_score: BaselineScore;
  readonly plate_prediction: PlatePrediction | null;
}

export interface JourneyInterpolation {
  readonly status: "inferred_straight_line_not_observed_route";
  readonly from_camera: string;
  readonly to_camera: string;
  readonly bearing_degrees: number;
}

export interface JourneyVisit {
  readonly sequence: number;
  readonly tracklet_key: string;
  readonly camera: string;
  readonly first_observed_s: number;
  readonly identified_at_s: number;
  readonly last_observed_s: number;
  readonly position: CameraPosition;
  readonly observation_status: "observed_camera_visit";
  readonly evidence_samples: readonly EvidenceSample[];
  readonly incoming_link: LinkEvidence | null;
  readonly interpolation_from_previous: JourneyInterpolation | null;
}

export interface Journey {
  readonly global_id: string;
  readonly camera_count: number;
  readonly visit_count: number;
  readonly prediction_status: "predicted_not_runtime_ground_truth";
  readonly disclosure: string | null;
  readonly geometry_status: string;
  readonly visits: readonly JourneyVisit[];
}

export interface AnalyticsSummary {
  readonly predicted_global_vehicle_ids: number;
  readonly multi_camera_predicted_vehicle_ids: number;
  readonly observed_runtime_visits: number;
  readonly predicted_transitions: number;
  readonly camera_count: number;
  readonly first_observed_s: number | null;
  readonly last_observed_s: number | null;
}

export interface CameraDensityRow {
  readonly camera: string;
  readonly observed_runtime_visit_count: number;
  readonly predicted_unique_vehicle_count: number;
  readonly multi_camera_predicted_vehicle_count: number;
  readonly share_of_observed_runtime_visits: number;
  readonly position: CameraPosition;
  readonly measurement_status: "runtime_prediction_visit_count_not_traffic_density";
}

export interface OriginDestinationRow {
  readonly origin_camera: string;
  readonly destination_camera: string;
  readonly predicted_vehicle_count: number;
  readonly share_of_multi_camera_predictions: number;
  readonly measurement_status: "predicted_endpoints_not_verified_od_flow";
}

export interface BottleneckProxyRow {
  readonly rank: number;
  readonly from_camera: string;
  readonly to_camera: string;
  readonly predicted_transition_count: number;
  readonly share_of_predicted_transitions: number;
  readonly median_observed_boundary_gap_s: number;
  readonly maximum_observed_boundary_gap_s: number;
  readonly measurement_status: "predicted_transition_support_not_congestion_or_route_time";
}

export interface AnalyticsClaimBoundaries {
  readonly uses_runtime_ground_truth: false;
  readonly counts_model_predicted_identities: true;
  readonly camera_density_is_traffic_volume: false;
  readonly origin_destination_is_verified_flow: false;
  readonly bottleneck_proxy_is_congestion: false;
  readonly boundary_gap_is_route_travel_time: false;
  readonly plate_or_owner_data_used: false;
}

export interface AnalyticsResponse {
  readonly schema_version: 1;
  readonly status: "UNVERIFIED";
  readonly scope: "prediction_only_aggregate_runtime_analytics";
  readonly scenario: string;
  readonly disclosure: string | null;
  readonly source_prediction_sha256: string;
  readonly summary: AnalyticsSummary;
  readonly camera_density: readonly CameraDensityRow[];
  readonly origin_destination_pairs: readonly OriginDestinationRow[];
  readonly bottleneck_proxies: readonly BottleneckProxyRow[];
  readonly claim_boundaries: AnalyticsClaimBoundaries;
}

export type PlateMatchKind = "exact" | "prefix" | "contains";

export interface PlateSearchResult {
  readonly global_id: string;
  readonly journey_url: string;
  readonly visit_index: number;
  readonly sample_index: number;
  readonly tracklet_key: string;
  readonly camera: string;
  readonly observed_s: number;
  readonly crop_sha256: string;
  readonly crop_url: string;
  readonly predicted_plate_text: string;
  readonly normalized_plate_text: string;
  readonly match_kind: PlateMatchKind;
  readonly ocr_score: number;
  readonly score_kind: "uncalibrated_ocr_model_score_not_probability";
  readonly is_probability: false;
  readonly prediction_status: "predicted_plate_text_not_ground_truth";
}

export interface PlateSearchResponse extends PlateSearchStatus {
  readonly query: string;
  readonly normalized_query: string;
  readonly result_count: number;
  readonly results: readonly PlateSearchResult[];
}

export interface FastApiValidationIssue {
  readonly loc: readonly (string | number)[];
  readonly msg: string;
  readonly type: string;
}

export interface ApiErrorPayload {
  readonly detail?: string | readonly FastApiValidationIssue[];
}
