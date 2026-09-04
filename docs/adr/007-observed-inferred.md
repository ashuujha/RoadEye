# ADR 007: Observed sightings versus inferred routes

Status: accepted for synthetic MVP.

## Context

Camera evidence does not observe every road between cameras or prove physical identity from text.

## Decision

Return observed nodes separately from inferred links, hard rejections, review candidates and multiple plausible branches/paths. Use directed road-graph distances and travel windows before soft quality scoring.

## Consequences

Do not report a unique route when alternatives remain. Flow/OD omit ambiguous links; enrolled-camera endpoints are not true trip origins/destinations.
