# Enforcement Architecture Candidate v0.1

Status: candidate evidence only
Task: T-0019

## Purpose

Design how the T-0017 real-project governance package can become enforceable,
auditable, and hard to skip.

This document repairs the T-0018 P1 finding:

```text
FIND-T0018-P1-001
```

## Core Decision

Use a layered enforcement model:

| Layer | Name | What It Does | Authority Level |
| --- | --- | --- | --- |
| L0 | AI discipline | Human-readable rules in `AGENTS.md`, `.ai`, and evidence docs. | Advisory only |
| L1 | Deterministic scripts | `validate_state.py` and later scripts read machine files and fail closed on pending gates or missing evidence. | Local mechanical blocker |
| L2 | Policy guard / wrapper | Future guarded entrypoints classify requested actions before shell, file write, build, deploy, or high-risk steps. | Pre-action blocker when installed later |
| L3 | Tool-entry enforcement | Future MCP / hook / tool middleware prevents sensitive tool calls unless the gate register allows them. | Hardest-to-skip runtime blocker |

T-0019 designs L1-L3 but installs none of them.

## Primary Objects

| Object | Location Candidate | Purpose |
| --- | --- | --- |
| Gate register | `.ai/evidence/<task-id>/gate-register.<stage>.yaml` | Machine-readable stage, gates, checks, evidence, forbidden scope, and blocking state. |
| Checker catalog | `.ai/checkers/catalog.yaml` or later equivalent | Declares checker IDs, stages, required runtime, gate binding, and blocking semantics. |
| Checker result | `.ai/evidence/<task-id>/checkers/<checker-id>.<run-id>.yaml` | Records structured checker output, status, evidence, and gate impact. |
| Tool restriction policy | `.ai/tool-entry-restrictions.yaml` or later equivalent | Maps sensitive action classes to required gates and denied tools. |
| Evidence lock | `.ai/evidence/<task-id>/evidence-lock.<stage>.yaml` | Frozen proof that stage checks were completed before transition. |
| Audit report | `.ai/evidence/<task-id>/audit.<trigger>.<timestamp>.yaml` | Independent closeout or transition audit of register, checker results, and exceptions. |

## Lifecycle Enforcement

Every non-trivial real-project stage should have:

1. A stage route profile.
2. A gate register initialized with all mandatory checkers as `pending`.
3. Required evidence paths for every stage artifact.
4. A forbidden-scope block covering actions outside the current gate.
5. Checker results or approved unavailable-checker exceptions.
6. A gate receipt that references the checker results.
7. A frozen evidence lock before stage transition.

Pending is blocking. Missing is blocking. Stale evidence is blocking when the
artifact changed after the checker run.

## What Becomes Deterministic

| Concern | Deterministic Enforcement Candidate |
| --- | --- |
| Pending user gate | `validate_state.py` fails when any gate status is `pending`. |
| Missing required artifact | Stage checker fails when required file is absent. |
| Missing checker result | Gate register checker fails while item remains `pending`. |
| Stale checker result | Checker result run time older than target artifact mtime blocks stage promotion. |
| Forbidden scope | Policy guard blocks action classes not listed in approved gate scope. |
| High-risk action | Tool-entry restriction requires a separate explicit gate. |
| Stale handoff | Handoff checker compares current task/gate/state against `.ai/HANDOFF.md`. |
| Reviewer PASS misuse | Gate receipt checker rejects review/test/validator evidence as approval. |
| Real-project confusion | Real-project entry checker requires target root, approved entry gate, and evidence location. |

## What Remains AI Discipline

Until a later implementation gate installs enforcement, Codex must still:

- choose the correct workflow from the latest user request
- avoid broad interpretation of scope
- avoid writing outside approved paths
- decide when to consult relevant contracts
- keep user-facing explanations clear
- identify when a new explicit gate is needed

These are still self-discipline in T-0019. The design makes them candidates for
later script or tool enforcement, but does not claim they are enforced now.

## Stage Adoption Path

| Phase | Scope | Required Future Gate |
| --- | --- | --- |
| P0 Design | Candidate docs only. | Current T-0019 gate |
| P1 Review | Review T-0019 candidate against T-0018 findings. | Separate review-only gate |
| P2 Prototype | Add scripts/schemas in this governance lab only. | Separate implementation gate |
| P3 Smoke test | Run against sample governance task, no real project. | Separate verification gate |
| P4 Project-local install | Install deterministic checks into this project only. | Separate installation/rule-change gate |
| P5 Real-project pilot | Apply to one explicitly named real project. | Separate real-project entry gate |
| P6 Tool-entry enforcement | Enable hooks/MCP/tool middleware. | Separate runtime/tool enablement gate |

## Non-Authorization

This candidate does not authorize implementation, installation, real-project
entry, `AGENTS.md` modification, runtime/tool enablement, deployment, rollback,
database, permission, secret, payment, production-data, or migration action.
