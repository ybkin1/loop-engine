# Validation And Test Plan Candidate v0.1

Status: candidate evidence
Task: T-0022

## Validation Goal

A future prototype should prove that governance checks fail closed for missing
or unsafe evidence and pass only for explicitly authorized, complete records.

## Candidate Test Levels

| Level | Purpose |
| --- | --- |
| Schema tests | Validate sample gate registers, checker results, and guard decisions. |
| Unit tests | Exercise checker logic for pending gates, missing artifacts, stale evidence, and forbidden scope. |
| Integration tests | Run validator on sample `.ai/tests/samples/` tasks. |
| Negative tests | Prove reviewer PASS, validator success, or AI recommendation cannot approve a gate. |
| Boundary tests | Prove high-risk classes require separate gates. |

## Required Negative Cases

- Pending gate blocks all work except exact user decision recording.
- Missing approval evidence blocks stage promotion.
- Missing required artifact blocks stage promotion.
- Checker result older than target artifact blocks stage promotion.
- Tool-entry simulation denies deployment, rollback, database, secret,
  payment, production-data, migration, `AGENTS.md`, and runtime/tool
  enablement without separate gates.
- Guard decision enum rejects unknown or superseded values.

## Tamper-Evidence Validation

The future prototype should create:

- hash manifest for required evidence files
- append-only receipt list for gate decisions
- evidence lock referencing hashes and checker result IDs
- audit report comparing current files to the lock

## Current Task Boundary

No tests are implemented or run by T-0022 beyond existing governance
validation scripts. This document is a candidate plan only.
