import type { Journey, PlateSearchResult } from "./api.generated";

export interface EvidenceSelection {
  readonly globalId: string;
  readonly visitIndex: number;
  readonly sampleIndex: number;
  readonly cropSha256?: string;
}

export type EvidenceSelectionHandler = (selection: EvidenceSelection) => void;

export function plateEvidenceSelection(result: PlateSearchResult): EvidenceSelection {
  return {
    globalId: result.global_id,
    visitIndex: result.visit_index,
    sampleIndex: result.sample_index,
    cropSha256: result.crop_sha256,
  };
}

export function validEvidenceSelection(selection: EvidenceSelection): boolean {
  return selection.globalId.length > 0 &&
    Number.isInteger(selection.visitIndex) && selection.visitIndex >= 0 &&
    Number.isInteger(selection.sampleIndex) && selection.sampleIndex >= 0;
}

export function resolveEvidence(journey: Journey, selection: EvidenceSelection) {
  if (!validEvidenceSelection(selection)) throw new Error("Invalid evidence selection.");
  if (journey.global_id !== selection.globalId) throw new Error("Evidence journey ID does not match the selection.");
  const visit = journey.visits[selection.visitIndex];
  if (!visit) throw new Error("Selected evidence visit is unavailable.");
  const sample = visit.evidence_samples[selection.sampleIndex];
  if (!sample) throw new Error("Selected evidence sample is unavailable.");
  if (selection.cropSha256 !== undefined && sample.crop_sha256 !== selection.cropSha256) {
    throw new Error("Selected evidence crop SHA-256 does not match the indexed prediction.");
  }
  return { journey, visit, sample };
}
