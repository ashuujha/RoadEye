# Runtime plate search and hybrid-evidence audit, hours 43-47 closure

- Date: 2026-09-09
- Engineering integration: **PASS**
- Runtime prediction quality/usefulness: **UNVERIFIED**
- OCR target inherited by this feature: **FAIL** at 13.85% full-string accuracy
- Frozen Re-ID/association changes: none

## Built boundary

`scripts/build_runtime_plate_index.py` validates the frozen detector weight,
development-selected confidence threshold, OCR model, OCR preprocessing freeze,
and sealed result before runtime inference. It then blocks network calls, fixes
deterministic seeds, uses CPU only, and processes every stored evidence sample for
multi-camera journeys. It never opens the transcription CSV or CityFlow identity
ground truth.

For each evidence crop the builder chooses at most one plate box deterministically,
runs the frozen `color_upscale` recognition path, and indexes only normalized
strings of at least three characters. No-box, unusable-text, invalid-crop, and
failure counts remain explicit. OCR output never changes or reranks vehicle
association.

Each ignored runtime directory contains `plate-runtime-manifest.json` and
`plate-index.json`. Tracked config pins both hashes. Startup fails closed unless
the manifest and index resolve to the current scenario, journey hash, entry
payload/count, evidence keys/crop hashes, and false ground-truth/association flags.

## Measured runtime output

| Measure | Frozen S02 default | S06 unverified demo |
|---|---:|---:|
| Multi-camera evidence crops | 216 | 849 |
| Detector boxes | 7 | 19 |
| OCR attempts | 7 | 18 |
| Searchable predictions | 1 | 2 |
| No plate box | 209 | 831 |
| Empty/short OCR | 6 | 16 |
| Invalid/unreadable crops | 0 | 0 |
| Processing failures | 0 | 0 |
| Batch wall time | 34.11 s | 763.80 s |
| Detector mean per evidence | 145.71 ms | 889.40 ms |
| OCR mean / p95 per attempt | 196.98 / 427.99 ms | 370.01 / 760.92 ms |
| Combined mean / p95 per evidence | 152.10 / 145.71 ms | 897.24 / 889.40 ms |

Ultralytics reports one shared per-result detector timing for each batch, which is
why detector p50/p95/max are identical within a run. Batch wall time is retained
as the end-to-end observation. These are local observations, not performance
benchmarks.

The S02 manifest/index hashes are
`40e515996ae551357a7f6cef36ba249332df3d10c244f4b27049aef4a0681ff5` /
`f08b19b2b390c99f2fac83a1b699415b0f1795626364806536a632ee57154be9`.
The S06 hashes are
`ef4c02ce0da1a982a1f6879b1eeb2fa3b23b99a63027ca0d5a7fb849cc71ef4a` /
`949e14bc45e122060c4f90ec1435f38dc4d2b679eec5edf6055da1b3a2a1a5d5`.

## API/frontend behavior

- `/api/plate-search/status` reports `READY` but retains status `UNVERIFIED`,
  uncalibrated-score wording, and the no-ground-truth claim notice.
- Exact, prefix, and contains searches return only current evidence-linked rows.
- Selecting a result opens its exact RoadEye ID, visit index, and sample index.
  The journey response and evidence panel show the predicted plate alongside the
  original crop and appearance evidence.
- No owner, person, address, watchlist, evaluator identity, benchmark string, or
  ownership inference is accepted or returned.

## Outcome

- **PASS:** offline build, provenance, source/evidence joins, enabled search,
  exact evidence handoff, deterministic query ranking, and no association change.
- **FAIL:** the inherited 90% recognition target.
- **UNVERIFIED:** all three CityFlow strings, their correctness, plate-query
  precision/recall, operational usefulness, and any end-to-end ANPR claim.
- **Measured limitation:** only 3/1,065 runtime crops produced searchable strings.
  Plate search is therefore a sparse inspection feature, not reliable retrieval.
