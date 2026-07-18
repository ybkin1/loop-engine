# T-0034 L0R3 Retry1 P1 Repair Gate Request v0.1

Requested: `2026-07-17T11:11:27.1894540+08:00`

Gate: `G-T-0034-REPAIR-L0R3-RETRY1-P1-FINDINGS-V0-4`; status and decision: `pending`.

## Source Rereview

Source Gate: `G-T-0034-FRESH-INDEPENDENT-REREVIEW-L0R2-V0-3-RETRY-1`

Source verdict: `REPAIR_REQUIRED`

Source evidence:

- `.ai/evidence/T-0034/t0034-l0r2-p1-fresh-independent-rereview-retry.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r2-p1-fresh-independent-rereview-retry-validation.v0.1.md`

## Exact Scope

This Gate may authorize only additive repair for these two retry findings:

- `T0034-L0R3-RETRY1-F001-HF003`
- `T0034-L0R3-RETRY1-F002-DEFAULTS`

No other finding, artifact status, task status, downstream task, downstream Gate, implementation, installation, activation, closeout, or user acceptance is in scope.

## Repair Goals

### F001

Fix the inconsistency between `HF-003 missing terminal LF` and the full-line marker cardinality / terminal LF rules. The repair must make normal and adversarial framing vectors independently reproducible under the declared execution order.

### F002

Remove the conflict between `Verdict/v2.0` required fields and empty-list defaults / consumer defaulting. The repair must explicitly define producer required behavior, consumer defaulting behavior, missing-field behavior, and compatibility rules without ambiguity.

## Exact Allowed Paths For Gate Registration

- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-gate-request.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-freeze-manifest.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-registration-commands.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

## Exact Allowed Paths After Later Approval Plus Exact Execution Request

- `.ai/evidence/T-0034/hash-framing-golden-vectors.v0.4.md`
- `.ai/evidence/T-0034/controller-agent-interface-schemas.v0.4.md`
- `.ai/evidence/T-0034/finding-verdict-schema-compatibility-matrix.v0.4.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-executor-report.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-commands.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-validation.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-changed-path-manifest.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-protected-baseline.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-cross-file-consistency.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

## Frozen Baseline And Protected Subjects

Protected baselines are listed in `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-freeze-manifest.v0.1.md`.

Frozen v0.3 repair subjects and retry review evidence must be read-only. Any mismatch in protected path, byte size, or SHA-256 before a future repair execution returns `BLOCKED`.

The fourteen v0.2 review subjects, `.ai/tasks/T-0034.md`, `.ai/task_graph.yaml`, the isolated candidate, and global Project Governor files remain protected by incorporated baselines and are not repair write targets.

## Decision And Execution Separation

- Gate creation is not approval.
- Approval is not repair execution.
- A later exact execution request is required after approval before any repair may begin.
- Approval must leave `repair_execution_authorized: false` and `execution_status: approved_not_started`.

## Validation Plan

- Strict UTF-8 decode and YAML/Markdown structural reads for all new or modified allowed paths.
- Verify changed paths are an exact subset of allowed execution paths.
- Verify all protected subjects by exact path, byte size, and SHA-256 before and after repair execution.
- For F001, independently reproduce marker cardinality, marker order, terminal-LF behavior, byte count, SHA-256, and normal/adversarial vectors.
- For F002, verify `Verdict/v2.0` has a single unambiguous required/default/missing-field contract and compatible producer/consumer rules.
- Verify task file, task graph, v0.2 subjects, v0.3 subjects, retry review evidence, isolated candidate, and global Project Governor files remain unchanged.
- Run `validate_state.py` and `audit_handoff.py`, expecting only the pending Gate plus six preserved historical mismatches during Gate registration.

## Independent Rereview Plan

- This repair Gate does not authorize independent rereview.
- If repair is later approved and executed, execution must stop after validation.
- A later separate pending rereview Gate is required before any repaired v0.4 slice can be considered independently resolved.
- Reviewer verdicts remain evidence only and cannot imply artifact PASS, T-0034 closeout, project PASS, or user acceptance.

## Rollback And Failure Recovery

- Protected-subject mismatch returns `BLOCKED`.
- Path or forbidden-effect breach returns `SCOPE_VIOLATION`.
- Partial additive evidence may be preserved truthfully if validation cannot complete.
- Historical evidence must not be deleted or overwritten.
- Destructive cleanup, rollback, repair expansion, closeout, or acceptance requires a separate explicit user Gate.

## Forbidden Effects

Do not modify any frozen subject or existing review evidence. Do not repair now. Do not rereview. Do not close T-0034. Do not install, activate, implement runtime behavior, create downstream tasks or Gates, enter a real project, deploy, migrate, change permissions, handle secrets, touch production data, or perform payment actions.

Approval phrase: `批准 G-T-0034-REPAIR-L0R3-RETRY1-P1-FINDINGS-V0-4`

Rejection phrase: `拒绝 G-T-0034-REPAIR-L0R3-RETRY1-P1-FINDINGS-V0-4`

Later execution phrase: `执行 G-T-0034-REPAIR-L0R3-RETRY1-P1-FINDINGS-V0-4`
