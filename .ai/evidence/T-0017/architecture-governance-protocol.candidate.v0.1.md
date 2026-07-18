# Architecture Governance Protocol Candidate v0.1

Status: candidate evidence only
Task: T-0017

## Purpose

Define how architecture moves from candidate to reviewable baseline before
implementation planning begins.

## Architecture First Rule

Build work packets must be derived from architecture nodes. Codex must not
generate implementation packets directly from filenames, UI wishes, or
temporary ideas.

## Architecture Node Minimum

Each node should include:

```text
node_id | node_type | level | parent | children | responsibility | contracts | data_owned | dependencies | work_packet_refs | validation_path | rollback_or_isolation_path | linked_ids
```

## Required Architecture Views

- system context
- user and external system boundary
- business capability map
- module/component map
- integration and event map
- data ownership and authority model
- trust boundaries
- deployment shape candidate
- operational and observability assumptions
- rollback and isolation strategy
- ADR candidates

## ADR Rule

Create ADR candidates for decisions affecting:

- cost
- timeline
- data ownership
- privacy/security
- integration strategy
- deployment or operations
- future reversibility

ADR approval remains separate from build approval.

## Baseline Review

Architecture baseline may be recommended only when:

- all MVP requirements map to architecture nodes
- every node has a validation path
- module dependency graph has no unreviewed cycle
- sensitive data has security treatment
- major decisions have ADR candidates
- rollback and isolation paths are credible
- unresolved P0/P1 findings are absent

## Forbidden Interpretations

- Architecture baseline is not build approval.
- Architecture baseline is not implementation readiness.
- Architecture baseline is not release readiness.
- Architecture baseline is not AGENTS.md or runtime behavior change.
