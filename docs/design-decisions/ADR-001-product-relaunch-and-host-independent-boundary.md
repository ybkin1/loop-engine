# ADR-001: Relaunch Loop As A Host-Independent Engineering Delivery System

## Status

Accepted as the product-baseline decision for T-0037.

## Date

2026-07-22

## Context

The repository began with governance and process experiments. The product goal
is now explicit: build a real Loop engineering control and delivery system
that can operate independently or extend AI coding hosts such as Codex, Claude
Code, Zcode, and Qoder. The system must supply missing software-engineering
responsibilities, quality controls, evidence, and blocking behavior.

The product cannot depend on one host's UI or prompt behavior, and a host that
cannot intercept an operation must not be described as providing hard control.

## Decision

Treat `loop-engineering-lab` as the real product development project. Build the
product around three boundaries:

1. `Loop Core` contains host-independent contracts and domain rules.
2. `Loop Runtime` performs or mediates controlled execution and enforcement.
3. `Host Adapters` translate host-specific surfaces into Core contracts and
   declare `HARD`, `PARTIAL`, or `ADVISORY` enforcement.

Durable project documents and machine state are the cross-session source of
truth. `HANDOFF.md` is only a current-session recovery index.

## Alternatives Considered

### Governance-only project

Rejected. Rules and review records without a real product runtime do not solve
the user's problem.

### Codex-only extension

Rejected as the core boundary. Codex is the first useful host integration, but
host-specific assumptions would prevent independent operation and other
adapters.

### Prompt-only role system

Rejected. Prompts cannot reliably block writes, commands, stale evidence, or
stage transitions and cannot prove role competence.

### One monolithic Agent

Rejected. It concentrates authority and makes role independence, evidence
freshness, and veto behavior unverifiable.

## Consequences

- Product development can proceed on this repository without entering an
  external business project.
- The Core contracts must be designed before host integrations multiply.
- Runtime enforcement capabilities become a first-class product concern.
- Each host adapter must expose honest capability limits.
- Existing governance artifacts remain valuable historical input but are not
  treated as the finished product.
- More initial design and contract work is required, but future adapters share
  the same engineering model.
