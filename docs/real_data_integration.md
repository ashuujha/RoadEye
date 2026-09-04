# Authorized real-data handoff

Real modes currently fail startup. This phase supplies mock candidates, not recognition accuracy. Next, collect authorized connected footage from a small network where the same vehicles actually pass multiple enrolled cameras. Document access, retention, permitted uses and evidence handling before capture.

1. Synchronize UTC clocks; record uncertainty, camera positions, road graph distances, lane direction and frame timestamps. Preserve capture time separately from upload/process time.
2. Annotate passages, visible full plate strings, unreadable/occluded conditions and known cross-camera journeys. Validate counting independently of OCR.
3. Keep adjacent frames and the same passage out of different train/test splits. Also separate physical journeys/cameras/time periods where appropriate to avoid identity and condition leakage.
4. Implement frame source → detector → within-camera tracker/passage source → OCR recognizer → existing versioned candidate batch contract. Preserve source mode, detector/OCR/tracker versions, preprocessing and hardware metadata. Never silently replace failed real inference with supplied mock candidates.
5. Evaluate held-out full-plate exact match, missed detections, incorrect accepted readings, rejection/review rates and condition-specific results. Confidence values require calibration; do not describe confidence or unit-test pass rates as accuracy.
6. Validate link precision/recall against annotated journeys, ambiguous/collision cases, missing coverage and travel-time estimation errors. Check traffic counts separately, including unreadable plates.
7. Benchmark the actual target hardware and feed count: ingestion throughput, end-to-end latency, frame loss, GPU/CPU/memory, disk growth, outbox backlog and recovery. Set capacity limits from measurement, not architecture diagrams.

Replace local role-selector authentication with externally managed identities and authorization, retention controls, encrypted transport, secrets management, storage quotas, monitoring and operational incident drills before real use. PostGIS geometry should be added only with verified coordinate reference systems and real spatial requirements. The current fictional graph is not georeferenced and does not validate road matching.
