# T-0034 L0R2 P1 Repair Gate Request v0.1

Requested at: `2026-07-16T18:57:11.2655822+08:00`

Gate: `G-T-0034-REPAIR-L0R2-P1-FINDINGS-V0-3`

Status: `pending`; decision: `pending`; approval required from: `user`.

## Purpose And Exact Scope

- `T0034-L0R2-F001`: uniquely define payload extraction, LF/end-marker boundary, byte count, SHA-256, reproduction commands, and deterministic normal/adversarial vectors.
- `T0034-L0R2-F002`: establish one canonical owner or explicit versioned base/extension relation for `Finding` and `Verdict`, including required/optional/default, compatibility, migration, breaking-change, producer/consumer, and unknown-field rules.
- Repair is additive and limited to these findings plus execution evidence.

## Exact Allowed Paths

Gate registration: these three `t0034-l0r2-p1-repair-*.v0.1.md` registration files plus `.ai/gates.yaml`, `.ai/state.yaml`, and `.ai/HANDOFF.md`.

Only after approval and a later separate exact execution request:

- `.ai/evidence/T-0034/t0034-requirements-baseline.v0.3.md`
- `.ai/evidence/T-0034/controller-agent-interface-schemas.v0.3.md`
- `.ai/evidence/T-0034/neutral-audit-charter-assurance-schemas.v0.3.md`
- `.ai/evidence/T-0034/hash-framing-golden-vectors.v0.3.md`
- `.ai/evidence/T-0034/finding-verdict-schema-compatibility-matrix.v0.3.md`
- `.ai/evidence/T-0034/t0034-l0r2-p1-repair-executor-report.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r2-p1-repair-commands.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r2-p1-repair-validation.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r2-p1-repair-changed-path-manifest.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r2-p1-repair-protected-baseline.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r2-p1-repair-cross-file-consistency.v0.1.md`
- Minimal truthful projection in `.ai/gates.yaml`, `.ai/state.yaml`, `.ai/HANDOFF.md`.

## Forbidden Paths And Effects

- All fourteen frozen v0.2 subjects and all existing review evidence are immutable.
- `.ai/tasks/T-0034.md`, `.ai/task_graph.yaml`, candidate, global Project Governor, T-0035 through T-0050, and all unlisted paths are forbidden.
- No repair now, rereview, closeout, implementation, build, install, activate, deploy, runtime change, downstream creation, real-project entry, migration, permission, secret, payment, or production-data action.

## Decision And Execution Separation

- Gate creation is not approval. Approval keeps `repair_execution_authorized: false` and sets `execution_status: approved_not_started`.
- Approval is not execution. Later exact request `?????? G-T-0034-REPAIR-L0R2-P1-FINDINGS-V0-3` is required.
- Repair stops before rereview and cannot imply artifact/task/project PASS, closeout, or user acceptance.

## Validation, Rereview, And Recovery

- Validate strict UTF-8, LF/BOM, YAML/JSON, path containment, immutable hashes, framing extraction/count/hash/vectors, and schema ownership/field/compatibility/migration/unknown-field rules.
- Verify task, graph, candidate, global Governor, frozen v0.2, and review evidence unchanged; validators may report only six preserved mismatches.
- This Gate does not authorize rereview; a later separate pending review Gate is required.
- Frozen mismatch: `BLOCKED`; boundary breach: `SCOPE_VIOLATION`; partial additive write: `PARTIAL_ADDITIVE_EVIDENCE_WRITE` with truthful evidence preserved.
- Never delete/overwrite history; destructive cleanup/rollback requires a recovery Gate; do not expand scope.

Approval: `?? G-T-0034-REPAIR-L0R2-P1-FINDINGS-V0-3`

Rejection: `?? G-T-0034-REPAIR-L0R2-P1-FINDINGS-V0-3`

Later execution: `?????? G-T-0034-REPAIR-L0R2-P1-FINDINGS-V0-3`
