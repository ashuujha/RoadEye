# Sealed OCR test audit, hours 33-43 closure

- Date: 2026-09-09
- Readiness result: **PASS**
- Frozen OCR target result: **FAIL**
- Scope: one independent full-string score on supplied plate crops

## Readiness reported before scoring

The ignored replacement `data/anpr/transcriptions.csv` passed the dedicated
readiness command before truth was loaded for scoring:

| Status | Count |
|---|---:|
| Reviewed | 31 |
| Corrected | 164 |
| Unreadable | 5 |
| Missing | 0 |
| Unrecognized | 0 |
| Readable | 195/200 |
| Required readable minimum | 150 |

Every one of the 200 frozen test rows had exactly one terminal state. Readable
coverage exceeded the minimum by 45 rows. The readiness artifact SHA-256 is
`683559f061495a53d5b728d8be6bb72bc5ea8a6d69db71f43895b320dfb4550e`.

## One-time sealed result

After readiness passed, `scripts/run_anpr.py evaluate-ocr-test` was executed
exactly once. It measured the already-frozen `color_upscale` recognizer:

| Metric | Result |
|---|---:|
| Exact full strings | 27/195 |
| Full-string accuracy | 0.1384615 (13.85%) |
| Wilson 95% interval | 0.0969346-0.1939577 (9.69-19.40%) |
| Character edits / truth characters | 489/1,865 |
| Character error rate | 0.2621984 (26.22%) |
| Nonempty predictions / readable rows | 195/195 |
| Coverage | 1.0000 |
| CPU mean latency | 67.81 ms per readable crop |
| CPU p95 latency | 124.89 ms per readable crop |
| Frozen 90% target | **FAIL** |

The result artifact SHA-256 is
`ad2f709eb2540b95fded3bd0c0212fa732c32159f8cf74d11d1bfc40e7a9b23f`.
Its prediction-file hash is
`cdaa88c66879b431215f281e6c51be2172581bc78abda54f699ae14277b570b6`;
its ignored transcription-file hash is
`c45250f308ba9bb6ce1caec311adeaf57274df5a2098e2422fcc158034950e86`.

## Claim boundary

- **PASS:** terminal-state, family/image-hash, split, and frozen-source gates
  controlled entry to scoring.
- **FAIL:** the 90% full-string target was not achieved.
- **UNVERIFIED:** end-to-end full-scene plate detection plus OCR, city-wide
  accuracy, and CityFlow plate accuracy were not measured by this crop test.
- Benchmark transcriptions remain ignored evaluation truth. They are not copied
  into runtime artifacts, the API, or the frontend.
