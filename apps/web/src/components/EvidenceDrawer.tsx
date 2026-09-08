import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { resolveEvidence, validEvidenceSelection, type EvidenceSelection } from "../evidence";
import { IconClose, IconExternalLink } from "./Icons";
import { StatusBadge } from "./StatusBadge";

interface EvidenceDrawerProps {
  readonly selection: EvidenceSelection | null;
  readonly onClose: () => void;
}

function EvidenceImage({ url, label }: { url: string; label: string }) {
  const [failed, setFailed] = useState(false);
  return (
    <figure className="drawer-evidence-image">
      {failed ? <p className="status-banner banner-danger" role="alert">{label} could not be loaded.</p> : (
        <img src={url} alt={label} onError={() => setFailed(true)} />
      )}
      <figcaption>
        <a href={url} target="_blank" rel="noreferrer"><IconExternalLink size={14} /> {label}</a>
      </figcaption>
    </figure>
  );
}

export function EvidenceDrawer({ selection, onClose }: EvidenceDrawerProps) {
  const panel = useRef<HTMLDivElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const isOpen = selection !== null;
  const valid = selection !== null && validEvidenceSelection(selection);
  const detail = useQuery({
    queryKey: ["drawer-evidence", selection?.globalId, selection?.visitIndex, selection?.sampleIndex, selection?.cropSha256],
    enabled: valid,
    queryFn: async ({ signal }) => {
      if (!selection) throw new Error("No evidence selected.");
      const journey = await api.journey(selection.globalId, { signal });
      return resolveEvidence(journey, selection);
    },
    staleTime: 60_000,
    retry: false,
  });

  useEffect(() => {
    if (!isOpen) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();

    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
      if (event.key === "Tab") {
        const controls = panel.current?.querySelectorAll<HTMLElement>("button:not([disabled]), a[href], summary, [tabindex='0']");
        if (!controls?.length) return;
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault(); first.focus();
        }
      }
    }
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [isOpen, onClose]);

  if (!selection) return null;
  const data = valid ? detail.data : undefined;
  const cropUrl = valid ? api.evidenceCropUrl(selection.globalId, selection.visitIndex, selection.sampleIndex) : "";
  const frameUrl = valid ? api.evidenceFrameUrl(selection.globalId, selection.visitIndex, selection.sampleIndex) : "";
  const incoming = data?.visit.incoming_link;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel" ref={panel} onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        <div className="drawer-header">
          <div>
            <div className="drawer-kicker">READ-ONLY PREDICTION EVIDENCE</div>
            <h2 id="drawer-title" className="drawer-title">{data ? data.visit.camera + " / frame " + data.sample.frame : "Prediction evidence"}</h2>
          </div>
          <button type="button" ref={closeButton} className="btn-icon" onClick={onClose} aria-label="Close evidence drawer"><IconClose size={20} /></button>
        </div>
        <div className="drawer-body">
          <StatusBadge status="uncertain" label="UNVERIFIED / NOT GROUND TRUTH" />
          {!valid && <p className="status-banner banner-danger" role="alert">Invalid evidence selection.</p>}
          {valid && detail.isPending && <p role="status">Loading the selected journey sample...</p>}
          {valid && detail.isError && (
            <div className="status-banner banner-danger" role="alert">
              <p>{detail.error.message}</p>
              <button type="button" className="btn btn-secondary" onClick={() => void detail.refetch()}>Retry evidence</button>
            </div>
          )}
          {data && (
            <>
              <p>{data.journey.disclosure ?? "Runtime identity predictions are not ground truth."}</p>
              <section className="drawer-section">
                <h3 className="section-title">Selected evidence sample {selection.sampleIndex + 1}</h3>
                <EvidenceImage key={cropUrl} url={cropUrl} label="Hash-bound vehicle crop" />
                <EvidenceImage key={frameUrl} url={frameUrl} label="Exact source frame with predicted box" />
                <dl className="drawer-evidence-metadata">
                  <dt>RoadEye predicted ID</dt><dd className="mono">{data.journey.global_id}</dd>
                  <dt>Tracklet / visit</dt><dd className="mono">{data.visit.tracklet_key} / {data.visit.sequence}</dd>
                  <dt>Observed sample time</dt><dd>{data.sample.time_s.toFixed(2)} s (scenario-relative)</dd>
                  <dt>Observed visit window</dt><dd>{data.visit.first_observed_s.toFixed(2)} to {data.visit.last_observed_s.toFixed(2)} s</dd>
                  <dt>Identity available at</dt><dd>{data.visit.identified_at_s.toFixed(2)} s</dd>
                  <dt>Bounding box (x, y, w, h)</dt><dd className="mono">{data.sample.bbox_xywh.join(", ")}</dd>
                  <dt>Crop SHA-256</dt><dd className="mono evidence-hash">{data.sample.crop_sha256}</dd>
                  <dt>Approximate camera position</dt><dd>{data.visit.position.latitude.toFixed(5)}, {data.visit.position.longitude.toFixed(5)} / {data.visit.position.kind}</dd>
                  <dt>Baseline appearance score</dt><dd>{data.sample.baseline_score.value.toFixed(3)} / {data.sample.baseline_score.kind}</dd>
                </dl>
                <p className="text-xs text-muted">Appearance scores are uncalibrated and are not probabilities.</p>
              </section>
              <section className="drawer-section">
                <h3 className="section-title">OCR prediction / UNVERIFIED</h3>
                {data.sample.plate_prediction ? (
                  <>
                    <strong className="mono evidence-plate">{data.sample.plate_prediction.predicted_plate_text}</strong>
                    <p>Normalized prediction: <span className="mono">{data.sample.plate_prediction.normalized_plate_text}</span></p>
                    <p>OCR model score: {data.sample.plate_prediction.ocr_score.toFixed(3)}. Uncalibrated, not a probability.</p>
                    <p>Predicted plate text is not ground truth. OCR does not change the vehicle association.</p>
                  </>
                ) : <p>No usable plate prediction is linked to this exact sample.</p>}
              </section>
              <section className="drawer-section">
                <h3 className="section-title">Incoming association evidence</h3>
                {incoming ? (
                  <>
                    <StatusBadge status="uncertain" label="Not scored in runtime" size="sm" />
                    <dl className="drawer-evidence-metadata">
                      <dt>From tracklet</dt><dd className="mono">{incoming.from_tracklet}</dd>
                      <dt>To tracklet</dt><dd className="mono">{incoming.to_tracklet}</dd>
                      <dt>Appearance similarity</dt><dd>{incoming.appearance_similarity.toFixed(3)}</dd>
                      <dt>Second best / ambiguity margin</dt><dd>{incoming.second_best_similarity?.toFixed(3) ?? "Unavailable"} / {incoming.ambiguity_margin?.toFixed(3) ?? "Unavailable"}</dd>
                      <dt>Boundary gap / approximate distance</dt><dd>{incoming.temporal_gap_s.toFixed(2)} s / {incoming.distance_m.toFixed(1)} m</dd>
                      <dt>Temporal / topology reason</dt><dd>{incoming.temporal_topology_reason}</dd>
                    </dl>
                    <p className="text-xs text-muted">Association scores are not probabilities. Boundary gaps are not route travel times.</p>
                  </>
                ) : <p>No incoming association is recorded for this visit.</p>}
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
