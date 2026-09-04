# Synthetic provenance

Dataset version 1, schema version 1, seed identifier 172, fixed UTC times on 2026-01-15. Construction is deterministic and contains no random sampling. The fictional graph has six cameras, three zones, one C2 branch, and a C5 merge. Positions are schematic units, not real installations. Every edge is 1000 m with [30,600] second travel windows and a declared synthetic baseline of 60 seconds.

Identifiers such as ZZ01AA0001 and ZZ01BB0000 are invented fixtures, not assertions about registrations or owners. The supported shape is illustrative conventional AA00AA0000 only, not a complete jurisdictional registration validator. Fixtures are test inputs, not a training corpus.

`scenarios` contains inputs, `ground_truth` contains independently asserted counts for tests, and the database contains derived outputs. Application modules do not read ground truth; Docker excludes it from runtime images. `manifest.json` records hashes, versions, purposes, event range, seed and limitations. Runtime verifies selected scenario file hashes before replay. `scripts/build_fixtures.py` is a maintenance tool, never a result-generation path.

The one compact SVG says SYNTHETIC EVIDENCE. It illustrates a passage and does not encode a vehicle plate. The mock adapter supplies candidates separately and never reads image pixels to infer them. No footage or public data was downloaded.
