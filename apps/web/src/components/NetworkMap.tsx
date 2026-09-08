import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import type { EvidenceSelectionHandler } from "../evidence";
import type { CameraDensityRow, CameraPosition, DemoStatus, Journey } from "../api.generated";
import { IconLayers } from "./Icons";
import { StatusBadge } from "./StatusBadge";

interface MapCamera extends CameraPosition {
  readonly id: string;
  readonly x: number;
  readonly y: number;
}

interface MapLink {
  readonly source: string;
  readonly target: string;
  readonly elapsed_seconds: number | null;
}

interface MapVisit {
  readonly id: string;
  readonly camera_id: string;
  readonly visitIndex: number;
  readonly sequence: number;
}

export function buildJourneyMapModel(
  journey: Journey | null,
  status?: Pick<DemoStatus, "camera_positions">,
) {
  const positions = new Map<string, CameraPosition>(Object.entries(status?.camera_positions ?? {}));
  for (const visit of journey?.visits ?? []) {
    if (!positions.has(visit.camera)) positions.set(visit.camera, visit.position);
  }
  const valid = [...positions].filter(([, point]) =>
    Number.isFinite(point.latitude) && Number.isFinite(point.longitude) &&
    Math.abs(point.latitude) <= 90 && Math.abs(point.longitude) <= 180,
  );
  const omittedCameraIds = [...positions.keys()].filter((id) => !valid.some(([key]) => key === id));
  const latitudeCenter = valid.length ? valid.reduce((sum, [, p]) => sum + p.latitude, 0) / valid.length : 0;
  const longitudeScale = Math.max(0.001, Math.cos(latitudeCenter * Math.PI / 180));
  const coordinates = valid.map(([id, position]) => ({
    id, position, east: position.longitude * longitudeScale, north: position.latitude,
  }));
  const east = coordinates.map((p) => p.east);
  const north = coordinates.map((p) => p.north);
  const minEast = east.length ? Math.min(...east) : 0;
  const maxEast = east.length ? Math.max(...east) : 0;
  const minNorth = north.length ? Math.min(...north) : 0;
  const maxNorth = north.length ? Math.max(...north) : 0;
  const width = maxEast - minEast;
  const height = maxNorth - minNorth;
  const scale = width === 0 && height === 0 ? 1 : Math.min(
    width === 0 ? Infinity : 490 / width,
    height === 0 ? Infinity : 190 / height,
  );
  const cameras: MapCamera[] = coordinates.map(({ id, position, east, north }) => ({
    id, ...position,
    x: 300 + (east - (minEast + maxEast) / 2) * scale,
    y: 130 - (north - (minNorth + maxNorth) / 2) * scale,
  }));
  const links: MapLink[] = [];
  (journey?.visits ?? []).forEach((visit, index) => {
    const interpolation = visit.interpolation_from_previous;
    const previous = journey?.visits[index - 1];
    if (interpolation && previous &&
        interpolation.from_camera === previous.camera &&
        interpolation.to_camera === visit.camera) {
      links.push({
        source: interpolation.from_camera, target: interpolation.to_camera,
        elapsed_seconds: visit.incoming_link?.temporal_gap_s ?? null,
      });
    }
  });
  const nodes: MapVisit[] = (journey?.visits ?? []).map((visit, visitIndex) => ({
    id: (journey?.global_id ?? "") + ":" + visitIndex,
    camera_id: visit.camera, visitIndex, sequence: visit.sequence,
  }));
  return { cameras, links, nodes, omittedCameraIds };
}

interface NetworkMapProps {
  readonly onSelectEvidence?: EvidenceSelectionHandler;
  readonly journey?: Journey;
  readonly status?: Pick<DemoStatus, "camera_positions">;
  readonly cameraCounts?: readonly CameraDensityRow[];
  readonly height?: number;
}

export function NetworkMap({ journey, status, cameraCounts = [], height = 420, onSelectEvidence }: NetworkMapProps) {
  const [showInferred, setShowInferred] = useState(true);
  const patternId = useId();
  const arrowId = useId();
  const model = buildJourneyMapModel(journey ?? null, status);
  const byCamera = new Map(model.cameras.map((camera) => [camera.id, camera]));
  const counts = new Map(cameraCounts.map((row) => [row.camera, row.observed_runtime_visit_count]));
  const maximumCount = Math.max(1, ...counts.values());

  return (
    <div className="network-map-container" style={{ minHeight: height }}>
      <div className="map-toolbar">
        <div className="map-title-group">
          <IconLayers size={16} />
          <span className="map-title">Approximate camera positions</span>
          <StatusBadge status="uncertain" label="UNVERIFIED journey" size="sm" />
        </div>
        <div className="map-legend">
          <span className="legend-item"><span className="legend-indicator dot-observed" />Observed camera visit</span>
          <label className="legend-item">
            <input type="checkbox" checked={showInferred} onChange={(event) => setShowInferred(event.target.checked)} />
            <span className="legend-indicator line-inferred" />Inferred straight connectors
          </label>
        </div>
      </div>
      {model.omittedCameraIds.length > 0 && (
        <p className="status-banner banner-danger" role="alert">
          Unavailable camera positions: {model.omittedCameraIds.join(", ")}. Their geometry is omitted.
        </p>
      )}
      {model.cameras.length === 0 ? <p className="empty-text">No usable camera positions are available.</p> : (
        <div className="map-canvas-wrapper">
          <svg viewBox="0 0 600 260" className="network-svg" role="img" aria-label="Approximate camera positions with observed visits and inferred straight connectors">
            <defs>
              <pattern id={patternId} width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#1f2127" strokeWidth="1" />
              </pattern>
              <marker id={arrowId} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#8BAFC8" />
              </marker>
            </defs>
            <rect width="100%" height="100%" fill={"url(#" + patternId + ")"} />
            {showInferred && model.links.map((link, index) => {
              const from = byCamera.get(link.source);
              const to = byCamera.get(link.target);
              if (!from || !to) return null;
              return (
                <g key={index}>
                  <title>{link.source + " to " + link.target + ": inferred geometry; identity not scored in runtime"}</title>
                  <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#8BAFC8" strokeWidth="2.5" strokeDasharray="6 4" markerEnd={"url(#" + arrowId + ")"} />
                  {link.elapsed_seconds !== null && (
                    <text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 10 - (model.links.length > 2 ? (index % 3) * 32 : 0)} fill="#8BAFC8" fontSize="10" textAnchor="middle">
                      {"gap " + link.elapsed_seconds.toFixed(2) + " s"}
                    </text>
                  )}
                </g>
              );
            })}
            {model.cameras.map((camera) => {
              const visits = model.nodes.filter((node) => node.camera_id === camera.id);
              const count = counts.get(camera.id);
              const radius = count === undefined ? 16 : 10 + 12 * Math.sqrt(count / maximumCount);
              return (
                <g key={camera.id}>
                  <title>{camera.id + ": " + camera.kind + "; " + (count === undefined ? "runtime count unavailable" : count + " runtime visits")}</title>
                  <circle cx={camera.x} cy={camera.y} r={radius} fill={visits.length ? "#1e3328" : "#191A1E"} stroke={visits.length ? "#82B095" : "#96939D"} strokeWidth="2" />
                  <text x={camera.x} y={camera.y + 4} fill="#F3F0EB" fontSize="10" textAnchor="middle">{camera.id}</text>
                  <text x={camera.x} y={camera.y + 34} fill="#96939D" fontSize="9" textAnchor="middle">
                    {visits.length ? "Visit " + visits.map((visit) => visit.sequence).join(", ") : "Camera reference"}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      )}
      <p className="text-xs text-muted">
        Approximate reference positions. Dashed straight connectors are inferred geometry, not an observed route or continuous GPS track.
        {cameraCounts.length > 0 && " Circle size shows runtime visit counts, not traffic density."}
        {" Boundary gaps are not route travel times; identity links are not scored in runtime."}
      </p>
      {journey && (
        <ol className="map-visit-list" aria-label="Chronological camera visits">
          {journey.visits.map((visit, index) => (
            <li key={visit.tracklet_key + ":" + index}>
              <strong>{visit.camera}</strong>{" / "}{visit.first_observed_s.toFixed(2)} to {visit.last_observed_s.toFixed(2)} s
              {visit.evidence_samples.length > 0 && (
                onSelectEvidence ? (
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => onSelectEvidence({
                    globalId: journey.global_id, visitIndex: index, sampleIndex: 0,
                    cropSha256: visit.evidence_samples[0].crop_sha256,
                  })}>Inspect visit evidence</button>
                ) : <a href={api.evidenceFrameUrl(journey.global_id, index, 0)} target="_blank" rel="noreferrer">Open boxed frame</a>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function PredictionMapView({ onSelectEvidence }: { onSelectEvidence?: EvidenceSelectionHandler } = {}) {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const status = useQuery({ queryKey: ["demo-status"], queryFn: ({ signal }) => api.status({ signal }), staleTime: 60_000 });
  const analytics = useQuery({ queryKey: ["analytics"], queryFn: ({ signal }) => api.analytics({ signal }), staleTime: 60_000 });
  const catalog = useQuery({
    queryKey: ["map-vehicles", query],
    queryFn: ({ signal }) => api.vehicles({ q: query, multiCameraOnly: true, limit: 100 }, { signal }),
    staleTime: 60_000,
  });
  const vehicles = catalog.data ?? [];
  const globalId = vehicles.some((vehicle) => vehicle.global_id === selectedId) ? selectedId : vehicles[0]?.global_id;
  const journey = useQuery({
    queryKey: ["map-journey", globalId],
    queryFn: ({ signal }) => api.journey(globalId!, { signal }),
    enabled: Boolean(globalId), staleTime: 60_000,
  });

  return (
    <div className="view-container map-view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Prediction Network Map</h1>
          <p className="view-subtitle">Observed camera visits and explicitly inferred geometry from frozen predictions.</p>
        </div>
        <StatusBadge status="uncertain" label="UNVERIFIED / PREDICTION-ONLY" />
      </div>
      <div className="panel">
        {status.data && <p>{status.data.scenario}: {status.data.disclosure ?? status.data.evaluation_notice}</p>}
        <div className="map-selection-controls">
          <label>Filter RoadEye ID, tracklet, or camera
            <input className="scope-input mono" value={query} maxLength={160} onChange={(event) => { setQuery(event.target.value); setSelectedId(""); }} />
          </label>
          <label>Predicted journey (up to 100 matches)
            <select className="scope-input mono" value={globalId ?? ""} onChange={(event) => setSelectedId(event.target.value)} disabled={!vehicles.length}>
              {!vehicles.length && <option value="">No prediction selected</option>}
              {vehicles.map((vehicle) => <option key={vehicle.global_id} value={vehicle.global_id}>{vehicle.global_id + " / " + vehicle.camera_count + " cameras"}</option>)}
            </select>
          </label>
        </div>
        {(status.isPending || catalog.isPending || (globalId && journey.isPending)) && <p role="status">Loading map evidence...</p>}
        {[status.error, catalog.error, journey.error, analytics.error].filter(Boolean).map((error, index) => (
          <p className="status-banner banner-danger" role="alert" key={index}>{error?.message}</p>
        ))}
        {catalog.isSuccess && !vehicles.length && <p>No multi-camera predictions match this filter.</p>}
        {journey.data?.disclosure && <p>{journey.data.disclosure}</p>}
        <NetworkMap journey={journey.data} status={status.data} cameraCounts={analytics.data?.camera_density} height={480} onSelectEvidence={onSelectEvidence} />
      </div>
    </div>
  );
}
