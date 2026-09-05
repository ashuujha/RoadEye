# Dataset decision — SIH2026172

Audit **2026-09-05 UTC**; baseline **ce06494**, repository implementation **13759e8**. This is a bounded primary-source assessment and integration proposal. No dataset archive, footage, annotations or model weights were downloaded during this audit. Small repository scripts/configuration/license files and HTTP headers were read. Code/test execution evidence and other blockers are in [progress audit](progress_audit.md).

## Decision

**Keep the Delhi recording for Indian OCR investigation. Defer RoundaboutHD acquisition and implementation until the readiness gates below.** Plan the isolated experiment now; do not spend tomorrow's preparation on a new identity subsystem. The local review interface and independent source-timeline labels are more immediately useful than another unlabelled pipeline.

RoundaboutHD is relevant additional evidence for appearance-based multi-camera tracking. RoadEye currently has no appearance encoder, re-identification gallery, cross-camera tracklet association or corresponding evaluator. `trajectories.py` links stored plate evidence using chronology and directed road constraints. It cannot identify unreadable-plate vehicles unchanged. Run isolation, durable jobs, evidence, authorization and the console are reusable infrastructure, but the current `Input` camera IDs, lane validation, observation schema and recorded registry are deliberately narrow.

## What the primary sources establish

| Source | Verified findings / limits |
|---|---|
| [Bath record 1574](https://researchdata.bath.ac.uk/1574/) | Bath hosts a dataset recorded in Indiana, USA, with four synchronized cameras, vehicle tracking annotations and camera geometry. The archive is listed as approximately 8 GB. A fresh HEAD request returned HTTP 200, `Content-Length: 8075314494`, `Accept-Ranges: bytes`, MIME `application/zip`. Availability of the endpoint is verified; successful full download, extraction and archive contents are not. |
| [Original paper, §3](https://arxiv.org/html/2507.08729v2), [record](https://arxiv.org/abs/2507.08729) | Carmel, Indiana; four simultaneous ten-minute videos, 4K/15 FPS; 512 global vehicles, 310 seen by at least two cameras. Camera geometry is provided. Crucially, §3.1 says the camera angles avoid readable license plates and recognizable faces. This is not an ANPR transcription dataset. Paper statements were inspected, not independently re-counted from video. |
| [Author dataset repository](https://github.com/siri-rouser/RoundaboutHD) | README describes `images/c001`–`c004`, videos, detection label archives, single-camera tracks, `Multi_CAM_Ground_Truth.txt`, vehicle statistics, geometry JSON and a ReID subset. Cross-camera rows are described with camera/global-ID/frame and pixel box/world-coordinate fields; frames start at zero. Same global IDs are evaluation annotations, not OCR. Camera JSON and actual annotation files were not downloaded or validated. |
| [Author labelling/evaluation repository](https://github.com/siri-rouser/multi_camera_tracking_labelling_tool) | Small evaluator sources and LICENSE inspected at tree `8a8d416b65486a43a2d2641876f585095912f5ac`. `eval_det.py` takes prediction/GT directories; `eval_sct.py` takes prediction/GT track files and uses motmetrics. The dataset README swaps those two script names. `eval_label.py` reads ten named columns including `Ori`, whereas the dataset README describes nine; reconcile with actual data before use. No scorer was executed. |

Download request actually executed (headers only):

```bash
curl -fsSI --max-time 30 https://researchdata.bath.ac.uk/1574/1/RoundaboutHD.zip
```

Do not use byte-range availability as proof that a two-camera subset is separately downloadable. Ask for a small authorized subset or establish a bounded extraction method before acquisition. We did not fetch the ZIP central directory or infer which ZIP members can be independently retrieved.

### Rights are separate

The Bath archive entry is labelled **“Software: MIT License”** in its metadata. Preserve that attribution; verify whether the deposit's license covers all supplied footage/annotations and inspect any archive-specific notices before reuse or redistribution. The inspected RoundaboutHD repository root did not expose a separate LICENSE file. Its linked **labelling-tool code** has an MIT LICENSE (Yuqiang Lin, 2025); that alone does not license third-party video. The **paper** is under CC BY-NC-SA 4.0 according to its arXiv record, which is not the dataset's license. The provided Delhi clip's original source URL and reuse/redistribution permission remain unknown. No legal permission is inferred from public access, and no footage is committed or uploaded.

Evaluator readiness also requires a tiny independently calculated fixture: verify column count, xyxy versus xywh conversion, camera/frame offsets, identity namespaces and matching threshold semantics. The inspected SCT script passes `distth=0.0`; do not treat its output as a comparable published benchmark without checking that choice and documenting any change. Inspect train/query/gallery identity overlap and reserve evaluation identities instead of assuming the supplied ReID split is suitable for a new model.

## Bounded Indian alternatives search

The search targeted Indian multi-camera ANPR video, synchronized connected vehicle footage, timing/geometry, plate annotations and reuse terms. It examined author/institution sources; it did not scrape footage or solicit access. **No Indian resource meeting all those requirements was verified in this bounded search. That is not a claim that none exists.** The following three are partial-fit leads, not substitutes for connected roadside ANPR footage:

| Candidate and official source | Video / connected identity / metadata | Plates and annotations | Access / reuse | Decision |
|---|---|---|---|---|
| [Minus Zero Indian urban autonomous-driving release](https://huggingface.co/datasets/gagandeepreehal/minuszero-indian-autonomous-driving-dataset) | Search-indexed owner card describes multi-camera ego-vehicle MCAP/H.265 recordings with timing/pose; not a verified fixed roadside network | Card describes no annotations or authored splits; readable plates and connected cross-camera GT not verified | Indexed card reports ~3.197 TB and CC BY-NC 4.0 plus privacy restrictions. Direct raw README request returned **401**; current access/terms and package size not independently confirmed. No credentials/form supplied. | Possible authorized sensor-data research lead, **not ready for this demo**. Cannot assert available connected Indian ANPR. |
| [IIIT-H IDD family](https://insaan.iiit.ac.in/datasets/) | Multimodal lists front stereo at 15 FPS plus GPS/LIDAR/OBD; Temporal supplies nearby ±15 frames. This is ego-driving data, not established cross-roadside-camera journeys | Detection/scene labels; no verified plate transcriptions or globally identified connected-roadside vehicles | Official page lists 6.5 GB primary multimodal package and larger alternatives. Download portal exists; complete applicable reuse terms/access not verified during this audit | Useful driving/detection data; does not satisfy required ANPR journey evidence. |
| [Indian Commercial Truck License Plates](https://github.com/siddagra/Indian-Commercial-Truck-License-Plates-Dataset) | Author explicitly describes an **image** dataset for weighbridge use, not continuous connected video | Plate boxes/text annotation assets; completeness and splits require inspection | Author says form-based access and CC BY-NC-SA for work/assets; license version and actual image access not verified. No form submitted or data downloaded | Potential future plate detection/OCR evaluation after terms/split review, **not multi-camera tracking evidence**. |

Unrelated plate images can legitimately evaluate or train detector/OCR components with proper labels and held-out splits. They must never be assembled into an allegedly observed journey. An ego rig with several simultaneous viewpoints is also not automatically equivalent to vehicles moving between separated city cameras.

## Readiness gates before adding RoundaboutHD

1. Finish or explicitly bound the Delhi review so its failures/metrics are understood; preserve its run and the synthetic judge demonstration.
2. Confirm dataset/code rights and obtain an approved small subset with a size/duration budget. No automatic 8 GB download is authorized by this plan.
3. Define independent detection, local tracklet, cross-camera association and evaluation contracts. A tracklet contains dataset/run/camera ID, local track ID, original frame/PTS span, boxes, vehicle class/quality, model version and evidence. An association contains source/target tracklet IDs, candidate score components, temporal/geometry constraints, alternatives and policy version. **No invented plate field.**
4. Build a fixture-tested evaluator boundary using labels only after predictions are frozen. Pin code versions, metrics and matching thresholds. Resolve the upstream format/command discrepancies first.

## Smallest useful experiment once ready

Use **one shared 3–5 minute interval from two cameras**, chosen after metadata inspection confirms sufficient actual transitions. Aim for at least 20 labelled cross-camera transitions for an initial engineering experiment; if fewer exist, lengthen the common interval within an approved budget or state that the experiment is underpowered. Do not promise that an uninspected interval or camera pair contains transitions.

Preserve original camera IDs, synchronized starts/frame numbering/PTS, road connections and supplied geometry with its documented coordinate reference. Validate projection residuals before using geometry; never borrow Delhi coordinates or fabricate locations. Create an isolated `roundabouthd:<manifest-digest>` dataset/run namespace and immutable model/config manifest. Runtime reads only video and permitted calibration; GT identities remain outside the production inference path.

First produce **runtime-predicted vehicle detections and local tracklets**; then an explicitly separate appearance-plus-time/geometry association stage returning uncertain alternatives. Ground-truth global IDs evaluate the predictions; they are never assigned to runtime tracks to make association appear successful. Export predictions before joining to evaluation labels. No model training or association subsystem was implemented in this audit.

Report detection precision/recall under a fixed IoU rule, local track fragmentation/ID switches and IDF1, cross-camera association precision/recall with all misses and false joins, transition sample counts, temporal errors, processing time/hardware, and examples of rejected/ambiguous associations. Report per-camera and per-transition results. Split calibration/development and evaluation by vehicle identity and time, preventing adjacent frames/the same passage leaking across the boundary. Initially benchmark the two-camera interval, not a claimed city-wide capacity.

Keep three console modes unambiguous:

| Mode | What it demonstrates |
|---|---|
| Predicted tracking from actual video | Tests detector, tracker and association implementation against withheld labels |
| Supplied ground-truth trajectory visualization | Checks annotation import/geometry/display; **does not test our matching algorithm** |
| Synthetic scenario replay | Tests deterministic backend rules, durability and UI using invented events |

RoundaboutHD could validate local/multi-camera tracking and scoped flow/travel-time derivations on that US roundabout if geometry, predictions and metrics are correctly integrated. It cannot establish Indian OCR, plate-based identity, representative Indian road conditions, true trip origin/destination beyond enrolled cameras, live-feed behavior, city-wide scaling or a greater-than-90% ANPR claim. Delhi and RoundaboutHD vehicles must never be linked across datasets.
