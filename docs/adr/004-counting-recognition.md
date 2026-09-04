# ADR 004: Separate counting from plate recognition

Status: accepted for synthetic MVP.

## Context

An unreadable plate still belongs to an observed camera passage.

## Decision

Emit separate passage and OCR inputs. Count unique camera-local passage rows; coverage divides accepted observation passages by total passages.

## Consequences

OCR failure never erases traffic counts. These are camera passages, not proven unique physical vehicles. Source passage IDs must be reliable.
