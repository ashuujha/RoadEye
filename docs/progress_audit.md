# RoadEye progress audit — SIH2026172

Audit date: **2026-09-05 UTC**. Starting commit: **ce064947798e407b79fe9d1dc6b49bb7114a5a12**. Delivered changes reviewed at **13759e8**, following review checkpoint **81e492f**, on `feat/recognition-audit-review`. The working tree was clean before this audit. No applicable AGENTS.md or attached handbook/build-guide file was found in the repository or its inspected ancestors. The user's supplied build specification, PRD, architecture, source, tests and primary technical sources are the available requirements/evidence. No statement about a missing handbook's delivered reference implementation is independently verified.

## Engineering judgement

**On track for an inspectable local engineering demonstration; not yet on track to claim validated Indian ANPR or a production city-wide system.** Durable input-to-console processing is real. The synthetic multi-camera slice works through the backend. The Delhi slice genuinely runs vehicle detection, local tracking, plate detection and crop OCR. Neither accepted plate correctness nor vehicle-count accuracy has a human-labelled denominator. A different dataset cannot repair that evidence gap.

Keep the modular monolith, PostgreSQL outbox and separate worker. Before a small-network beta, remove fixed camera/lane assumptions, define streaming tracklet finalization and clock uncertainty, validate Indian formats/OCR, calibrate connected cameras, and evaluate real links. Byte-based future adapter protocols and the working NumPy-based adapters are not yet a unified plugin interface. Production identity, retention/deletion, backup drills, capacity planning, multi-feed fairness, alert adjudication and operational monitoring remain substantial work. No overall percentage is assigned: requirement coverage is not effort remaining or probability of achieving 90%.

## Reproduced claims

Original run: `fe25474a-fa66-404d-9213-7013e3ca687f`. Recording and original machine outputs were preserved. Fresh PyAV metadata and a full decode-only count confirmed 1272×720, 25 FPS, 304.04 s, 7,601 frames, time base 1/12800 and start PTS 0. Frames beyond the first minute were counted without inference or visual inspection. Source digest and metadata are in the server registry and [recorded runbook](recorded_video_demo.md).

| Earlier claim | Fresh evidence and interpretation |
|---|---|
| 1,500 decoded; 300 processed | Re-decoding PTS in [0,60) reproduced 1,500 frames and the 300-frame schedule. New complete inference also processed 300. The terminating boundary frame is excluded. |
| 25 passages; 22 with plate detections | PostgreSQL passages and retained sample metadata reproduce these totals. They are predicted line crossings and retained plate proposals, not human truth. |
| 2 accepted, 6 review, 17 rejected | Reconstructed original consensus for all 25 from stored actual OCR: exact machine JSON equality. |
| Approximately 25 seconds CPU inference | Original persisted latest attempt is 24.661 s. Earlier saved reports show 25.064 s initial timing; that historical timing is a log claim, not newly timed. New v2 recovered attempt was 25.758 s; duplicate replay 25.272 s. No GPU or concurrent-feed benchmark. |
| 99 verified evidence objects | Fresh digest/size checks passed on every original object. |
| 39 crops match source pixels/time | All 39 original PNGs matched decoded pixels at stored PTS/boxes; OCR text, slots, character scores and preprocessing metadata also reproduced exactly. |
| Tests/recovery passed | Fresh complete `make validate` passed, plus a new real-model SIGKILL/recovery/replay acceptance. Historical hosted CI/Docker claims cannot be inferred from local checks. |
| Recognition accuracy | **Not yet measured**: CSV contains 25 rows, zero human transcriptions and all unreviewed. No real-run evaluation labels were manufactured by this audit. 2/25 = 8% acceptance coverage of predicted passages only. |

The versioned cadence fix produced a separate run `d7d83f8c-76ef-40fc-8c20-30c53f772ca9`: 25 passages, 22 with plate detections, **2 accepted / 8 review / 15 rejected**, zero pending, 51 completed jobs, 102 verified evidence objects, 42 exact crop/PTS and OCR reproductions. Two previously rejected passages now retain supported review candidates. Thresholds and models were unchanged. This is not evidence of increased accuracy.

## Requirement matrix

Status vocabulary: **Verified working** = executed for the stated scope/mode; **Implemented but unverified** = code exists without an executed gate; **Partially implemented** = only part of the stated requirement works; **Planned only** = design/contracts without a working path; **Blocked** = named prerequisite prevents the gate; **Not found** = no implementing code found. A synthetic pass does not make the corresponding real-world requirement verified.

Test abbreviations: U = `tests/unit`; P = `tests/integration/test_postgres.py`; RP = `test_recorded_postgres.py`; EP = `test_evaluation_postgres.py`; B = `tests/e2e/console.spec.ts`; RA = `scripts.recorded_acceptance.py`. P includes the twelve parametrized scenarios. Links below identify actual implementation, not merely API names.

| Requirement | Status | Code/document evidence | Test evidence | Validation mode | Remaining work | Acceptance gate |
|---|---|---|---|---|---|---|
| Register cameras, lanes, zones, directed network | Partially implemented | `models.py`, `services.seed`, API camera config; `Input` restricts C1–C6/REAL_C1 and L1 | P normal/scoped scenarios | synthetic; one recorded camera | Arbitrary enrolled networks/lanes and run membership; no invented real coordinates | Register and process an authorized new camera/lane without source edits |
| Recorded-video ingestion | Verified working | `recorded/service.py`, `processing.py`, VideoTask, fixed registry | RA actual 60 s receipt/crash/replay; RP provenance | recorded-real | Arbitrary start/end windows, long-job admission and reliable resume optimization | Current gate: first 60 s durably completes; full clip remains unexecuted |
| RTSP/live-feed ingestion | Planned only | `contracts.py` protocols, `config.py` rejects live mode | U provenance validation; no live decoder test | untested | Feed adapters, reconnect, clock sync, backpressure, finalization | Authorized continuous feeds with disconnect/recovery test |
| Vehicle detection and local tracking | Verified working | YOLO11 vehicle DFL decoding, IoU Tracker, downward crossing rule | U crossing/PTS; RA actual frame processing | recorded-real; algorithm fixtures synthetic | Occlusion/fragmentation, missed crossing and duplicate accuracy | Independent full-timeline crossing labels, precision/recall and duplicate rate |
| Plate detection and OCR pipeline | Verified working | Plate-specific detector; physical crop → RGB CCT recognizer | 39 original + 42 v2 source/crop/OCR reproductions; U RGB tensor contract | recorded-real | Accurate Indian and two-line recognition; detector precision/recall | Independent labels; errors stratified by visibility/size/layout |
| Indian >90% full-plate recognition | Partially implemented | Existing model pipeline; `plates.py` supports only AA00AA0000 shape | No labelled recognition benchmark | recorded-real inputs; accuracy untested | Representative authorized data, broader validated formats, suitable model and locked holdout | Predeclared numerator/denominator, >90% exact match under defined conditions plus false-accept/coverage reporting |
| Consensus, uncertainty and alternatives | Verified working | `plates.consensus`, immutable machine JSON | U boundaries/frame dedup; P disagreement; exact reproduction | synthetic and recorded-real | Calibrated decision policy, correlated-frame effects; single frame can currently be accepted | Human-labelled false accepts/rejects; thresholds fixed before holdout |
| Evidence integrity | Verified working | `evidence.py`, `save_image`, metadata/digests, safe keys, authorized retrieval | P missing/unsafe keys; RA pixels, PTS, 102 authorized objects; EP video Range | synthetic and recorded-real | Original frames are JPEG re-encodings; immutable MP4 is source truth; orphan cleanup/backup drill | Restore database + objects + source and rehash; adversarial access tests |
| Persistent storage and worker recovery | Verified working | PostgreSQL constraints/triggers, `jobs.py` leases/token fencing/retries/poison | P concurrent receipt/rollback/lease recovery; RA killed after 3 publications and recovered | synthetic and recorded-real | Production DB failure and recovery objectives; replay currently decodes from zero | No duplicate effects under crash; separately rehearse full DB/object disaster recovery |
| Cross-camera plate matching | Verified working | `trajectories.reconstruct`, `services.trajectory`, versioned snapshots | P normal/impossible/branch/collision; process E2E | **synthetic only** | Connected real sightings with timestamp/distance calibration | Real link precision/recall, false joins and ambiguous alternatives measured |
| Appearance-assisted cross-camera matching | Not found | No embeddings/re-ID/tracklet association implementation; new plan in `dataset_decision.md` | None | untested | Separate association contract and predicted tracklets | Video-predicted identities evaluated against withheld cross-camera GT |
| GIS chronology and inferred routes | Partially implemented | Chronological DAG, directed edge distances/windows, offline schematic; PostGIS installed | U directed paths/collision; P versioned queries; clean PostGIS function test | synthetic only | Surveyed geometry/GIS, direction calibration, clock uncertainty | Road-graph path validation on authorized network; sightings remain observed, paths inferred |
| Independent passage counts | Verified working | Passage inputs/table separate from OCR observations | U crossing without OCR; P unreadable case; RA rejected passages remain counted | synthetic and recorded-real | Human count accuracy; multi-lane aggregation generalization | Reconcile to independently counted unique crossings, including misses |
| Flow and OD patterns | Verified working | `analytics.py` query-derived adjacent flow and maximal unambiguous enrolled chains | P normal/ambiguous scenarios and B actual backend | **synthetic only** | Real trip/session validation; boundary/truncation bias | Labelled connected journeys, exclusions reported; not true origin/destination |
| Travel time, segment speed, congestion proxy | Verified working | Median/p90 and graph distance / elapsed; synthetic baseline ratio | P congestion/travel scenarios and B analytics | **synthetic only** | Calibrated real distance/baseline; actual congestion validation | Travel-time error and sample/coverage gates; never instantaneous speed or vehicles/km |
| Watchlists, alerts and operational review | Verified working | `services.py` matching/anomalies, API approvals/revisions/ack, unique suppression | P roles/validity/suppression/audit; process E2E | **synthetic only** for alert correctness | Recorded label-backed alert evaluation; production adjudication policy | Approved scoped entry, correct evidence-linked match, no duplicate alert; human false-alert review |
| Independent recognition review | Verified working | `evaluation_labels` append-only table; recorded review/timeline endpoints and React form | EP roles/revisions/idempotency; U denominators and correction leakage; B blank labels/decoded seek | recorded-real display; test labels only in isolated test runs | Human transcriptions, missed crossings, duplicate adjudication | Every prediction reviewed + whole timeline surveyed; unresolved cases block complete metrics |
| Authorization and audit | Verified working | `auth.py`, server sessions/roles, API investigator guards, immutable audit | P/RP/EP and B viewer denial | synthetic and recorded-real | Real individual identities, OIDC/MFA, deployment security | Production identity integration and access/security review; local role chooser is demo-only |
| Duplicate and late-event handling | Verified working | Unique receipt keys, run-version changes, immutable historical query output | P concurrency/late/review; RA stable IDs under replay | duplicate: both; late: synthetic | Real streamed late batches/clock changes | Late real input updates correct event windows without rewriting raw evidence |
| Docker stack | Blocked | `compose.yaml`, Dockerfiles; recorded mounts/dependencies not provided | `docker compose version`: executable absent | untested | Execute synthetic container stack; explicitly design recorded-volume/dependency extension | Clean Compose migration, API/worker/web/evidence health on pinned container versions |
| GitHub CI | Implemented but unverified | `.github/workflows/ci.yml`, minimal permissions, PostGIS service, no deploy | Corresponding native `make validate` passed; no hosted run | local tests synthetic/recorded-real; hosted untested | Execute on PG17/PostGIS3.5/Node22 CI matrix | Actual hosted successful run, not workflow existence |
| Multi-feed performance / city scale | Not found | Single local clip; run locks and bounded query scans; no capacity harness | One CPU clip ~25 s per 60 s at 5 FPS | untested for multiple feeds | Load/admission/fairness, long-video memory, realistic queries and failure load | Declared feed count/resolution/hardware, p95 lag, sustained throughput and recovery |
| Pilot/production operations | Planned only | `operations.md`, `SECURITY.md`, real-data/evaluation plans | No backup restore drill, OIDC, retention exercise or field pilot | untested | Source rights, privacy, retention, backup, monitoring, operational ownership | Approved small-network pilot, restore drill and operational acceptance before expansion |

The supplied guide's architecture is a proposal. Delivered implementation is the smaller modular monolith above. Existing wording that presented PRD acceptance as exclusively synthetic has been updated to distinguish the later recorded extension. No detector/OCR training, real multi-camera identity, live-feed support or measured production scalability is inferred from working endpoint names.

## Commands and checks actually executed

From repository root, native PostgreSQL on port 55432; no competing worker during recovery/tests:

```bash
export ROADEYE_DATABASE_URL=postgresql+psycopg://roadeye@127.0.0.1:55432/roadeye
export ROADEYE_RECORDED_ENABLED=true
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.audit_recorded fe25474a-fa66-404d-9213-7013e3ca687f --output .runtime/audit/baseline-reproduced.json
.venv/bin/python -m scripts.recorded_acceptance --report .runtime/audit/v2-acceptance.json
.venv/bin/python -m scripts.audit_recorded d7d83f8c-76ef-40fc-8c20-30c53f772ca9 --output .runtime/audit/v2-reproduced.json
UV_CACHE_DIR=/tmp/roadeye-uv UV_PYTHON_INSTALL_DIR=/tmp/roadeye-python \
PLAYWRIGHT_BROWSERS_PATH=/tmp/roadeye-browsers \
ROADEYE_RECORDED_RUN=d7d83f8c-76ef-40fc-8c20-30c53f772ca9 make validate
```

Additional executed inspections: `git status`, `git log`, repository/ancestor AGENTS and handbook searches, `lscpu`, `nvidia-smi`, `docker compose version`, and `SELECT version(), postgis_lib_version()` (18.6 / 3.6.2). Source metadata/count was independently checked with:

```bash
.venv/bin/python - <<'PY'
import av
with av.open("data/recorded_real/delhi_anpr.mp4") as source:
    stream = source.streams.video[0]
    print(stream.width, stream.height, stream.average_rate,
          float(stream.duration * stream.time_base), stream.time_base, stream.start_time)
    print(sum(1 for _ in source.decode(stream)))
PY
```

Results: **48 Pytest tests (22 unit, 26 PostgreSQL), one Vitest test, four Chromium tests**, Ruff, formatting, mypy, TypeScript, production build and generated OpenAPI/client consistency passed. Separate-process synthetic E2E passed; fresh recovery run `4a90cec2-9da7-4c2f-ac5c-0c13fd4b0191`. Clean migration test created a new UTF8 database, applied all migrations through `20260907_labels`, and executed a real PostGIS distance query. Real-video acceptance took 88.986 s including intentional crash, lease expiry, recovered processing, replay and HTTP evidence checks. Local artifacts stay under ignored `.runtime/audit`; actual source/model data were not committed.

Resolved check failures: initial duplicate test-module names prevented collection; fixed names. A new fixture attempted to update immutable video config; corrected fixture insertion, preserving the production constraint. Sandbox localhost/DNS restrictions blocked initial database/Vitest checks; actual checks subsequently ran with authorized native access. One Starlette/AnyIO deprecation warning remains; Playwright reports the non-failing NO_COLOR/FORCE_COLOR warning.

Blocked/unexecuted: Docker binary absent (exit 127); `nvidia-smi` cannot communicate with driver; no hosted CI; no full-clip inference, RoundaboutHD download/evaluation, live feeds, independent human accuracy/count labels, representative benchmark, or fresh full PostgreSQL service restart/backup restore. The previous full database-restart report remains historical evidence, not a check rerun here. A successful process recovery check is not substituted for a database disaster-recovery drill.

## Final critical review

Checked runtime imports: evaluation labels are read by the review API, never inference. Metrics compare immutable machine output, so operational corrections cannot inflate accuracy (regression tested). Synthetic and recorded scopes remain isolated; real footage does not acquire invented routes or calibration. Ground-truth fixture directories are test-only result assertions. No threshold was reduced; no plate was supplied manually; no acceptance count was hard-coded. Source video and crop access are server-authorized, and real review labels remain empty. Outstanding bounded-demo assumptions—fixed camera IDs, one lane, IoU tracking, narrow plate grammar, JSON inspection payloads and replay-from-zero—are explicit, not production claims.
