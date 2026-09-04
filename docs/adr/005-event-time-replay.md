# ADR 005: Event-time handling and replay

Status: accepted for synthetic MVP.

## Context

Late arrival and replay must not rewrite history or turn old events into live traffic.

## Decision

Use capture-time half-open windows, separate receipt/process wall time, fixed historical run clock and manifest order. Increment run version on new effects/reviews; retain immutable query snapshots.

## Consequences

SQL-derived metrics recompute on request. Runs cap 500 inputs; this favors correctness and inspectability over city-scale materializations. Duplicate replay does not advance versions.
