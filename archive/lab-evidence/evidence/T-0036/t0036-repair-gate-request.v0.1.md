# T-0036 Repair Gate Request v0.1

Requested Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Requested status: `pending`.

## Decision Requested

Approve or reject a future bounded repair of all nine T-0036 findings in the existing isolated T-0035 candidate. Gate approval would record authority only; repair would still require a later independent message containing the exact execution phrase.

## Scope

- Repair F001-F009 using the exact candidate paths and test/acceptance mapping in `t0036-repair-decision-packet.v0.1.md`.
- Keep authority-bearing isolated CLI transitions fail closed with `USER_DECISION_REQUIRED` because no trusted Codex host user-message/turn source exists.
- Use a controlled final-validation runner, normalized continuity/lifecycle/transaction state, independent producer/auditor construction, and bounded manifest-driven streaming evidence hashing.
- Preserve `BOUNDARY.md` history, append `PROVENANCE.yaml` lineage, and keep `NOT_INSTALLED`/`NOT_ACTIVATED` byte-for-byte unchanged.
- Stop after repair evidence; do not perform fresh independent rereview in the repair execution.

## Exclusions

No installation, activation, global Project Governor or `AGENTS.md` modification, host identity adapter, controller/agent/automation/skill/MCP/plugin/hook/protocol enablement, T-0037 creation, real-project entry, deployment, migration, database, permission, secret, payment, production-data action, user acceptance, or project PASS.

## Evidence

- Decision packet: `.ai/evidence/T-0036/t0036-repair-decision-packet.v0.1.md`
- Test plan: `.ai/evidence/T-0036/t0036-repair-test-plan.v0.1.md`
- Baseline: `.ai/evidence/T-0036/t0036-repair-candidate-and-protected-baseline.v0.1.yaml`

## Decision Phrases

Approval: `批准 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Rejection: `拒绝 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Later execution, only after approval in an independent message:

`执行已批准的 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`
