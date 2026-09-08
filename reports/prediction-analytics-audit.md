# Hours 43â€“47 audit â€” prediction-only aggregate analytics

## Scope

This checkpoint covers the aggregate analytics that can be computed from frozen
RoadEye runtime predictions without plate strings or evaluator mappings. Plate
search and plate/vehicle hybrid evidence remain blocked on the sealed human OCR
review and are not part of this implementation.

## Claim boundary

- **PASS â€” ground-truth isolation:** the analytics builder receives only the
  hash-verified runtime journeys, approximate camera positions, link count,
  scenario label, and prediction hash.
- **PASS â€” honest labels:** every analytics response is `UNVERIFIED`. Camera
  visit intensity is not traffic density; predicted first/last-camera counts are
  not verified OD flow; transition support and boundary gaps are not congestion
  or route travel time.
- **PASS â€” runtime integrity:** the existing six-file allowlist is unchanged and
  the service verifies all source hashes before constructing aggregates.
- **UNVERIFIED â€” operational accuracy:** the aggregate counts inherit identity
  association errors and do not measure city traffic.
- **UNVERIFIED â€” plate search/hybrid evidence:** no plate truth has been attached
  to a runtime identity, and no such route or interface has been added.

## Interface

`GET /api/analytics` returns summary counts, per-camera observed runtime visits,
predicted journey endpoint pairs, directed transition-support proxies, and
machine-readable claim boundaries. The test frontend renders the values and
scales its approximate camera circles by runtime visit count while preserving
the prediction-only disclosure.

## Measured S06 rehearsal

The real frozen S06 runtime passed hash verification and produced 666 predicted
global IDs, 123 multi-camera predicted IDs, 826 observed runtime visits, and 160
predicted transitions across all six cameras from 0.0 to 199.9 seconds. The
largest camera visit count was c043 with 193. The most frequent predicted OD
endpoint pair was c042 to c043 with 21 IDs, and the highest transition-support
proxy was c042 to c043 with 35 predicted links.

These are aggregate properties of the same unverified S06 prediction, not
accuracy or traffic measurements. The audit artifact contains no global vehicle
IDs or plate strings. The live local S06 server returned HTTP 200 from
`/api/analytics` with the same counts and both prohibited-data flags false. The
complete repository finished with 80 passing tests; Ruff, `pip check`, and
JavaScript syntax also passed.

A headless Edge rehearsal loaded the local-only frontend, analytics route,
50-row vehicle catalog, selected five-camera S06 journey, evidence crop, and
boxed source frame with HTTP 200 responses. Visual inspection confirmed the
aggregate cards, tables, scaled camera markers, UNVERIFIED status, and S06
no-ground-truth disclosure rendered together. The deterministic tracked aggregate
artifact is `reports/prediction-analytics-s06.json` with SHA-256
`00ec63cea0c384926c444b02bd6c7b3f6df942879c8d41844d1eb4ba096ceaf9`.
