# Recorded-video vertical slice — SIH2026172

Implementation and measurement are in progress; measured results will replace this section after the actual PostgreSQL run completes.

## Scope and source

One provided third-party recording, `data/recorded_real/delhi_anpr.mp4`, represents **REAL_C1 only**. Original source URL and redistribution permission are currently unknown; the original file is excluded from Git and is never modified or uploaded. Registry SHA256: `bef435656f050df576aedd5ac694824b9425a40b33072ef1213e377910cf1f96`.

PyAV decoded metadata: 1272 × 720, 25 FPS, 7,601 frames, 304.04 seconds, time base 1/12800, start PTS 0. The initial half-open interval is [0,60) seconds. Positions use decoded presentation timestamps. The default UTC anchor is **assigned** 2026-01-01T00:00:00Z, configurable per run; it is not the actual recording time. The burned-in timestamp/date/timezone are not interpreted.

## Models and decisions

All three models run locally with ONNX Runtime CPUExecutionProvider and two intra-op threads. This machine's NVIDIA driver is unavailable. Models are checksum-pinned in `packages/roadeye/recorded/models.json`; download URLs, export versions and sizes are stored there and snapshotted into each recorded run.

- Vehicle detector: Ultralytics YOLO11n COCO, [Espressif ONNX export](https://github.com/espressif/esp-dl/tree/master/models/coco_detect), export version 8.3.96. AGPL-3.0 model metadata. Six raw output tensors require DFL distance decoding and sigmoid class scores, following [Ultralytics source](https://github.com/ultralytics/ultralytics/blob/v8.3.96/ultralytics/utils/tal.py). Only car/motorcycle/bus/truck classes are retained.
- Plate-specific detector: [MorseTech YOLO11 license plate nano](https://huggingface.co/morsetechlab/yolov11-license-plate-detection), immutable revision 251a30d7daedca065f56e04b0af04052c907c68f, export 8.3.123, AGPL-3.0. Its author warns that upstream dataset overlap inflates benchmark results. No benchmark accuracy claim is adopted here.
- OCR: [fast-plate-ocr CCT XS global v2](https://github.com/ankandrew/fast-plate-ocr), 3.34 MB ONNX release. Repository MIT license; model weights stay outside this repository. The release config accepts RGB uint8 crops resized bilinearly to 128 × 64, ten character slots, Latin letters/digits and padding. India is not among the explicit region-head classes; regional generalization is unvalidated. Region predictions are not used. These upstream licenses do not establish permission to redistribute the recording.

Physical plate boxes are detected inside vehicle crops. The top 45 pixels are excluded before detection, and all crop coordinates are mapped back to the original frame. OCR never receives full frames or supplied strings. Raw physical JPEG crops, original frames, OCR slots/strings/character scores, bounding boxes, preprocessing and model hashes remain inspectable. JPEG evidence is an unannotated re-encoding of decoded pixels; the original MP4 remains unchanged.

Provisional passage rule: at 5 sampled frames/second, deterministic IoU association (threshold 0.15, maximum one-second gap) counts a vehicle once when its bounding-box bottom centre crosses y=300 downward after at least two detections. IDs are camera/run-local. Vehicles first appearing below the line do not count. Occlusion, detector misses and fragmented tracks can affect counts; this is not measured counting accuracy. Expensive plate/OCR inference runs selectively on nearby vehicle crops at least 0.6 seconds apart. Up to three largest score-weighted physical crops per track enter the existing consensus policy. Unreadable vehicles still publish passage inputs and rejected OCR outcomes.

The existing conservative AA00AA0000 normalizer remains unchanged; other plate shapes can be rejected even when raw text looks readable. Model scores are uncalibrated. Recognition accuracy is **unmeasured**, pending independent human labels.

## Durability

A recording request commits a run, immutable configuration/model/source snapshot, input event and outbox job before returning HTTP 202. The separate worker renews its fenced lease as progress commits. A crash retries decoding from the beginning with stable run/track/event IDs. Published passage/OCR receipts use the existing ingestion transactions, jobs, constraints and consensus. Duplicate inputs return original receipts; they do not add passages, observations or alerts. Original evidence is content-addressed, written before metadata receipt, and authorized through the existing evidence endpoint. Files left by a rolled-back receipt are possible orphans and can be reconciled with evidence metadata; do not delete the entire evidence store.

Synthetic camera lists, scenarios and controls remain scoped to the fictional network. Recorded runs reject synthetic trajectory/analytics endpoints and have separate recorded counts/status. No geographical placement, routes, speed or congestion is inferred for REAL_C1.
