# Implementation Planning Scope v0.1

Status: evidence
Task: T-0022

## Purpose

Define the implementation-planning scope for a future prototype of the T-0019
real project governance enforcement architecture.

## Planning Goal

Prepare a future implementation gate that could create lab-local, non-enabled
prototype files for deterministic governance checks.

## Included Planning Topics

- Machine-readable gate register schema.
- Checker catalog and result schema.
- Validator/checker runner boundaries.
- Policy guard and wrapper prototype boundaries.
- Evidence lock and tamper-evidence design.
- Test and validation plan.
- Rollout and recovery plan.
- Next explicit gate recommendation.

## Required T-0020 Repairs Before Implementation

| Finding | Required Planning Handling |
| --- | --- |
| `FIND-T0020-P2-001` | Add positive authorization fields such as `allowed_action_classes`, `allowed_tools`, and exact gate evidence references. |
| `FIND-T0020-P2-002` | Define deterministic tamper-evidence with hash manifests and append-only receipts. |
| `FIND-T0020-P3-001` | Normalize guard decision enum values before any prototype implementation. |

## Scope Boundary

This task creates planning evidence only. It does not create scripts, schemas,
wrappers, guards, hooks, MCP servers, skills, automations, or runtime/tool
behavior.
