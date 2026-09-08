import { type FormEvent, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import type {
  PlateSearchResult,
  VehicleSummary,
} from "../api.generated";
import { IconAlertTriangle, IconClock, IconSearch } from "../components/Icons";
import { NetworkMap } from "../components/NetworkMap";
import { StatusBadge } from "../components/StatusBadge";

type SearchMode = "plate" | "vehicle";

interface SubmittedSearch {
  readonly mode: SearchMode;
  readonly query: string;
}

interface SearchCandidate {
  readonly key: string;
  readonly globalId: string;
  readonly title: string;
  readonly detail: string;
  readonly cropUrl: string;
  readonly annotation: string;
}


function formatSeconds(value: number): string {
  return `${value.toFixed(2)} s`;
}

function formatScore(value: number | null): string {
  return value === null ? "not available" : value.toFixed(3);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The read-only API request failed.";
}

function vehicleCandidate(vehicle: VehicleSummary): SearchCandidate {
  return {
    key: vehicle.global_id,
    globalId: vehicle.global_id,
    title: vehicle.global_id,
    detail: `${vehicle.camera_count} cameras / ${vehicle.visit_count} visits / ${formatSeconds(vehicle.first_observed_s)}-${formatSeconds(vehicle.last_observed_s)}`,
    cropUrl: vehicle.representative_crop_url,
    annotation: "Predicted identity; not runtime ground truth",
  };
}

function plateCandidate(result: PlateSearchResult): SearchCandidate {
  return {
    key: `${result.global_id}:${result.visit_index}:${result.sample_index}`,
    globalId: result.global_id,
    title: result.predicted_plate_text,
    detail: `${result.match_kind} match / ${result.camera} at ${formatSeconds(result.observed_s)} / ${result.global_id}`,
    cropUrl: result.crop_url,
    annotation: `OCR score ${result.ocr_score.toFixed(3)}; uncalibrated, not a probability`,
  };
}

export function TrajectoryView() {
  const [mode, setMode] = useState<SearchMode>("plate");
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState<SubmittedSearch | null>(null);
  const [selectedGlobalId, setSelectedGlobalId] = useState<string | null>(null);

  const demoStatusQuery = useQuery({
    queryKey: ["trajectory", "demo-status"],
    queryFn: ({ signal }) => api.status({ signal }),
  });
  const plateStatusQuery = useQuery({
    queryKey: ["trajectory", "plate-search-status"],
    queryFn: ({ signal }) => api.plateSearchStatus({ signal }),
  });
  const plateResultsQuery = useQuery({
    queryKey: [
      "trajectory",
      "plate-results",
      submitted?.mode === "plate" ? submitted.query : "",
    ],
    enabled: submitted?.mode === "plate",
    queryFn: ({ signal }) =>
      api.searchPlates({ q: submitted?.query ?? "", limit: 25 }, { signal }),
  });
  const vehicleResultsQuery = useQuery({
    queryKey: [
      "trajectory",
      "vehicle-results",
      submitted?.mode === "vehicle" ? submitted.query : "",
    ],
    enabled: submitted?.mode === "vehicle",
    queryFn: ({ signal }) =>
      api.vehicles(
        { q: submitted?.query ?? "", multiCameraOnly: false, limit: 25 },
        { signal },
      ),
  });

  const candidates = useMemo(() => {
    if (submitted?.mode === "plate") {
      return (plateResultsQuery.data?.results ?? []).map(plateCandidate);
    }
    if (submitted?.mode === "vehicle") {
      return (vehicleResultsQuery.data ?? []).map(vehicleCandidate);
    }
    return [];
  }, [plateResultsQuery.data, submitted?.mode, vehicleResultsQuery.data]);

  const activeGlobalId = selectedGlobalId ?? candidates[0]?.globalId ?? null;
  const journeyQuery = useQuery({
    queryKey: ["trajectory", "journey", activeGlobalId],
    enabled: Boolean(activeGlobalId),
    queryFn: ({ signal }) => api.journey(activeGlobalId ?? "", { signal }),
  });

  const minimumPlateLength = plateStatusQuery.data?.minimum_query_length ?? 3;
  const trimmedQuery = query.trim();
  const plateSearchEnabled = plateStatusQuery.data?.enabled === true;
  const canSubmit =
    mode === "plate"
      ? plateSearchEnabled && trimmedQuery.length >= minimumPlateLength
      : trimmedQuery.length > 0;
  const searching = plateResultsQuery.isFetching || vehicleResultsQuery.isFetching;
  const activeSearchError =
    submitted?.mode === "plate" ? plateResultsQuery.error : vehicleResultsQuery.error;
  const journey = journeyQuery.data;

  function selectMode(nextMode: SearchMode): void {
    setMode(nextMode);
    setSubmitted(null);
    setSelectedGlobalId(null);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (!canSubmit) return;
    setSelectedGlobalId(null);
    setSubmitted({ mode, query: trimmedQuery });
  }

  return (
    <div className="view-container trajectory-view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Plate Search &amp; Predicted Trajectories</h1>
          <p className="view-subtitle">
            Search frozen OCR predictions or RoadEye IDs, then inspect the existing
            prediction evidence. This read-only view does not expose ground truth or
            writable review actions.
          </p>
        </div>
      </div>

      <div className="panel search-panel">
        <div className="trajectory-search-modes" role="group" aria-label="Search mode">
          <button
            type="button"
            className={`tab-btn ${mode === "plate" ? "active" : ""}`}
            aria-pressed={mode === "plate"}
            onClick={() => selectMode("plate")}
          >
            Predicted plate
          </button>
          <button
            type="button"
            className={`tab-btn ${mode === "vehicle" ? "active" : ""}`}
            aria-pressed={mode === "vehicle"}
            onClick={() => selectMode("vehicle")}
          >
            RoadEye ID / tracklet / camera
          </button>
        </div>

        <form onSubmit={submitSearch} className="trajectory-form">
          <label htmlFor="trajectory-query">
            {mode === "plate" ? "Predicted plate text" : "Prediction catalog query"}
          </label>
          <div className="trajectory-search-row">
            <input
              id="trajectory-query"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={mode === "plate" ? "e.g. KA01AB1234" : "RoadEye ID, tracklet, or camera"}
              className="scope-input mono trajectory-search-input"
              maxLength={mode === "plate" ? 32 : 160}
            />
            <button type="submit" className="btn btn-primary" disabled={!canSubmit || searching}>
              <IconSearch size={16} />
              <span>{searching ? "Searching..." : "Search predictions"}</span>
            </button>
          </div>
        </form>

        {mode === "plate" && plateStatusQuery.isPending && (
          <div className="status-banner banner-info">Checking the sealed OCR search index...</div>
        )}
        {mode === "plate" && plateStatusQuery.isError && (
          <div className="status-banner banner-danger">
            Plate-search readiness could not be loaded: {errorMessage(plateStatusQuery.error)}
          </div>
        )}
        {mode === "plate" && plateStatusQuery.data && (
          <div
            className={`status-banner ${plateSearchEnabled ? "banner-info" : "banner-danger"}`}
          >
            <strong>{plateStatusQuery.data.availability}</strong>
            {` / ${plateStatusQuery.data.index_entry_count} frozen predictions / minimum ${minimumPlateLength} characters. `}
            Predicted plate text is not ground truth; OCR scores are not probabilities.
            {plateStatusQuery.data.reason ? ` ${plateStatusQuery.data.reason}` : ""}
          </div>
        )}
        {activeSearchError && (
          <div className="status-banner banner-danger">{errorMessage(activeSearchError)}</div>
        )}
      </div>

      {submitted && !searching && !activeSearchError && (
        <div className="trajectory-result-layout">
          <section className="panel trajectory-search-results" aria-label="Prediction matches">
            <div className="trajectory-section-heading">
              <div>
                <h2 className="panel-title">Prediction matches</h2>
                <p className="text-xs text-muted">
                  {candidates.length} evidence {candidates.length === 1 ? "match" : "matches"}
                </p>
              </div>
              <StatusBadge status="uncertain" label="UNVERIFIED" size="sm" />
            </div>

            {candidates.length === 0 ? (
              <p className="empty-text">No frozen prediction matched this query.</p>
            ) : (
              <div className="trajectory-candidate-list">
                {candidates.map((candidate) => (
                  <button
                    type="button"
                    key={candidate.key}
                    className={`trajectory-candidate ${activeGlobalId === candidate.globalId ? "active" : ""}`}
                    onClick={() => setSelectedGlobalId(candidate.globalId)}
                  >
                    <img src={candidate.cropUrl} alt="Predicted vehicle evidence crop" />
                    <span className="trajectory-candidate-copy">
                      <strong className="mono">{candidate.title}</strong>
                      <span>{candidate.detail}</span>
                      <small>{candidate.annotation}</small>
                    </span>
                  </button>
                ))}
              </div>
            )}
          </section>

          <section className="trajectory-journey-column" aria-label="Selected predicted journey">
            {journeyQuery.isPending && activeGlobalId && (
              <div className="panel empty-state-panel">Loading prediction evidence...</div>
            )}
            {journeyQuery.isError && (
              <div className="panel status-banner banner-danger">
                {errorMessage(journeyQuery.error)}
              </div>
            )}
            {journey && (
              <>
                <div className="panel version-banner">
                  <div className="version-info">
                    <span className="version-tag mono">RoadEye ID: {journey.global_id}</span>
                    <StatusBadge status="uncertain" label="PREDICTED / NOT GROUND TRUTH" size="sm" />
                  </div>
                  <div className="disclaimer-tag">
                    <IconAlertTriangle size={14} />
                    <span>{journey.disclosure ?? "Prediction-only runtime evidence."}</span>
                  </div>
                </div>

                <div className="trajectory-split">
                  <div className="panel map-panel">
                    <NetworkMap
                      journey={journey}
                      status={demoStatusQuery.data}
                      height={400}
                    />
                    <p className="trajectory-map-disclosure text-xs text-muted">
                      Approximate camera positions; straight connectors are inferred and are not an
                      observed route or continuous GPS track.
                    </p>
                  </div>

                  <div className="panel timeline-panel">
                    <h3 className="panel-title">Observed camera visits</h3>
                    <div className="timeline-list">
                      {journey.visits.map((visit, visitIndex) => {
                        const sample = visit.evidence_samples[0];
                        return (
                          <div key={`${visit.tracklet_key}:${visit.sequence}`} className="timeline-item">
                            <div className="timeline-marker">
                              <span className="marker-ordinal mono">{visit.sequence}</span>
                            </div>
                            <div className="timeline-content">
                              <div className="timeline-top">
                                <span className="timeline-cam font-bold">{visit.camera}</span>
                                <StatusBadge status="observed" label="Observed visit" size="sm" />
                              </div>
                              <div className="timeline-time mono text-xs text-muted">
                                <IconClock size={12} />
                                {formatSeconds(visit.first_observed_s)}-{formatSeconds(visit.last_observed_s)}
                              </div>
                              <div className="timeline-meta">
                                <span className="mono">{visit.tracklet_key}</span>
                              </div>
                              {sample ? (
                                <div className="trajectory-sample">
                                  <img
                                    src={api.evidenceCropUrl(journey.global_id, visitIndex, 0)}
                                    alt={`Evidence crop for ${visit.camera}`}
                                  />
                                  <div>
                                    <p className="mono text-xs">SHA-256 {sample.crop_sha256}</p>
                                    {sample.plate_prediction ? (
                                      <p className="text-xs text-muted">
                                        Predicted plate: <strong className="mono text-copper">
                                          {sample.plate_prediction.predicted_plate_text}
                                        </strong>{" "}
                                        / score {sample.plate_prediction.ocr_score.toFixed(3)}, not a probability
                                      </p>
                                    ) : (
                                      <p className="text-xs text-muted">No plate prediction for this sample.</p>
                                    )}
                                    <a
                                      href={api.evidenceFrameUrl(journey.global_id, visitIndex, 0)}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="trajectory-evidence-link"
                                    >
                                      Open exact boxed source frame
                                    </a>
                                  </div>
                                </div>
                              ) : (
                                <p className="text-xs text-muted">No runtime evidence sample available.</p>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <div className="panel table-panel">
                  <h3 className="panel-title">Predicted association evidence</h3>
                  {journey.visits.every((visit) => visit.incoming_link === null) ? (
                    <p className="empty-text">This predicted journey has no cross-camera association.</p>
                  ) : (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>From tracklet</th>
                          <th>To tracklet</th>
                          <th>Boundary gap</th>
                          <th>Appearance</th>
                          <th>Ambiguity margin</th>
                          <th>Runtime verification</th>
                        </tr>
                      </thead>
                      <tbody>
                        {journey.visits.map((visit) =>
                          visit.incoming_link ? (
                            <tr key={`${visit.tracklet_key}:incoming`}>
                              <td className="mono">{visit.incoming_link.from_tracklet}</td>
                              <td className="mono">{visit.incoming_link.to_tracklet}</td>
                              <td className="mono">{formatSeconds(visit.incoming_link.temporal_gap_s)}</td>
                              <td className="mono">{formatScore(visit.incoming_link.appearance_similarity)}</td>
                              <td className="mono">{formatScore(visit.incoming_link.ambiguity_margin)}</td>
                              <td>
                                <StatusBadge status="uncertain" label="Not scored" size="sm" />
                              </td>
                            </tr>
                          ) : null,
                        )}
                      </tbody>
                    </table>
                  )}
                  <p className="text-xs text-muted trajectory-score-note">
                    Association and OCR values are uncalibrated model scores, not probabilities.
                    Boundary gaps are not route travel times.
                  </p>
                </div>
              </>
            )}
          </section>
        </div>
      )}

      {!submitted && (
        <div className="panel empty-state-panel">
          Search existing prediction data to inspect its journey and hash-bound evidence.
        </div>
      )}
    </div>
  );
}
