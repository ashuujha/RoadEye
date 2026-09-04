# Model adapter contract

`packages/roadeye/contracts.py` defines FrameSource, PlateDetector, OCRRecognizer, VehiclePassageSource, ObservationInputSource and EvidenceStore protocols. Only synthetic event replay and local evidence storage are implemented. Detector/OCR protocols define a future seam, not installed models.

Future pipeline: FrameSource produces image bytes, UTC capture time and stable frame ID; detector returns bounded pixel boxes; tracking groups detections into a camera-local passage; OCR returns Candidate(text, confidence). An adapter then emits the existing separate passage record and complete OCR batch, with frame IDs deduplicated before consensus. Batches are immutable: corrections are explicit review revisions. Streaming passage finalization must be defined in the real adapter before integration.

Required metadata extension before enabling real modes: camera clock uncertainty, detector/tracker/OCR model IDs and immutable weight digests, runtime version, resize/letterbox/crop transforms, original frame dimensions, color order/normalization, inference device and latency, evidence digest/key, and source recorded_real/live_real. Document whether confidence is a raw model score or calibrated quantity. Supported plate formats need real jurisdiction-specific evaluation; never globally replace O/0 or fill missing characters.

Evaluation gates: authorized held-out data, full-plate exact-match and false-accept/reject breakdowns, per-condition results, independent passage-count validation, trajectory link precision/recall, travel-time error and hardware throughput. A score of .95 in a supplied candidate is not “95% accurate.” No training framework is included.
