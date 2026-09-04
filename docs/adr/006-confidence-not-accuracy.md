# ADR 006: Model-confidence inputs do not establish accuracy

Status: accepted for synthetic MVP.

## Context

Supplied mock scores and passing tests have no empirical relationship to held-out recognition accuracy.

## Decision

Label consensus score as heuristic. Store thresholds and candidate contributions; use provisional acceptance .8 and margin .2. Never convert .95 into a claimed 95% recognition result.

## Consequences

Actual accuracy requires authorized annotated held-out footage, full-plate exact-match, false-accept/rejection measurements and condition-specific analysis.
