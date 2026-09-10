import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./map-view.css";
import {
  cameraSequence,
  featuredTrajectory,
  minimumAssociationScore,
  orderedPoints,
  trajectorySpanSeconds,
  visibleTrajectory,
  type CameraMapPayload,
  type MapCamera,
  type MapTrajectory,
  type TrajectoryMapPayload,
} from "./map-model";

interface MapViewProps {
  runId: string;
}

interface MapResponse<T> {
  data: T;
}

const TRAJECTORY_COLORS = [
  "#f28a50",
  "#5fc3df",
  "#9ed470",
  "#df6f91",
  "#b99af2",
  "#e8c463",
];
const REPLAY_DURATION_MS = 7000;

async function loadMapData<T>(url: URL, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { credentials: "include", signal });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Map request failed (${response.status})${body ? `: ${body}` : ""}`);
  }
  return ((await response.json()) as MapResponse<T>).data;
}

function tooltip(content: string): HTMLElement {
  const element = document.createElement("span");
  element.textContent = content;
  return element;
}

function cameraIcon(): L.DivIcon {
  return L.divIcon({
    className: "road-map-camera-marker",
    html: '<span aria-hidden="true"><i></i></span>',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    tooltipAnchor: [0, -17],
  });
}

function vehicleIcon(): L.DivIcon {
  return L.divIcon({
    className: "road-map-vehicle-marker",
    html: '<span aria-hidden="true"></span>',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

function sequenceIcon(sequence: number): L.DivIcon {
  return L.divIcon({
    className: "road-map-sequence-marker",
    html: `<span>${sequence}</span>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    tooltipAnchor: [0, -14],
  });
}

function fitMap(map: L.Map, cameras: MapCamera[], trajectories: MapTrajectory[]): void {
  const positions = trajectories.flatMap((trajectory) =>
    trajectory.points.map(
      (point) => [point.latitude, point.longitude] as [number, number],
    ),
  );
  const fallback = cameras.map(
    (camera) => [camera.latitude, camera.longitude] as [number, number],
  );
  const bounds = positions.length ? positions : fallback;
  if (bounds.length === 1) {
    map.setView(bounds[0], 16);
  } else if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [90, 90], maxZoom: 19 });
  }
}

export function MapView({ runId }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const overlayRef = useRef<L.LayerGroup | null>(null);
  const [cameraData, setCameraData] = useState<CameraMapPayload | null>(null);
  const [trajectoryData, setTrajectoryData] = useState<TrajectoryMapPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tileErrors, setTileErrors] = useState(0);
  const [selectedVehicle, setSelectedVehicle] = useState("");
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"static" | "replay">("static");
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!runId) {
      setCameraData(null);
      setTrajectoryData(null);
      return;
    }
    const controller = new AbortController();
    const cameraUrl = new URL("/v1/map/cameras", window.location.origin);
    const trajectoryUrl = new URL("/v1/map/trajectories", window.location.origin);
    cameraUrl.searchParams.set("run_id", runId);
    trajectoryUrl.searchParams.set("run_id", runId);
    trajectoryUrl.searchParams.set("multi_camera_only", "true");
    trajectoryUrl.searchParams.set("limit", "200");
    setLoading(true);
    setError("");
    setCameraData(null);
    setTrajectoryData(null);
    Promise.all([
      loadMapData<CameraMapPayload>(cameraUrl, controller.signal),
      loadMapData<TrajectoryMapPayload>(trajectoryUrl, controller.signal),
    ])
      .then(([cameras, trajectories]) => {
        setCameraData(cameras);
        setTrajectoryData(trajectories);
        setSelectedVehicle(featuredTrajectory(trajectories.trajectories)?.vehicle_id ?? "");
        setMode("static");
        setProgress(0);
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : String(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [runId]);

  const trajectories = trajectoryData?.trajectories ?? [];
  const rankedTrajectories = useMemo(
    () =>
      [...trajectories].sort(
        (left, right) =>
          right.camera_count - left.camera_count || right.point_count - left.point_count,
      ),
    [trajectories],
  );
  const selected = useMemo(
    () => trajectories.find((trajectory) => trajectory.vehicle_id === selectedVehicle) ?? null,
    [selectedVehicle, trajectories],
  );
  const displayedTrajectories = useMemo(
    () => (selected ? [selected] : trajectories),
    [selected, trajectories],
  );
  const filteredTrajectories = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return rankedTrajectories;
    return rankedTrajectories.filter(
      (trajectory) =>
        trajectory.vehicle_id.toLowerCase().includes(normalized) ||
        trajectory.predicted_plate?.toLowerCase().includes(normalized),
    );
  }, [query, rankedTrajectories]);

  useEffect(() => {
    if (!containerRef.current || !cameraData || mapRef.current) return;
    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
    });
    const tiles = L.tileLayer(cameraData.tile_source.url, {
      attribution: cameraData.tile_source.attribution,
      maxZoom: 19,
      crossOrigin: true,
    });
    tiles.on("tileerror", () => setTileErrors((count) => count + 1));
    tiles.addTo(map);
    overlayRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    fitMap(map, cameraData.cameras, trajectories);
    window.setTimeout(() => map.invalidateSize(), 0);
    return () => {
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
  }, [cameraData, trajectories]);

  useEffect(() => {
    const map = mapRef.current;
    const overlays = overlayRef.current;
    if (!map || !overlays || !cameraData) return;
    overlays.clearLayers();

    for (const camera of cameraData.cameras) {
      const marker = L.marker([camera.latitude, camera.longitude], {
        icon: cameraIcon(),
        keyboard: true,
        title: camera.label,
        zIndexOffset: 600,
      });
      marker.bindTooltip(
        tooltip(`${camera.label} · ${camera.location_description} · approximate position`),
        { direction: "top", opacity: 0.95 },
      );
      marker.addTo(overlays);
    }

    displayedTrajectories.forEach((trajectory, index) => {
      const color = selected ? "#ff8b4d" : TRAJECTORY_COLORS[index % TRAJECTORY_COLORS.length];
      const ordered = orderedPoints(trajectory.points);
      const visible =
        mode === "replay" && selected
          ? visibleTrajectory(ordered, progress)
          : visibleTrajectory(ordered, 1);
      if (visible.positions.length > 1) {
        const line = L.polyline(visible.positions, {
          color,
          weight: selected ? 6 : 3,
          opacity: selected ? 1 : 0.65,
          dashArray: selected ? "12 10" : "8 12",
          className: `road-map-trajectory-line${selected ? " road-map-trajectory-line--selected" : ""}`,
        });
        line.bindTooltip(
          tooltip(
            `${trajectory.predicted_plate || trajectory.vehicle_id} · ${trajectory.camera_count} cameras · predicted path`,
          ),
          { sticky: true },
        );
        line.on("click", () => {
          setSelectedVehicle(trajectory.vehicle_id);
          setMode("static");
          setPlaying(false);
          setProgress(0);
        });
        line.addTo(overlays);
      }
      if (selected) {
        ordered.forEach((point, pointIndex) => {
          const marker = L.marker([point.latitude, point.longitude], {
            icon: sequenceIcon(pointIndex + 1),
            keyboard: true,
            title: `${pointIndex + 1}. Camera ${point.camera_id}`,
            zIndexOffset: 800,
          });
          marker.bindTooltip(
            tooltip(
              `${pointIndex + 1}. Camera ${point.camera_id} · observed ${point.first_observed_s.toFixed(1)}–${point.last_observed_s.toFixed(1)}s`,
            ),
            { direction: "top", opacity: 0.95 },
          );
          marker.addTo(overlays);
        });
      }
      if (mode === "replay" && selected && visible.currentPosition) {
        L.marker(visible.currentPosition, {
          icon: vehicleIcon(),
          zIndexOffset: 1000,
          title: selected.predicted_plate || selected.vehicle_id,
        }).addTo(overlays);
      }
    });
  }, [cameraData, displayedTrajectories, mode, progress, selected]);

  useEffect(() => {
    if (!mapRef.current || !cameraData) return;
    fitMap(mapRef.current, cameraData.cameras, displayedTrajectories);
  }, [cameraData, displayedTrajectories, selectedVehicle]);

  useEffect(() => {
    if (!playing || mode !== "replay" || !selected) return;
    const startedAt = performance.now() - progress * REPLAY_DURATION_MS;
    let frame = 0;
    const tick = (now: number) => {
      const next = Math.min(1, (now - startedAt) / REPLAY_DURATION_MS);
      setProgress(next);
      if (next < 1) {
        frame = requestAnimationFrame(tick);
      } else {
        setPlaying(false);
      }
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [mode, playing, selected]);

  function chooseTrajectory(vehicleId: string) {
    setSelectedVehicle(vehicleId);
    setMode("static");
    setPlaying(false);
    setProgress(0);
  }

  function startReplay() {
    const vehicle = selected ?? trajectories[0];
    if (!vehicle) return;
    setSelectedVehicle(vehicle.vehicle_id);
    setMode("replay");
    setProgress(0);
    setPlaying(true);
  }

  if (!runId) {
    return (
      <section className="road-map-page road-map-state" aria-labelledby="map-view-title">
        <h1 id="map-view-title">Trajectory Map</h1>
        <p>Choose a delivered run to load camera nodes and vehicle trajectories.</p>
      </section>
    );
  }

  return (
    <section className="road-map-page" aria-labelledby="map-view-title">
      <header className="road-map-header">
        <div>
          <span className="road-map-eyebrow">CITYFLOW TRAJECTORY VIEW</span>
          <h1 id="map-view-title">U.S. Camera Network Map</h1>
          <p>
            Frozen CityFlow S02 camera observations shown over their approximate U.S. road
            context. Connectors follow observation order; they are not road-snapped GPS tracks.
          </p>
        </div>
        <div className="road-map-status" aria-label="Map data status">
          <span>{cameraData?.scenario ?? "Loading scenario"}</span>
          <strong>{trajectoryData?.prediction_status ?? "LOADING"}</strong>
        </div>
      </header>

      {error && (
        <div className="road-map-message road-map-message--error" role="alert">
          <strong>Map data could not be loaded.</strong>
          <span>{error}</span>
        </div>
      )}
      {loading && (
        <div className="road-map-message" role="status">
          Loading camera nodes and frozen trajectory predictions…
        </div>
      )}
      {tileErrors > 0 && (
        <div className="road-map-message road-map-message--warning" role="status">
          Some OpenStreetMap tiles are unavailable. Camera nodes and trajectory overlays remain usable.
        </div>
      )}

      <div className="road-map-layout">
        <aside className="road-map-panel" aria-label="Trajectory controls">
          <div className="road-map-panel-heading">
            <div>
              <span>Tracked journeys</span>
              <strong>{trajectories.length}</strong>
            </div>
            <button
              type="button"
              className="road-map-clear"
              onClick={() => chooseTrajectory("")}
              disabled={!selectedVehicle}
            >
              Show all
            </button>
          </div>

          <label className="road-map-search">
            <span>Find vehicle or predicted plate</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="RoadEye ID or plate"
            />
          </label>

          {selected && (
            <section className="road-map-route-card" aria-label="Selected vehicle route">
              <span>Selected camera sequence</span>
              <strong>{cameraSequence(selected)}</strong>
              <dl>
                <div>
                  <dt>Observed span</dt>
                  <dd>{trajectorySpanSeconds(selected).toFixed(1)}s</dd>
                </div>
                <div>
                  <dt>Lowest ReID link</dt>
                  <dd>
                    {minimumAssociationScore(selected)?.toFixed(3) ?? "N/A"}
                    <small> uncalibrated</small>
                  </dd>
                </div>
              </dl>
            </section>
          )}

          <div className="road-map-list" aria-label="Available trajectories">
            {!loading && !error && filteredTrajectories.length === 0 && (
              <p className="road-map-empty">No multi-camera trajectories match this filter.</p>
            )}
            {filteredTrajectories.map((trajectory) => (
              <button
                type="button"
                key={trajectory.vehicle_id}
                className={`road-map-vehicle${trajectory.vehicle_id === selectedVehicle ? " active" : ""}`}
                onClick={() => chooseTrajectory(trajectory.vehicle_id)}
                aria-pressed={trajectory.vehicle_id === selectedVehicle}
              >
                <span>
                  <strong>{trajectory.predicted_plate || "Plate unavailable"}</strong>
                  <small>{trajectory.vehicle_id}</small>
                </span>
                <em>{trajectory.camera_count} cameras</em>
              </button>
            ))}
          </div>

          <div className="road-map-replay">
            <div className="road-map-replay-actions">
              <button type="button" onClick={startReplay} disabled={!trajectories.length}>
                Replay selected
              </button>
              <button
                type="button"
                onClick={() => setPlaying((value) => !value)}
                disabled={mode !== "replay" || progress >= 1}
              >
                {playing ? "Pause" : "Resume"}
              </button>
            </div>
            <label>
              <span>Replay progress</span>
              <output>{Math.round(progress * 100)}%</output>
              <input
                type="range"
                min="0"
                max="100"
                value={Math.round(progress * 100)}
                onChange={(event) => {
                  setMode("replay");
                  setPlaying(false);
                  setProgress(Number(event.target.value) / 100);
                }}
                disabled={!selected}
              />
            </label>
          </div>
        </aside>

        <div className="road-map-canvas-wrap">
          <div ref={containerRef} className="road-map-canvas" aria-label="OpenStreetMap trajectory visualization" />
          {cameraData && (
            <div className="road-map-location" aria-label="Approximate map location">
              <strong>{cameraData.location_label}</strong>
              <span>
                {cameraData.approximate_center.latitude.toFixed(6)}, {cameraData.approximate_center.longitude.toFixed(6)}
                {cameraData.location_country ? ` · ${cameraData.location_country}` : ""}
              </span>
            </div>
          )}
          {!loading && !error && trajectories.length === 0 && (
            <div className="road-map-overlay-empty">
              No multi-camera trajectories are available for this run.
            </div>
          )}
          <div className="road-map-legend" aria-label="Map legend">
            <span><i className="road-map-legend-camera" /> Camera node</span>
            <span><i className="road-map-legend-path" /> Predicted direction</span>
          </div>
        </div>
      </div>

      <footer className="road-map-notice">
        <span>© OpenStreetMap contributors · ODbL</span>
        <span>{cameraData?.coordinate_notice ?? "Coordinates are approximate."}</span>
        <span>Numbered points are camera visits. Animated dashes show predicted direction, not a verified road route or measured speed.</span>
      </footer>
    </section>
  );
}
