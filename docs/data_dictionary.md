# Data dictionary

| Store | Ownership / meaning |
|---|---|
| zones, cameras, lanes, edges | Registered fictional six-camera network; one forward lane per camera. Distances are metres along directed road edges. Schematic x/y are fictional units. |
| datasets, runs | Manifest and immutable synthetic scope. Each run snapshots directed graph configuration. `clock` is historical event time; `version` advances on processed inputs/revisions. |
| input_events | Immutable canonical payload, event ID, scoped idempotency key/digest, actor and wall-clock receipt. |
| jobs | Transactional outbox: same primary key as input; pending/leased/done/poison, attempt counter, eligibility, lease token/deadline, error, process completion time. |
| vehicle_passages | One per run/camera/passage key; count source independent of OCR. FK to input, lane/camera and evidence. |
| ocr_readings | One per observation/frame; candidate contribution JSON retains raw strings, normalized alternatives and scores. Original duplicated readings remain in input payload. A separate candidate table is unnecessary for this bounded batch. |
| observations | Immutable machine result, capture/process time, policy and provenance. Plate/time/run index supports search. |
| observation_revisions | Append-only numbered review decisions, actor/reason, corrected plate/status. Latest revision overlays reads without changing machine output. |
| evidence_assets | Relative key, SHA-256, byte count, media type, run and provenance; bytes outside database. |
| trajectory_queries | Query parameters, immutable result JSON and run version. Old snapshots expose staleness after new data. |
| watchlists, watchlist_approvals | Scoped plate/reason/severity/half-open validity window; distinct creator/approver; draft/approved/revoked lifecycle and approval history. |
| alerts, alert_actions | Unique suppression key, evidence/observation references, status, details, classification, notes and actor. |
| camera_health | Last processed heartbeat per run/camera. Input history supplies window coverage intervals. |
| audit_records | Actor/action/target/run/correlation/time; database forbids updates/deletes. |
| local_sessions | SHA-256 of random session token, actor, wall-clock expiry; cookie contains raw token. |
| commands | Actor/operation/key uniqueness, canonical digest and response for retry-safe commands. |

Database timestamps use timezone-aware UTC instants. Capture is observed event time, receipt is durable API intake time, processing is worker completion time. UUIDs identify persisted records; fixture event UUIDs are deterministic. `source_mode=synthetic` and `inference_origin=mock_candidates` must never be interpreted as real model output.

Ratios: recognition coverage = accepted observation passages / observed passages, nullable at zero denominator; heartbeat coverage = union of 120-second heartbeat-validity intervals / requested window. Neither is a recognition-accuracy measurement or a full physical uptime guarantee.
