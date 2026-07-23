# T-0036 Repair Gate Request v0.2

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Requested status remains `pending`. This revision does not approve or execute repair.

This request supersedes the decision semantics of `t0036-repair-gate-request.v0.1.md` while preserving its exact candidate scope and forbidden effects.

## Revised Decision Basis

- F001/F002 target is secure isolation with production authority lifecycle unavailable, not restored operational authority.
- Installation eligibility remains blocked even after repair PASS until separately gated host identity integration, live structured-state provisioning, fresh independent rereview, and a later installation Gate.
- ProjectContinuity/v1, TransactionRegistry/v1, and EvidenceManifest/v1 now have exact sources, persistence paths, owners, schemas, missing behavior, and hash binding.
- `.ai/PROJECT.md`, `.ai/CONTRACTS.md`, and the T-0034 PCC/CDFT contracts are added to the read-only protected baseline.
- T-0036's no-repair-Gate wording is explicitly historical to the completed review-registration stage.
- `E2E-CURRENT-001` adds a real positive temporary-mirror path for HANDOFF, lifecycle projection, checkpoint progression, audit, and controlled validation without claiming authority transition availability.

## Effective Evidence

- `.ai/evidence/T-0036/t0036-repair-decision-packet.v0.2.md`
- `.ai/evidence/T-0036/t0036-repair-test-plan.v0.2.md`
- `.ai/evidence/T-0036/t0036-repair-structured-state-contracts.v0.2.md`
- `.ai/evidence/T-0036/t0036-repair-candidate-and-protected-baseline.v0.2.yaml`

Approval: `批准 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Rejection: `拒绝 G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Approval remains a decision only; execution still requires a later distinct exact request.
