import React from "react";
import { IconClock, IconLayers } from "./Icons";

interface ScopeBarProps {
  runId: string;
  onRunChange: (id: string) => void;
  runs: Array<Record<string, any>>;
  start: string;
  end: string;
  onStartChange: (s: string) => void;
  onEndChange: (e: string) => void;
  cameras?: Array<Record<string, any>>;
  selectedCamera?: string;
  onCameraChange?: (cam: string) => void;
  sourceMode?: string;
  lastUpdated?: number;
  isFetching?: boolean;
}


export function ScopeBar({
  runId,
  onRunChange,
  runs,
  start,
  end,
  onStartChange,
  onEndChange,
  cameras = [],
  selectedCamera = "",
  onCameraChange,
  sourceMode,
  lastUpdated,
  isFetching,
}: ScopeBarProps) {
  return (
    <div className="scope-bar" role="toolbar" aria-label="Operational scope and filters">
      <div className="scope-filters">
        <div className="scope-field">
          <label htmlFor="scope-run-select">Selected Run</label>
          <select
            id="scope-run-select"
            value={runId}
            onChange={(e) => onRunChange(e.target.value)}
            className="scope-select"
          >
            <option value="">Select an active or historical run</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.scenario || "Scenario"} · {r.id.slice(0, 8)} ({r.state || "run"})
              </option>
            ))}
          </select>
        </div>

        {cameras.length > 0 && onCameraChange && (
          <div className="scope-field">
            <label htmlFor="scope-cam-select">Camera Scope</label>
            <select
              id="scope-cam-select"
              value={selectedCamera}
              onChange={(e) => onCameraChange(e.target.value)}
              className="scope-select"
            >
              <option value="">All cameras ({cameras.length})</option>
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} {c.zone_id ? `(${c.zone_id})` : ""}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="scope-field">
          <label htmlFor="scope-start-input">UTC Window Start</label>
          <input
            id="scope-start-input"
            type="text"
            value={start}
            onChange={(e) => onStartChange(e.target.value)}
            className="scope-input mono"
            placeholder="2026-01-15T08:00:00Z"
          />
        </div>

        <div className="scope-field">
          <label htmlFor="scope-end-input">UTC Window End</label>
          <input
            id="scope-end-input"
            type="text"
            value={end}
            onChange={(e) => onEndChange(e.target.value)}
            className="scope-input mono"
            placeholder="2026-01-15T09:00:00Z"
          />
        </div>
      </div>

      <div className="scope-status">
        {sourceMode && (
          <span className={`mode-pill ${sourceMode.includes("real") || sourceMode.includes("RECORDED") ? "mode-real" : "mode-synthetic"}`}>
            {sourceMode}
          </span>
        )}
        {lastUpdated ? (
          <span className="scope-timestamp" title="Refreshes automatically via query cache">
            <IconClock size={13} />
            <span>{isFetching ? "Syncing…" : new Date(lastUpdated).toLocaleTimeString()}</span>
          </span>
        ) : null}
      </div>
    </div>
  );
}
