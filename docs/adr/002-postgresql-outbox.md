# ADR 002: PostgreSQL outbox instead of Kafka

Status: accepted for synthetic MVP.

## Context

Input acceptance must survive process failure without requiring a separate broker.

## Decision

Insert immutable input and unique job in one transaction. Lease with SKIP LOCKED, retry with backoff, poison failures and fence handlers with tokens. Commit effects and completion together.

## Consequences

At-least-once delivery with idempotent effects. Per-run serialization simplifies versioning at demo scale; throughput needs measurement before expansion.
