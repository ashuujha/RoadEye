import React, { useState } from "react";
import { IconLayers } from "./Icons";

type RecordData = Record<string, any>;

interface NetworkMapProps {
  cameras: RecordData[];
  edges: RecordData[];
  links?: RecordData[];
  nodes?: RecordData[];
  rejectedLinks?: RecordData[];
  reviewCandidates?: RecordData[];
  selectedCameraId?: string;
  onSelectCamera?: (cameraId: string) => void;
  onSelectNode?: (observationId: string) => void;
  height?: number;
}

export function NetworkMap({
  cameras,
  edges,
  links = [],
  nodes = [],
  rejectedLinks = [],
  reviewCandidates = [],
  selectedCameraId,
  onSelectCamera,
  onSelectNode,
  height = 420,
}: NetworkMapProps) {
  const [showInferred, setShowInferred] = useState(true);
  const [showReview, setShowReview] = useState(true);
  const [showRejected, setShowRejected] = useState(false);

  // Default coordinate space: 600 x 260
  const viewBoxWidth = 600;
  const viewBoxHeight = 260;

  return (
    <div className="network-map-container" style={{ minHeight: `${height}px` }}>
      {/* Map Layer Controls & Discoverable Legend */}
      <div className="map-toolbar">
        <div className="map-title-group">
          <IconLayers size={16} />
          <span className="map-title">Network Topology & Journey Tracking</span>
          <span className="map-badge">Schematic Geometry</span>
        </div>

        <div className="map-legend">
          <label className="legend-item">
            <span className="legend-indicator dot-observed" />
            <span>Observed Sightings</span>
          </label>

          <label className="legend-item">
            <input
              type="checkbox"
              checked={showInferred}
              onChange={(e) => setShowInferred(e.target.checked)}
            />
            <span className="legend-indicator line-inferred" />
            <span>Inferred Link</span>
          </label>

          <label className="legend-item">
            <input
              type="checkbox"
              checked={showReview}
              onChange={(e) => setShowReview(e.target.checked)}
            />
            <span className="legend-indicator line-review" />
            <span>Review Link</span>
          </label>

          <label className="legend-item">
            <input
              type="checkbox"
              checked={showRejected}
              onChange={(e) => setShowRejected(e.target.checked)}
            />
            <span className="legend-indicator line-rejected" />
            <span>Rejected Link</span>
          </label>
        </div>
      </div>

      <div className="map-canvas-wrapper">
        <svg
          viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
          className="network-svg"
          role="img"
          aria-label="RoadEye network camera topology, observed nodes, and inferred connections"
        >
          <defs>
            {/* Grid background pattern */}
            <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
              <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#1f2127" strokeWidth="1" />
            </pattern>

            {/* Standard edge arrow */}
            <marker
              id="edge-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#3b3d47" />
            </marker>

            {/* Inferred link arrow (blue) */}
            <marker
              id="inferred-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#8BAFC8" />
            </marker>

            {/* Review link arrow (amber) */}
            <marker
              id="review-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#D2B477" />
            </marker>

            {/* Rejected link arrow (red) */}
            <marker
              id="rejected-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#D98689" />
            </marker>
          </defs>

          {/* Grid background */}
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* 1. Base Graph Edges (Directed Network Geometry) */}
          {edges.map((e) => {
            const a = cameras.find((c) => c.id === e.source);
            const b = cameras.find((c) => c.id === e.target);
            if (!a || !b) return null;

            return (
              <g key={`base-${e.source}-${e.target}`}>
                <line
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke="#2b2d37"
                  strokeWidth="2"
                  markerEnd="url(#edge-arrow)"
                />
              </g>
            );
          })}

          {/* 2. Inferred Links (Blue dashed) */}
          {showInferred &&
            links.map((l, idx) => {
              const a = cameras.find((c) => c.id === l.source);
              const b = cameras.find((c) => c.id === l.target);
              if (!a || !b) return null;

              return (
                <g key={`inferred-${idx}`} className="inferred-link-group">
                  <line
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    stroke="#8BAFC8"
                    strokeWidth="3.5"
                    strokeDasharray="6 4"
                    markerEnd="url(#inferred-arrow)"
                  />
                  {l.elapsed_seconds && (
                    <text
                      x={(a.x + b.x) / 2}
                      y={(a.y + b.y) / 2 - 8}
                      fill="#8BAFC8"
                      fontSize="10"
                      textAnchor="middle"
                      className="mono"
                    >
                      {Math.round(l.elapsed_seconds)}s
                    </text>
                  )}
                </g>
              );
            })}

          {/* 3. Review Candidate Links (Amber dotted) */}
          {showReview &&
            reviewCandidates.map((r, idx) => {
              const a = cameras.find((c) => c.id === r.source);
              const b = cameras.find((c) => c.id === r.target);
              if (!a || !b) return null;

              return (
                <line
                  key={`review-${idx}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke="#D2B477"
                  strokeWidth="2.5"
                  strokeDasharray="3 3"
                  markerEnd="url(#review-arrow)"
                />
              );
            })}

          {/* 4. Rejected Links (Red solid/dashed) */}
          {showRejected &&
            rejectedLinks.map((rej, idx) => {
              const a = cameras.find((c) => c.id === rej.source);
              const b = cameras.find((c) => c.id === rej.target);
              if (!a || !b) return null;

              return (
                <line
                  key={`rej-${idx}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke="#D98689"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                  markerEnd="url(#rejected-arrow)"
                />
              );
            })}

          {/* 5. Camera Nodes (Physical Sensors) */}
          {cameras.map((c) => {
            const isObserved = nodes.some((n) => n.camera_id === c.id);
            const isSelected = selectedCameraId === c.id;

            return (
              <g
                key={c.id}
                className="camera-node"
                onClick={() => onSelectCamera?.(c.id)}
                style={{ cursor: "pointer" }}
              >
                {/* Selection ring */}
                {isSelected && (
                  <circle
                    cx={c.x}
                    cy={c.y}
                    r="24"
                    fill="none"
                    stroke="#B8A3D7"
                    strokeWidth="2"
                    strokeDasharray="2 2"
                  />
                )}

                {/* Base camera outer circle */}
                <circle
                  cx={c.x}
                  cy={c.y}
                  r="18"
                  fill={isObserved ? "#1e3328" : "#191A1E"}
                  stroke={isObserved ? "#82B095" : "#454854"}
                  strokeWidth={isObserved ? "2.5" : "1.5"}
                />

                {/* Camera label */}
                <text
                  x={c.x}
                  y={c.y + 4}
                  textAnchor="middle"
                  fill={isObserved ? "#82B095" : "#F3F0EB"}
                  fontSize="11"
                  fontWeight="600"
                  className="mono"
                >
                  {c.id}
                </text>

                {/* Zone metadata */}
                <text
                  x={c.x}
                  y={c.y + 32}
                  textAnchor="middle"
                  fill="#96939D"
                  fontSize="10"
                >
                  {c.zone_id || ""}
                </text>
              </g>
            );
          })}

          {/* 6. Observed Nodes Sequence Badges (Numbered in green) */}
          {nodes.map((n, idx) => {
            const cam = cameras.find((c) => c.id === n.camera_id);
            if (!cam) return null;

            return (
              <g
                key={n.id || idx}
                className="observed-node-badge"
                onClick={() => onSelectNode?.(n.id)}
                style={{ cursor: "pointer" }}
              >
                {/* Numbered badge on top right of camera */}
                <circle
                  cx={cam.x + 14}
                  cy={cam.y - 14}
                  r="9"
                  fill="#82B095"
                  stroke="#111214"
                  strokeWidth="2"
                />
                <text
                  x={cam.x + 14}
                  y={cam.y - 11}
                  textAnchor="middle"
                  fill="#111214"
                  fontSize="10"
                  fontWeight="bold"
                  className="mono"
                >
                  {idx + 1}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="map-footnote">
        <span>Attribution: RoadEye Six-Camera Schematic Topology</span>
        <span>Observed nodes are confirmed camera sightings; dashed lines indicate algorithmic path inference.</span>
      </div>
    </div>
  );
}
