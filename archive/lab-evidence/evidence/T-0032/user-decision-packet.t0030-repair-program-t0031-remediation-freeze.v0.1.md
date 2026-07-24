# User Decision Packet - T-0032

## Decision Requested

Approve or reject the bounded T-0030 repair-program governance baseline and T-0031 remediation freeze. This decision does not execute downstream work.

## Exact Paths Changed For Registration

- `.ai/tasks/T-0032.md`
- `.ai/evidence/T-0032/`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/HANDOFF.md`

## Modification Baseline

Before registration, T-0031 was completed with `REPAIR_REQUIRED`, no pending gate existed, the four governance-file hashes were recorded in `changed-path-baseline.v0.1.md`, and both startup commands returned only the six preserved historical mismatches.

## Governance Changes Approval Would Adopt

- Freeze T-0031 until repaired T-0030 is independently reviewed, installed, and explicitly activated.
- Keep Option D globally and pursue Option C only in an isolated candidate.
- Preserve the T-0033 through T-0038 ordering and separate implementation, installation, and activation gates.
- Keep tests, reviews, validators, and AI recommendations as evidence only.
- Preserve T-0030/T-0031 original evidence and append future repair/reverification results.
- Require a future HANDOFF contract to include an independent "origin and position" field.

## Validation Plan

- Confirm YAML parsing, one T-0032 pending gate, and matching active task/task-graph state.
- Run `validate_state.py` and `audit_handoff.py` read-only.
- Accept only the pending-gate blocker plus the six preserved historical mismatches.
- Verify no source evidence, Project Governor script, `AGENTS.md`, skill, MCP, plugin, hook, automation, protocol, or runtime/tool path changed.

## Risk Review

- The main risk is scope confusion: approval may be mistaken for implementation, installation, activation, or T-0033 authorization.
- The HANDOFF structural finding may be mistaken for authority to repair it immediately.
- Pending status intentionally blocks further governed action until the user decides.
- Six historical mismatches remain unresolved and visible.

## Rollback Or Recovery Plan

- Use the recorded pre-change hashes to restore `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/gates.yaml`, and `.ai/task_graph.yaml` only under separately authorized recovery.
- Remove only new T-0032 records if recovery is separately authorized.
- Never rewrite original T-0030/T-0031 evidence.
- Re-run both validators and stop on any error beyond the preserved six.

## T-0033 Through T-0038 Boundary

- T-0033 creates an isolated candidate and restores the activation boundary.
- T-0034 repairs only the isolated candidate.
- T-0035 independently reviews the candidate.
- T-0036 installs only through a separate installation gate.
- T-0037 activates only through a separate activation gate.
- T-0038 reverifies T-0031 and appends an addendum.

## Explicit Non-Authorization

Approving T-0032 does not approve any T-0030 repair, implementation, installation, activation, T-0031 remediation, T-0033 creation, historical repair, or automatic loop. Discovering that HANDOFF lacks an independent "origin and position" section does not authorize direct modification of that defect.

## Exact Decision Phrases

Approve:

    批准 G-T-0032-REGISTER-T0030-REPAIR-PROGRAM-T0031-REMEDIATION-FREEZE

Reject:

    拒绝 G-T-0032-REGISTER-T0030-REPAIR-PROGRAM-T0031-REMEDIATION-FREEZE
