import React, { useState } from "react";
import { RecordedVideo } from "../RecordedVideo";
import { StatusBadge } from "../components/StatusBadge";
import { IconCamera, IconVideo, IconClock } from "../components/Icons";

type RecordData = Record<string, any>;

interface CameraWorkspaceViewProps {
  actor: string;
  cameras: RecordData[];
  onSelectObservation?: (id: string) => void;
}

export function CameraWorkspaceView({
  actor,
  cameras,
  onSelectObservation,
}: CameraWorkspaceViewProps) {
  const [activeTab, setActiveTab] = useState<"recorded" | "network">("recorded");
  const [selectedCamera, setSelectedCamera] = useState<RecordData | null>(null);

  return (
    <div className="view-container camera-workspace-view">
      <div className="view-header">
        <div>
          <h1 className="view-title">Camera & Video Workspace</h1>
          <p className="view-subtitle">
            Recorded real-video inference, multi-camera topology directory, and independent evaluation labeling.
          </p>
        </div>

        {/* Sub-tabs */}
        <div className="tab-group" role="tablist">
          <button
            className={`tab-btn ${activeTab === "recorded" ? "active" : ""}`}
            onClick={() => setActiveTab("recorded")}
            role="tab"
            aria-selected={activeTab === "recorded"}
          >
            <IconVideo size={16} />
            <span>Recorded Footage (Real Inference)</span>
          </button>
          <button
            className={`tab-btn ${activeTab === "network" ? "active" : ""}`}
            onClick={() => setActiveTab("network")}
            role="tab"
            aria-selected={activeTab === "network"}
          >
            <IconCamera size={16} />
            <span>Enrolled Camera Network ({cameras.length})</span>
          </button>
        </div>
      </div>

      {activeTab === "recorded" ? (
        <div className="recorded-video-wrapper">
          {/* Embed the verified working RecordedVideo component with dark operations styling */}
          <RecordedVideo actor={actor} />
        </div>
      ) : (
        <div className="network-directory-wrapper">
          <div className="camera-grid">
            {cameras.map((c) => (
              <div
                key={c.id}
                className={`panel camera-card ${selectedCamera?.id === c.id ? "selected" : ""}`}
                onClick={() => setSelectedCamera(c)}
              >
                <div className="camera-card-header">
                  <div className="camera-card-id mono">{c.id}</div>
                  <StatusBadge status="observed" label="Active" size="sm" />
                </div>

                <div className="camera-card-body">
                  <div className="card-detail-row">
                    <span className="card-label">Zone</span>
                    <span className="card-val">{c.zone_id || "Central Corridor"}</span>
                  </div>
                  <div className="card-detail-row">
                    <span className="card-label">Schematic Coordinates</span>
                    <span className="card-val mono">
                      X: {c.x}, Y: {c.y}
                    </span>
                  </div>
                  <div className="card-detail-row">
                    <span className="card-label">Lanes Enrolled</span>
                    <span className="card-val">{c.lanes?.length || 1} calibrated lanes</span>
                  </div>
                  <div className="card-detail-row">
                    <span className="card-label">Sensor Type</span>
                    <span className="card-val">Fixed Optical ANPR (RGB)</span>
                  </div>
                </div>

                <div className="camera-card-footer">
                  <button className="btn btn-secondary btn-xs btn-block">
                    View Passage Stream
                  </button>
                </div>
              </div>
            ))}
          </div>

          {selectedCamera && (
            <div className="panel camera-detail-panel">
              <div className="panel-header">
                <h3 className="panel-title">
                  Camera Details: <span className="mono text-copper">{selectedCamera.id}</span>
                </h3>
                <span className="mono text-xs text-muted">Zone {selectedCamera.zone_id}</span>
              </div>

              <div className="camera-detail-content">
                <p>
                  Camera {selectedCamera.id} participates in the city-wide directed road graph. Sightings from this sensor are verified against upstream/downstream travel times to infer defensible vehicle paths.
                </p>
                <div className="camera-meta-grid">
                  <div className="meta-box">
                    <span className="meta-kicker">INGEST SPECIFICATION</span>
                    <div className="meta-line">Transport Cadence: <b>25.0 FPS</b></div>
                    <div className="meta-line">Inference Sampling: <b>4.0 FPS</b></div>
                    <div className="meta-line">Bounding Box Model: <b>RTMDet-tiny (Indian plates)</b></div>
                  </div>
                  <div className="meta-box">
                    <span className="meta-kicker">GOVERNANCE & AUDIT</span>
                    <div className="meta-line">Retention Period: <b>30 days (default)</b></div>
                    <div className="meta-line">Face Redaction: <b>Enabled by default</b></div>
                    <div className="meta-line">Access Constraint: <b>Role-authorized search only</b></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
