import { type FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import type { EvidenceSelectionHandler } from "../evidence";
import type { EvidenceSample, JourneyVisit, VehicleSummary } from "../api.generated";
import { IconCamera, IconSearch, IconShield } from "../components/Icons";
import { StatusBadge } from "../components/StatusBadge";

const catalogLimit = 100;

function seconds(value: number): string {
  return `${value.toFixed(2)} s`;
}

function score(value: number): string {
  return value.toFixed(3);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function SampleCard({
  globalId,
  visitIndex,
  sampleIndex,
  sample,
  onSelectEvidence,
}: {
  globalId: string;
  visitIndex: number;
  sampleIndex: number;
  sample: EvidenceSample;
  onSelectEvidence?: EvidenceSelectionHandler;
}) {
  const cropUrl = api.evidenceCropUrl(globalId, visitIndex, sampleIndex);
  const frameUrl = api.evidenceFrameUrl(globalId, visitIndex, sampleIndex);

  return (
    <article className="panel evidence-sample-card">
      <div className="evidence-sample-heading">
        <div>
          <span className="meta-kicker">CAUSAL APPEARANCE SAMPLE {sampleIndex + 1}</span>
          <h4 className="panel-title">Frame {sample.frame}</h4>
        </div>
        <StatusBadge status="observed" label={`Observed ${seconds(sample.time_s)}`} size="sm" />
      </div>

      <div className="evidence-image-pair">
        <figure className="evidence-image-frame">
          <img
            src={cropUrl}
            alt={`Vehicle crop for ${globalId}, frame ${sample.frame}`}
            loading="lazy"
          />
          <figcaption>Hash-bound vehicle crop</figcaption>
        </figure>
        <figure className="evidence-image-frame">
          <img
            src={frameUrl}
            alt={`Boxed source frame for ${globalId}, frame ${sample.frame}`}
            loading="lazy"
          />
          <figcaption>Exact source frame with predicted box</figcaption>
        </figure>
      </div>

      {onSelectEvidence && (
        <button type="button" className="btn btn-secondary" onClick={() => onSelectEvidence({
          globalId, visitIndex, sampleIndex, cropSha256: sample.crop_sha256,
        })}>Inspect this sample in evidence drawer</button>
      )}

      <dl className="evidence-metadata-grid">
        <div>
          <dt>Bounding box (x, y, w, h)</dt>
          <dd className="mono">{sample.bbox_xywh.join(", ")}</dd>
        </div>
        <div>
          <dt>Crop SHA-256</dt>
          <dd className="mono evidence-hash" title={sample.crop_sha256}>
            {sample.crop_sha256}
          </dd>
        </div>
        <div>
          <dt>Appearance score</dt>
          <dd className="mono">{score(sample.baseline_score.value)}</dd>
        </div>
        <div>
          <dt>Score semantics</dt>
          <dd>{sample.baseline_score.kind} · not a probability</dd>
        </div>
      </dl>

      {sample.plate_prediction ? (
        <div className="evidence-ocr-panel">
          <div>
            <span className="meta-kicker">PREDICTED PLATE TEXT · NOT GROUND TRUTH</span>
            <strong className="mono evidence-plate">
              {sample.plate_prediction.predicted_plate_text}
            </strong>
          </div>
          <div className="text-right">
            <span className="meta-kicker">UNCALIBRATED OCR SCORE · NOT PROBABILITY</span>
            <strong className="mono">{score(sample.plate_prediction.ocr_score)}</strong>
          </div>
        </div>
      ) : (
        <p className="evidence-no-ocr">No usable runtime OCR prediction is linked to this sample.</p>
      )}
    </article>
  );
}

function VisitCard({
  globalId,
  visitIndex,
  visit,
  onSelectEvidence,
}: {
  globalId: string;
  visitIndex: number;
  visit: JourneyVisit;
  onSelectEvidence?: EvidenceSelectionHandler;
}) {
  return (
    <section className="evidence-visit-section">
      <div className="evidence-visit-heading">
        <div>
          <span className="meta-kicker">OBSERVED CAMERA VISIT {visit.sequence}</span>
          <h3 className="panel-title">{visit.camera}</h3>
          <span className="mono text-xs text-muted">{visit.tracklet_key}</span>
        </div>
        <div className="evidence-visit-badges">
          <StatusBadge status="observed" label="Observed camera visit" size="sm" />
          {visit.interpolation_from_previous && (
            <StatusBadge status="inferred" label="Straight-line interpolation" size="sm" />
          )}
        </div>
      </div>

      <div className="panel evidence-visit-metadata">
        <div>
          <span className="meta-kicker">OBSERVED WINDOW</span>
          <strong className="mono">
            {seconds(visit.first_observed_s)} – {seconds(visit.last_observed_s)}
          </strong>
        </div>
        <div>
          <span className="meta-kicker">IDENTIFIED AT</span>
          <strong className="mono">{seconds(visit.identified_at_s)}</strong>
        </div>
        <div>
          <span className="meta-kicker">APPROXIMATE POSITION</span>
          <strong className="mono">
            {visit.position.latitude.toFixed(5)}, {visit.position.longitude.toFixed(5)}
          </strong>
          <span className="text-xs text-muted">{visit.position.kind}</span>
        </div>
      </div>

      {visit.incoming_link && (
        <div className="panel incoming-evidence-panel">
          <div className="incoming-evidence-title">
            <IconShield size={16} />
            <strong>Incoming predicted association evidence</strong>
            <StatusBadge status="uncertain" label="Not scored in runtime" size="sm" />
          </div>
          <dl className="evidence-metadata-grid">
            <div>
              <dt>Appearance similarity</dt>
              <dd className="mono">{score(visit.incoming_link.appearance_similarity)}</dd>
            </div>
            <div>
              <dt>Second best / margin</dt>
              <dd className="mono">
                {visit.incoming_link.second_best_similarity === null
                  ? "Not available"
                  : score(visit.incoming_link.second_best_similarity)}
                {" / "}
                {visit.incoming_link.ambiguity_margin === null
                  ? "Not available"
                  : score(visit.incoming_link.ambiguity_margin)}
              </dd>
            </div>
            <div>
              <dt>Temporal / topology gate</dt>
              <dd>{visit.incoming_link.temporal_topology_reason}</dd>
            </div>
            <div>
              <dt>Gap / distance</dt>
              <dd className="mono">
                {seconds(visit.incoming_link.temporal_gap_s)} / {visit.incoming_link.distance_m.toFixed(1)} m
              </dd>
            </div>
          </dl>
          <p className="text-xs text-muted">
            {visit.incoming_link.score_kind}; values are uncalibrated scores, not probabilities.
          </p>
        </div>
      )}

      <div className="evidence-sample-grid">
        {visit.evidence_samples.map((sample, sampleIndex) => (
          <SampleCard
            key={`${sample.frame}-${sample.crop_sha256}`}
            globalId={globalId}
            visitIndex={visitIndex}
            sampleIndex={sampleIndex}
            sample={sample}
            onSelectEvidence={onSelectEvidence}
          />
        ))}
      </div>
    </section>
  );
}

export function CameraWorkspaceView({ onSelectEvidence }: { onSelectEvidence?: EvidenceSelectionHandler } = {}) {
  const [draftQuery, setDraftQuery] = useState("");
  const [catalogQuery, setCatalogQuery] = useState("");
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null);

  const vehiclesQuery = useQuery({
    queryKey: ["vehicles", "evidence", catalogQuery],
    queryFn: ({ signal }) =>
      api.vehicles(
        { q: catalogQuery, multiCameraOnly: true, limit: catalogLimit },
        { signal },
      ),
    staleTime: 60_000,
  });

  const vehicles = vehiclesQuery.data ?? [];
  const selectedGlobalId =
    (selectedVehicleId && vehicles.some((row) => row.global_id === selectedVehicleId)
      ? selectedVehicleId
      : vehicles[0]?.global_id) ?? null;

  const journeyQuery = useQuery({
    queryKey: ["journey", "evidence", selectedGlobalId],
    queryFn: ({ signal }) => api.journey(selectedGlobalId!, { signal }),
    enabled: selectedGlobalId !== null,
    staleTime: 60_000,
  });

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSelectedVehicleId(null);
    setCatalogQuery(draftQuery.trim());
  }

  return (
    <div className="view-container evidence-workspace-view">
      <div className="view-header evidence-workspace-header">
        <div>
          <h1 className="view-title">Audited Evidence Workspace</h1>
          <p className="view-subtitle">
            Inspect hash-bound vehicle crops, exact boxed source frames, and the evidence behind
            prediction-only multi-camera journeys.
          </p>
        </div>
        <div className="evidence-claim-badges">
          <StatusBadge status="uncertain" label="Predicted identity · not ground truth" />
          <StatusBadge status="observed" label="Read-only audited artifacts" />
        </div>
      </div>

      <div className="evidence-browser-layout">
        <aside className="panel evidence-catalog-panel" aria-label="Vehicle prediction catalog">
          <div className="panel-header">
            <div>
              <span className="meta-kicker">MULTI-CAMERA CATALOG</span>
              <h2 className="panel-title">RoadEye predictions</h2>
            </div>
            <IconCamera size={18} />
          </div>

          <form className="evidence-catalog-search" onSubmit={submitSearch}>
            <label htmlFor="evidence-catalog-query">
              RoadEye ID, tracklet, or camera
            </label>
            <div className="evidence-search-row">
              <input
                id="evidence-catalog-query"
                className="scope-input mono"
                value={draftQuery}
                onChange={(event) => setDraftQuery(event.target.value)}
                placeholder="e.g. c008/104"
                maxLength={160}
              />
              <button type="submit" className="btn btn-primary" disabled={vehiclesQuery.isFetching}>
                <IconSearch size={15} />
                Search
              </button>
            </div>
          </form>

          {vehiclesQuery.isPending ? (
            <div className="evidence-query-state" role="status">
              <div className="spinner" />
              Loading audited vehicle catalog…
            </div>
          ) : vehiclesQuery.error ? (
            <p className="status-banner banner-danger" role="alert">
              {errorMessage(vehiclesQuery.error)}
            </p>
          ) : vehicles.length === 0 ? (
            <p className="empty-text">No multi-camera predictions match this search.</p>
          ) : (
            <div className="evidence-vehicle-list">
              {vehicles.map((vehicle: VehicleSummary) => {
                const isSelected = vehicle.global_id === selectedGlobalId;
                return (
                  <button
                    type="button"
                    key={vehicle.global_id}
                    className={`evidence-vehicle-card ${isSelected ? "selected" : ""}`}
                    onClick={() => setSelectedVehicleId(vehicle.global_id)}
                    aria-pressed={isSelected}
                  >
                    <img
                      src={vehicle.representative_crop_url}
                      alt={`Representative crop for ${vehicle.global_id}`}
                      loading="lazy"
                    />
                    <span className="evidence-vehicle-copy">
                      <strong className="mono">{vehicle.global_id}</strong>
                      <span>{vehicle.cameras.join(" → ")}</span>
                      <span className="text-xs text-muted">
                        {vehicle.visit_count} visits · {seconds(vehicle.first_observed_s)} to{" "}
                        {seconds(vehicle.last_observed_s)}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </aside>

        <div className="evidence-journey-panel">
          {!selectedGlobalId ? (
            <div className="panel empty-state-panel">
              Select a vehicle prediction to inspect its evidence.
            </div>
          ) : journeyQuery.isPending ? (
            <div className="panel evidence-query-state" role="status">
              <div className="spinner" />
              Loading journey evidence…
            </div>
          ) : journeyQuery.error ? (
            <p className="status-banner banner-danger" role="alert">
              {errorMessage(journeyQuery.error)}
            </p>
          ) : journeyQuery.data ? (
            <>
              <div className="panel evidence-journey-summary">
                <div>
                  <span className="meta-kicker">ROADEYE PREDICTED IDENTITY</span>
                  <h2 className="mono">{journeyQuery.data.global_id}</h2>
                  <p>{journeyQuery.data.disclosure ?? "Runtime predictions are not ground truth."}</p>
                </div>
                <div className="evidence-summary-metrics">
                  <div>
                    <span className="meta-kicker">PREDICTED CAMERA SPAN</span>
                    <strong>{journeyQuery.data.camera_count}</strong>
                  </div>
                  <div>
                    <span className="meta-kicker">OBSERVED VISITS</span>
                    <strong>{journeyQuery.data.visit_count}</strong>
                  </div>
                  <div>
                    <span className="meta-kicker">GEOMETRY</span>
                    <strong>{journeyQuery.data.geometry_status}</strong>
                  </div>
                </div>
              </div>

              <div className="evidence-visit-list">
                {journeyQuery.data.visits.map((visit, visitIndex) => (
                  <VisitCard
                    key={visit.tracklet_key}
                    globalId={journeyQuery.data.global_id}
                    visitIndex={visitIndex}
                    visit={visit}
                    onSelectEvidence={onSelectEvidence}
                  />
                ))}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
