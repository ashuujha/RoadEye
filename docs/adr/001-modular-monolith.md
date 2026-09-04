# ADR 001: Modular monolith

Status: accepted for synthetic MVP.

## Context

A team of 3–5 needs one coherent deployment and shared domain policy.

## Decision

FastAPI and a separate worker share packages/roadeye modules and one relational database. Keep domain algorithms independent from HTTP; use explicit contracts and SQLAlchemy transactions.

## Consequences

Avoids distributed consistency and service sprawl. services.py coordinates multiple domains; split modules as behavior grows, not into speculative microservices.
