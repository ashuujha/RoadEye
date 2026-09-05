import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { client, key, unwrap } from "./api";
import { Json, State } from "./components";
import type { components } from "./api.generated";
type R = Record<string, any>;

export function BoxFrame({
  evidence,
  boxes,
  label,
}: {
  evidence: string;
  boxes: { box: number[]; label: string; color: string }[];
  label: string;
}) {
  return (
    <figure>
      <svg
        viewBox="0 0 1272 720"
        className="recorded-frame"
        role="img"
        aria-label={label}
      >
        <image href={`/v1/evidence/${evidence}`} width="1272" height="720" />
        {boxes.map((item, i) => (
          <g key={i}>
            <rect
              x={item.box[0]}
              y={item.box[1]}
              width={item.box[2] - item.box[0]}
              height={item.box[3] - item.box[1]}
              fill="none"
              stroke={item.color}
              strokeWidth="3"
            />
            <text
              x={item.box[0]}
              y={Math.max(40, item.box[1] - 6)}
              fill={item.color}
              stroke="white"
              strokeWidth=".3"
              fontSize="22"
            >
              {item.label}
            </text>
          </g>
        ))}
      </svg>
      <figcaption>
        {label} · overlays are detector proposals, not human labels
      </figcaption>
    </figure>
  );
}

export function RecordedReview({
  runId,
  config,
  passage,
}: {
  runId: string;
  config: R;
  passage?: R;
}) {
  const qc = useQueryClient();
  const player = useRef<HTMLVideoElement>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [form, setForm] = useState({
    reviewer_name: "",
    notes: "",
    transcription: "",
    readability: "not_assessed",
    plate_detection: "uncertain",
    passage_assessment: "uncertain",
  });
  const [marker, setMarker] = useState("");
  useEffect(() => {
    setForm((f) => ({
      ...f,
      notes: "",
      transcription: "",
      readability: "not_assessed",
      plate_detection: "uncertain",
      passage_assessment: "uncertain",
    }));
    setMarker("");
  }, [passage?.id]);
  const [complete, setComplete] = useState(false);
  const evaluation = useQuery({
    queryKey: ["evaluation", runId],
    queryFn: async () =>
      unwrap(
        await client.GET("/v1/recorded/runs/{run_id}/evaluation", {
          params: { path: { run_id: runId } },
        }),
      ).data as R,
  });
  async function save(
    kind: "passage" | "missed_vehicle" | "timeline_coverage",
  ) {
    setBusy(true);
    setMessage("");
    try {
      const body = {
        ...form,
        kind,
        passage_id: kind === "passage" ? passage?.id : null,
        target_id:
          kind === "missed_vehicle" ? marker || crypto.randomUUID() : null,
        relative_seconds:
          kind === "timeline_coverage" ? config.start_seconds || 0 : seconds,
        end_seconds:
          kind === "timeline_coverage" ? config.duration_seconds : null,
        transcription:
          form.readability === "readable" ? form.transcription : null,
        confirmed_complete: kind === "timeline_coverage" && complete,
      } as components["schemas"]["LabelRequest"];
      unwrap(
        await client.POST("/v1/recorded/runs/{run_id}/evaluation", {
          params: { path: { run_id: runId }, header: key() },
          body,
        }),
      );
      await qc.invalidateQueries({ queryKey: ["evaluation", runId] });
      setMessage("Independent human label saved. Machine output unchanged.");
      setForm((f) => ({
        ...f,
        transcription: "",
        notes: "",
        readability: "not_assessed",
        plate_detection: "uncertain",
        passage_assessment: "uncertain",
      }));
      setComplete(false);
      setMarker("");
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(false);
    }
  }
  const field = (name: keyof typeof form, value: string) =>
    setForm((f) => ({ ...f, [name]: value }));
  return (
    <section aria-label="Independent evaluation">
      <h2>Independent human review</h2>
      <p>
        Labels start blank. Do not copy OCR into ground truth. Review all source
        traffic, including vehicles never reported by the tracker. Local account
        is audited; reviewer name is self-reported.
      </p>
      <video
        ref={player}
        controls
        preload="metadata"
        className="recorded-frame"
        src={`/v1/recordings/${config.recording_id}/video`}
        onTimeUpdate={() => setSeconds(player.current?.currentTime || 0)}
        onError={() =>
          setMessage(
            "Source video unavailable or permission denied. Check the authenticated recording endpoint.",
          )
        }
      />
      <p>
        Source timeline: {seconds.toFixed(2)} clip seconds. Review interval [
        {config.start_seconds || 0}, {config.duration_seconds}) seconds.
        Burned-in time remains uninterpreted.
      </p>
      <label>
        Seek clip seconds
        <input
          type="number"
          min="0"
          max={config.manifest.duration_seconds}
          step="0.04"
          value={seconds}
          onChange={(e) => {
            const t = Number(e.target.value);
            setSeconds(t);
            if (player.current) player.current.currentTime = t;
          }}
        />
      </label>
      {passage && (
        <button
          onClick={() => {
            if (player.current)
              player.current.currentTime = Math.max(
                0,
                passage.relative_seconds - 1,
              );
          }}
        >
          View selected passage in source
        </button>
      )}
      <div className="scope">
        <label>
          Reviewer name
          <input
            value={form.reviewer_name}
            onChange={(e) => field("reviewer_name", e.target.value)}
          />
        </label>
        <label>
          Vehicle assessment
          <select
            value={form.passage_assessment}
            onChange={(e) => field("passage_assessment", e.target.value)}
          >
            <option value="uncertain">Not decided</option>
            <option value="valid">Valid unique vehicle crossing</option>
            <option value="duplicate">Duplicate predicted passage</option>
            <option value="incorrect">
              Incorrect passage / withdraw missed marker
            </option>
          </select>
        </label>
        <label>
          Plate detection assessment
          <select
            value={form.plate_detection}
            onChange={(e) => field("plate_detection", e.target.value)}
          >
            <option value="uncertain">Not decided</option>
            <option value="correct">Correct plate detected</option>
            <option value="incorrect">Incorrect plate detection</option>
            <option value="missing">Plate detection missing</option>
          </select>
        </label>
        <label>
          Human readability
          <select
            value={form.readability}
            onChange={(e) => {
              field("readability", e.target.value);
              field("transcription", "");
            }}
          >
            <option value="not_assessed">Not assessed</option>
            <option value="readable">Fully readable</option>
            <option value="partial">Partially readable</option>
            <option value="unreadable">Unreadable</option>
          </select>
        </label>
        <label>
          Independent full transcription
          <input
            autoComplete="off"
            disabled={form.readability !== "readable"}
            value={form.transcription}
            onChange={(e) => field("transcription", e.target.value)}
          />
        </label>
      </div>
      <label>
        Human review notes
        <textarea
          value={form.notes}
          onChange={(e) => field("notes", e.target.value)}
        />
      </label>
      <p>
        {passage
          ? `Selected predicted passage: ${passage.id} at ${passage.relative_seconds}s`
          : "Select a predicted passage below to label it, or mark a missed vehicle on the timeline."}
      </p>
      <button disabled={busy || !passage} onClick={() => save("passage")}>
        Save passage evaluation
      </button>
      <button
        disabled={
          busy || !["valid", "incorrect"].includes(form.passage_assessment)
        }
        onClick={() => save("missed_vehicle")}
      >
        {marker
          ? "Revise selected missed marker"
          : "Add missed vehicle at current time"}
      </button>
      <label>
        Missed marker to revise
        <select
          value={marker}
          onChange={(e) => {
            setMarker(e.target.value);
            const prior = evaluation.data?.labels?.find(
              (r: R) => r.label.target_id === e.target.value,
            );
            if (prior) {
              setSeconds(prior.label.relative_seconds);
              if (player.current)
                player.current.currentTime = prior.label.relative_seconds;
            }
          }}
        >
          <option value="">New marker</option>
          {evaluation.data?.labels
            ?.filter((r: R) => r.label.kind === "missed_vehicle")
            .map((r: R) => (
              <option key={r.target} value={r.label.target_id}>
                {r.label.relative_seconds}s · revision {r.revision} ·{" "}
                {r.label.passage_assessment}
              </option>
            ))}
        </select>
      </label>
      <label>
        <input
          type="checkbox"
          checked={complete}
          onChange={(e) => setComplete(e.target.checked)}
        />
        I reviewed the entire run interval and marked all missed crossings;
        unresolved cases must remain uncertain.
      </label>
      <button
        disabled={busy || !complete}
        onClick={() => save("timeline_coverage")}
      >
        Record timeline coverage
      </button>
      {message && <p role="status">{message}</p>}
      <State query={evaluation} />
      <p>
        Evaluation is not measured until labels and timeline coverage are
        complete. Acceptance coverage is not recognition accuracy.
      </p>
      <Json
        value={evaluation.data?.metrics}
        label="Review coverage and explicitly defined metrics"
      />
      <Json
        value={evaluation.data?.labels}
        label="Independent labels and revision identities"
      />
    </section>
  );
}
