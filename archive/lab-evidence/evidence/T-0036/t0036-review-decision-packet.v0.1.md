# T-0036 Review Decision Packet v0.1

## Outcome Of This Registration

This packet creates a user decision point for a future review. It does not execute review, repair, installation, activation, runtime enablement, downstream work, or real-project entry.

## Source Of Truth

- T-0031: reviewed findings and repair plan.
- T-0033: isolated-candidate provenance, boundary, recovery, and activation-boundary evidence.
- T-0034: canonical requirements, `PCC-2026-07-16-R1`, HANDOFF writing standard, checkpoint/interface additive chain, final fresh rereview, and downstream separation.
- T-0035: task, Gate, decision packet, preflight, commands, executor report, final manifest, protected-boundary postcheck, and changed-path manifest.
- Current isolated candidate: exactly 10 files.
- Protected baseline: project `AGENTS.md` and the 26 global Project Governor files bound by the T-0035 final manifest.
- Registration-time HANDOFF defect evidence and T-0036 governance records.

Exact source fingerprints are in `t0036-review-subject-freeze-manifest.v0.1.md`.

## Review Questions

1. Does the candidate correctly enforce create, approve/reject, execution-start, request separation, no same-turn chaining, path containment, and transaction recovery?
2. Does structured HANDOFF/checkpoint generation preserve canonical authority and fresh-session control semantics?
3. Are final-validation and completion claims genuinely bound to current bytes, sizes, mtimes, commands, and test counts?
4. Do tests exercise externally observable behavior and failure paths rather than only implementation details?
5. Is the 1,382-line `governor_lib.py` responsibility concentration a material architecture/readability/security/recovery risk?
6. Are candidate/global/environment/installation/activation boundaries intact?

## Five-Axis Method

- Correctness: requirements, edge/error paths, state transitions, evidence freshness, and semantic consistency.
- Readability: naming, control flow, complexity, test intent, and maintainability.
- Architecture: module boundaries, responsibility concentration, dependency direction, and interface ownership.
- Security: untrusted JSON/path/YAML boundaries, traversal/reparse handling, authority escalation, injection, and evidence integrity.
- Performance: bounded parsing, hashing, inventory, subprocess behavior, and avoidable whole-file/whole-tree work.

## Preliminary Leads

Three leads are registered separately. They are not findings, verdicts, or required conclusions. A fresh reviewer must reproduce, rebut, or adjust them and continue searching beyond them.

## Risk And Failure Rules

- Frozen-subject drift: `BLOCKED` before substantive review.
- Reviewer independence unavailable: `BLOCKED`.
- Missing/conflicting authority or business decision: `USER_DECISION_REQUIRED`.
- Review finding: preserve evidence; do not repair in the review turn.
- Any scope expansion or protected-path write: stop with a scope violation.

## User Authority

The user owns the Gate decision and final acceptance. Reviewer, tests, validators, audits, and AI conclusions provide evidence only.
