# Verification, Acceptance, Convergence, And Recovery Rules v0.2

Contract ID: `VACR-2026-07-16-R1`. Satisfies `OUT-07` and contributes to `WS-06` and `WS-08`.

## 1. Verdict And PASS Layers

| Layer | Meaning | Required authority |
|---|---|---|
| `local_slice` | Declared checks for one bounded packet passed. | Packet owner may report evidence only. |
| `artifact` | One immutable artifact satisfies its complete mapped requirements under the selected AssuranceProfile. | Independent review evidence; no user effect. |
| `task` | All task outputs, acceptance, dependencies, findings, and boundaries are satisfied. | Task controller evidence plus separately authorized closeout decision. |
| `project` | Integrated product/roadmap outcome is coherent and release-ready for the declared phase. | Project controller evidence plus required gates. |
| `user_acceptance` | User accepts delivered outcome and residual risk. | Explicit user message only. |

No automatic transition exists among layers. A lower PASS cannot populate a higher-layer field.

## 2. VerificationPlan Admission

A plan is admissible only if it contains canonical revision/hash, complete requirement mapping, deterministic checks, adversarial vectors, protected baselines, expected error set, evidence requirements, budgets, and stop conditions. Missing fields yield `BLOCKED` before verification begins.

## 3. Deterministic Verdict Rules

```text
if scope_violation: SCOPE_VIOLATION
else if authority_missing or baseline_conflict: USER_DECISION_REQUIRED or BLOCKED
else if any P0: BLOCKED
else if incomplete mandatory coverage or any unresolved P1: REPAIR_REQUIRED
else if stale evidence, missing result, conflict, or blocking queue: REPAIR_REQUIRED
else if all criteria/checks/evidence current and no blockers: PASS at declared layer only
```

Uncertainty is reported; it is never rounded up to PASS.

## 4. Acceptance Rules

- `ACC-R01`: Acceptance criteria are observable, requirement-linked, and have an oracle.
- `ACC-R02`: Positive, negative, boundary, recovery, and authorization scenarios are covered.
- `ACC-R03`: User acceptance remains an explicit later decision and cannot be inferred from technical evidence.
- `ACC-R04`: Missing product/visual/API/architecture/code golden baseline is a blocking gap when required by scope.
- `ACC-R05`: Downstream readiness requires boundary compliance and residual-risk disclosure, not only document presence.
- `ACC-R06`: Design repair completion means complete artifacts/evidence and stop-before-review, not artifact/task PASS.

## 5. Finding Lifecycle

```text
OPEN -> ACCEPTED_FOR_REPAIR -> REPAIRED_PENDING_REVIEW -> VERIFIED -> CLOSED
OPEN -> USER_DECISION_REQUIRED | BLOCKED | REJECTED
any non-terminal -> SUPERSEDED_BY_ADDITIVE_FINDING
```

Only a later independent review may move `REPAIRED_PENDING_REVIEW` to `VERIFIED`. Only authorized task closeout may close task-level findings. Original findings remain immutable.

## 6. Repair Contract

Each repair run requires enumerated findings, exact paths/effects, immutable baseline, precise change plan, deterministic validation plan, rollback/recovery, budgets, and explicit stop boundary. Repair may address only authorized findings and must produce a finding-to-change-to-check map.

Repair results:

- `REPAIR_COMPLETED_AWAITING_REVIEW`: all authorized changes/evidence complete; stop.
- `PARTIAL_ADDITIVE_EVIDENCE_WRITE`: truthful partial bytes exist; preserve and stop.
- `BLOCKED`: precondition, scope, authority, baseline, or environment prevents completion.
- `USER_DECISION_REQUIRED`: required tradeoff or scope change exceeds authority.

## 7. Convergence And No-Progress

```yaml
convergence_policy:
  max_repair_iterations_per_finding: 3
  max_same_finding_recurrence: 2
  max_no_progress_iterations: 1
  progress_measure:
    - reduced_open_blocking_findings
    - increased_requirement_coverage
    - increased_deterministic_check_passes
    - reduced_unverified_items
  terminal_states: [PASS, BLOCKED, USER_DECISION_REQUIRED, BUDGET_EXCEEDED]
```

An iteration has no progress if artifact hashes change but none of the progress measures improve. No-progress freezes the slice and escalates; it never triggers indefinite prompt/document refinement.

## 8. Budget And Anti-Self-Loop Rules

- Reserve capacity before writing for complete artifacts, validation, consistency checks, command/evidence records, and final report.
- Refuse output admission when the complete required set cannot fit.
- Every governance artifact must map to a delivery risk, requirement, or executable decision.
- Repeated policy wording changes without new requirement coverage or evidence are no progress.
- The system must always expose a bounded next safe action toward real delivery or user decision.

## 9. Recovery Rules

| Failure | Recovery |
|---|---|
| Precondition/hash mismatch before write | Stop; write no target artifact; report blocker. |
| Partial additive artifact | Preserve bytes and exact changed paths; mark partial; require separate recovery decision for deletion. |
| Invalid UTF-8/YAML/schema | Do not commit candidate verdict; repair within same authorized path if budget remains, otherwise stop partial. |
| Protected baseline changed | `SCOPE_VIOLATION` or `BLOCKED`; no automatic restoration outside authority. |
| Validation command unavailable | Record command/error; use no substitute unless contract explicitly permits it. |
| Crash after write | Recover from changed-path manifest and hashes; do not assume completion. |
| Conflicting requirement revisions | Freeze affected effects and request user decision. |

Rollback is a separate effect when destructive. Additive correction is preferred; original evidence is retained.

## 10. Closeout Blockers

Task closeout is blocked by any open P0/P1, incomplete required output, missing acceptance oracle, stale/conflicting evidence, unreviewed repair, blocking queued delta, missing user decision, or unauthorized effect. This Gate explicitly prohibits T-0034 closeout.

## 11. Verification Checks

- `MC-PASS-001`: reject cross-layer PASS inference.
- `MC-COVER-001`: complete WS/OUT/acceptance/test/review-role mapping.
- `MC-FIND-001`: legal finding lifecycle transitions.
- `MC-CONV-001`: iteration and no-progress thresholds.
- `MC-RECOVERY-001`: failure maps to deterministic safe action.
- `MC-LOOP-001`: governance output has requirement/evidence/delivery-risk trace.
- `ADV-PASS-001`: user says “looks good” and system infers task PASS; reject.
- `ADV-CONV-001`: same finding rewritten three times without coverage gain; freeze/escalate.
- `ADV-RECOVERY-001`: partial write is deleted to make report clean; reject as evidence violation.

## 12. Boundary

These rules do not perform verification review, close T-0034, implement checkers, install, activate, deploy, or accept delivery.
