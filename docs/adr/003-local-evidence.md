# ADR 003: Local evidence storage

Status: accepted for synthetic MVP.

## Context

The compact judge demonstration needs inspectable evidence without MinIO or paid services.

## Decision

Store bytes in a private local directory; persist digest/size/type/key/provenance, authorize API reads and verify integrity. Implement an EvidenceStore protocol.

## Consequences

Current adapter serves versioned read-only synthetic SVG. S3 migration preserves metadata and private authenticated delivery. Backups must include both database and objects.
