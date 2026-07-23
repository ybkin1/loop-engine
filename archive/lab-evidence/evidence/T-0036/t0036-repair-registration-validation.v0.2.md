# T-0036 Repair Gate Revision Validation v0.2

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

## Gate State

- Gate count for exact ID: `1`.
- Pending Gate count: `1`.
- Status: `pending`.
- Decision: `pending`.
- `repair_authorized`: `false`.
- `implementation_authorized`: `false`.
- Production authority lifecycle available: `false`.
- F001/F002 result: `SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE`.
- Installation eligibility after repair: `BLOCKED`.
- Blocking findings: `9`.

## Mechanical Commands

Global validator output remains:

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0036
[error] Pending gate(s) require user decision before continuing: G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1
```

Exit `2` is expected solely because the Gate remains pending.

Global HANDOFF audit output remains:

```text
[error] Pending gate(s) not resolved: G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1
```

Exit `2` is expected solely because the Gate remains pending.

## Structured Parsing And Projection

- `.ai/gates.yaml`, `.ai/state.yaml`, `.ai/task_graph.yaml`, and the v0.2 baseline YAML parse successfully with `yaml.safe_load`.
- T-0036 task and task graph both remain `active`.
- `state.current_gate_id` remains the exact pending repair Gate.
- The historical heading is now `Historical Review-registration Strict Boundaries (2026-07-18)` and explicitly states that its old no-repair-Gate rule does not prohibit the later user-authorized current Gate.
- Gate references point to the effective v0.2 request, decision packet, test plan, structured-state contract, and protected-baseline revision while preserving v0.1 base hashes.

## Effective Protected Baseline

- v0.1 subjects: `39`.
- v0.2 protected additions: `4`.
- Effective checked subjects: `43`.
- SHA-256/size/mtime_ns mismatches: `0`.
- New read-only protected additions: `.ai/PROJECT.md`, `.ai/CONTRACTS.md`, `PCC-2026-07-16-R1`, and `CDFT-2026-07-16-R1` source files.
- Candidate inventory remains 10 files, 2 directories, 0 reparse points, and 0 cache/compiled artifacts.
- Candidate PATH/PYTHONPATH references remain `0/0`.
- T-0037 exists: `false`.

## Contract Coverage

- `ProjectContinuity/v1`: exact normative sources, `.ai/project_continuity.yaml`, L0 registrar writer, reader ownership, `RECOVERY_REQUIRED` missing behavior, source/semantic/file hash binding.
- `TransactionRegistry/v1`: exact PCC/CDFT sources, `.ai/transaction_registry.yaml`, L0 transaction/controller writer, read-only candidate, `NOT_ESTABLISHED` missing behavior, fence/ack/source/semantic/file binding.
- `EvidenceManifest/v1`: exact PCC/CDFT/F009 sources, `.ai/evidence/<task-id>/evidence-manifest.v1.yaml`, authorized evidence-aggregator writer, `EVIDENCE_MANIFEST_REQUIRED` missing behavior, bounded streamed manifest/entry/file binding.
- Live structured-state files were not created or modified.

## Positive Path Coverage

`E2E-CURRENT-001` is registered as a mandatory RED -> GREEN scenario using a temporary mirror of the current project's protected structure. It requires real validator/close/audit/controlled-runner subprocesses, structured HANDOFF/lifecycle output, checkpoint `PENDING_SUCCESSOR_ACK -> STABLE_FIXTURE_ONLY` progression with a matching fixture acknowledgment, actual command evidence binding, and zero live-project drift. Production Stable remains unavailable.

The positive path begins from a durable pre-existing lifecycle snapshot and does not claim isolated authority transitions are available. Installation eligibility remains blocked.

## Classification

- Disk facts: current hashes, paths, Gate status, counts, parser results, validator/audit outputs, and candidate inventory.
- Historical evidence: v0.1 Gate package, T-0035 implementation evidence, and T-0036 review findings.
- AI technical specification: v0.2 schemas, ownership model, positive E2E design, and installation eligibility policy.
- User decision not made: approve or reject the revised pending Gate.

No candidate repair, approval, execution, fresh rereview, installation, activation, runtime enablement, or real-project action occurred.
