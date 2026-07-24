# Checker Implementation Plan Candidate v0.1

Status: candidate evidence
Task: T-0022

## Objective

Plan a future lab-local checker prototype that turns T-0019 governance
concepts into deterministic, auditable scripts without enabling runtime
enforcement.

## Candidate Components

| Component | Candidate Path | Purpose |
| --- | --- | --- |
| Gate register schema | `.ai/schemas/gate-register.schema.yaml` | Validate required gate, artifact, checker, scope, and transition fields. |
| Checker result schema | `.ai/schemas/checker-result.schema.yaml` | Standardize checker output. |
| Checker catalog | `.ai/checkers/catalog.yaml` | Declare checker IDs, stages, blocking level, and unavailable policy. |
| Gate register validator | `.ai/checkers/validate_gate_register.py` | Fail closed on pending gates, missing artifacts, stale checkers, and invalid exceptions. |
| Checker runner | `.ai/checkers/run_governance_checks.py` | Execute selected deterministic checks and write structured results. |

## Minimum Checks For Prototype

- `governance-state-check`
- `pending-gate-check`
- `required-artifact-presence-check`
- `high-risk-gate-separation-check`
- `stale-handoff-check`
- `evidence-lock-check`
- `tool-entry-authorization-check` as policy simulation only

## Required Schema Repairs

The future schema must add positive authorization fields:

- `allowed_action_classes`
- `allowed_tools`
- `allowed_paths`
- `approval_evidence`
- `approval_text`
- `scope_source_gate_id`

## Blocking Semantics

Direct checkers block on `pending`, `failed`, `blocked`,
`manual_pending`, and invalid `unavailable`. Checkers remain evidence
producers only; they never approve gates.

## Boundary

This plan does not implement the components. Any future code creation requires
a separate implementation gate.
