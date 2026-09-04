import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { client, key, unwrap } from "./api";
import { Json, State } from "./components";
type RecordData = Record<string, any>;

export function RecordedVideo({ actor }: { actor: string }) {
  const qc = useQueryClient();
  const [runId, setRunId] = useState("");
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const allowed = ["administrator", "investigator"].includes(actor);
  const registry = useQuery({
    queryKey: ["recordings"],
    enabled: allowed,
    queryFn: async () =>
      unwrap(await client.GET("/v1/recordings")).data as RecordData[],
  });
  const runs = useQuery({
    queryKey: ["recorded-runs"],
    enabled: allowed,
    queryFn: async () =>
      unwrap(await client.GET("/v1/recorded/runs")).data as RecordData[],
  });
  const status = useQuery({
    queryKey: ["recorded-status", runId],
    enabled: allowed && !!runId,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/recorded/runs/{run_id}", {
          params: { path: { run_id: runId } },
        }),
      ).data as RecordData,
  });
  const passages = useQuery({
    queryKey: ["recorded-passages", runId],
    enabled: allowed && !!runId,
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/recorded/runs/{run_id}/passages", {
          params: { path: { run_id: runId } },
        }),
      ).data as RecordData[],
  });
  const passage = passages.data?.find((p) => p.id === selected);
  async function process(replay = false) {
    setBusy(true);
    setError("");
    try {
      const response = replay
        ? await client.POST("/v1/recorded/runs/{run_id}/replay", {
            params: { path: { run_id: runId }, header: key() },
          })
        : await client.POST("/v1/recorded/runs", {
            body: {
              recording_id: "delhi_anpr",
              duration_seconds: 60,
              line_y: 300,
              roi_top: 45,
              replay_anchor: "2026-01-01T00:00:00Z",
            },
            params: { header: key() },
          });
      const data = unwrap(response).data as RecordData;
      setRunId(data.run_id);
      setSelected("");
      await qc.invalidateQueries();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  if (!allowed)
    return (
      <p role="alert">
        Permission denied. Investigator or administrator authorization is
        required for recorded footage.
      </p>
    );
  return (
    <section>
      <p className="synthetic">Recorded footage — real model inference</p>
      <p>
        REAL_C1 · One uncalibrated camera · Clip-relative time · Recognition
        accuracy unmeasured
      </p>
      <State query={registry} />
      {registry.data?.map((r) => (
        <p key={r.id}>
          {r.title} · {r.duration_seconds} seconds · {r.width} × {r.height} ·{" "}
          {r.fps} FPS
        </p>
      ))}
      {registry.data?.length === 0 && <p>No registered recordings.</p>}
      <button
        disabled={busy || actor !== "administrator" || !registry.data?.length}
        onClick={() => process()}
      >
        Process first 60 seconds
      </button>
      <label>
        Recorded run
        <select
          aria-label="Recorded run"
          value={runId}
          onChange={(e) => {
            setRunId(e.target.value);
            setSelected("");
          }}
        >
          <option value="">Choose a recorded run</option>
          {runs.data?.map((r) => (
            <option key={r.run_id} value={r.run_id}>
              {r.recording_id} · {r.run_id.slice(0, 8)} · {r.state}
            </option>
          ))}
        </select>
      </label>
      <State query={runs} />
      {busy && <p role="status">Waiting for durable receipt…</p>}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!runId && (
        <p className="empty">
          Create or select a recorded run. The video is processed by the
          separate worker.
        </p>
      )}
      {runId && (
        <>
          <State query={status} />
          <State query={passages} />
        </>
      )}
      {status.data && (
        <>
          <h2>Processing: {status.data.state}</h2>
          {status.data.error && (
            <p role="alert" className="error">
              {status.data.error}
            </p>
          )}
          {status.data.missing_evidence > 0 && (
            <p role="alert" className="error">
              Missing evidence objects: {status.data.missing_evidence}
            </p>
          )}
          <progress
            max={status.data.config.duration_seconds}
            value={status.data.progress.relative_seconds || 0}
          />
          <p>
            {status.data.progress.frames_decoded} frames decoded ·{" "}
            {status.data.progress.frames_processed} frames processed · Attempt{" "}
            {status.data.attempts}
          </p>
          <p>
            {status.data.vehicle_passages} vehicle passages ·{" "}
            {status.data.outcomes.accepted} accepted ·{" "}
            {status.data.outcomes.review_required} review-required ·{" "}
            {status.data.outcomes.rejected} rejected ·{" "}
            {status.data.pending_outcomes} pending
          </p>
          <p>{status.data.count_rule}</p>
          <p className="meta">
            {status.data.config.anchor_meaning}:{" "}
            {status.data.config.replay_anchor}. The burned-in timestamp is not
            interpreted.
          </p>
          <button
            disabled={
              busy ||
              actor !== "administrator" ||
              !["completed", "failed"].includes(status.data.state)
            }
            onClick={() => process(true)}
          >
            Replay same run (duplicate check)
          </button>
          <Json
            value={status.data}
            label="Processing configuration, model hashes and durable status"
          />
          <h2>Passages and human review</h2>
          <p>
            Inspect original pixels before labeling. OCR output is not ground
            truth. Export the review CSV with the documented CLI.
          </p>
          {!passages.data?.length && (
            <p className="empty">
              No durable passages yet. A missing or unreadable plate does not
              suppress a crossing.
            </p>
          )}
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Clip seconds</th>
                  <th>Local track</th>
                  <th>Machine plate</th>
                  <th>Decision</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {passages.data?.map((p) => (
                  <tr key={p.id}>
                    <td>{p.relative_seconds.toFixed(2)}</td>
                    <td>{p.track_id}</td>
                    <td>
                      {p.observation?.plate || "Unreadable / unsupported"}
                    </td>
                    <td>{p.observation?.status || "pending"}</td>
                    <td>
                      <button onClick={() => setSelected(p.id)}>
                        Inspect passage
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {passage && (
        <article>
          <h2>Passage at {passage.relative_seconds.toFixed(2)} seconds</h2>
          <a
            target="_blank"
            href={`/v1/evidence/${passage.original_frame_evidence_id}`}
          >
            Open original crossing frame
          </a>
          <img
            className="recorded-frame"
            alt="Original recorded frame at vehicle crossing"
            src={`/v1/evidence/${passage.original_frame_evidence_id}`}
          />
          <p>
            Decision: {passage.observation?.status || "pending"} ·{" "}
            {passage.observation?.machine.reasons.join(", ")}
          </p>
          {!passage.inference?.samples?.length && (
            <p>No usable plate detection retained for this passage.</p>
          )}
          {passage.inference?.samples?.map((sample: RecordData) => (
            <section key={sample.pts} className="crop-review">
              <h3>
                Physical plate crop · {sample.relative_seconds.toFixed(2)}{" "}
                seconds
              </h3>
              <a
                target="_blank"
                href={`/v1/evidence/${sample.frame_evidence_id}`}
              >
                Open supporting original frame
              </a>
              <a
                target="_blank"
                href={`/v1/evidence/${sample.crop_evidence_id}`}
              >
                <img
                  className="plate-crop"
                  alt={`Physical plate crop at ${sample.relative_seconds} seconds`}
                  src={`/v1/evidence/${sample.crop_evidence_id}`}
                />
              </a>
              <p>
                Raw OCR: <code>{sample.ocr.text || "(empty)"}</code> · Score:{" "}
                {sample.ocr.confidence.toFixed(3)} (uncalibrated)
              </p>
              <Json
                value={sample}
                label="Raw model slots, character scores, preprocessing and original coordinates"
              />
            </section>
          ))}
          <Json
            value={passage.observation?.machine}
            label="Existing backend consensus and normalization contributions"
          />
        </article>
      )}
    </section>
  );
}
