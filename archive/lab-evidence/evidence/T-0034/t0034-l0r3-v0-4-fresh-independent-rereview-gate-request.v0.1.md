# T-0034 L0R3 v0.4 Fresh Independent Rereview Gate Request v0.1

Requested: `2026-07-17T13:29:53.4480633+08:00`

Gate: `G-T-0034-FRESH-INDEPENDENT-REREVIEW-L0R3-RETRY1-V0-4`; status and decision: `pending`.

## Source Repair

Source repair Gate: `G-T-0034-REPAIR-L0R3-RETRY1-P1-FINDINGS-V0-4`

Source repair status: `repair_completed_awaiting_independent_rereview`

Source repair scope:

- `T0034-L0R3-RETRY1-F001-HF003`
- `T0034-L0R3-RETRY1-F002-DEFAULTS`

## Exact Scope

This Gate may authorize only a fresh independent read-only rereview of the frozen v0.4 repair artifacts and execution evidence listed in `t0034-l0r3-v0-4-fresh-independent-rereview-freeze-manifest.v0.1.md`.

The rereview must assess whether the bounded v0.4 repair resolves the two source findings without changing any subject. It must not review unrelated artifacts, expand into v0.2/v0.3 design review, close T-0034, or infer user acceptance.

## Frozen Rereview Subjects

The frozen rereview subjects are exactly:

- `.ai/evidence/T-0034/hash-framing-golden-vectors.v0.4.md`
- `.ai/evidence/T-0034/controller-agent-interface-schemas.v0.4.md`
- `.ai/evidence/T-0034/finding-verdict-schema-compatibility-matrix.v0.4.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-executor-report.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-commands.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-validation.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-changed-path-manifest.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-protected-baseline.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-retry1-p1-repair-cross-file-consistency.v0.1.md`

These subjects are read-only. Any path, size, or SHA-256 mismatch before content rereview returns `BLOCKED`.

## Allowed Paths For Gate Registration

- `.ai/evidence/T-0034/t0034-l0r3-v0-4-fresh-independent-rereview-gate-request.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-v0-4-fresh-independent-rereview-freeze-manifest.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-v0-4-fresh-independent-rereview-registration-commands.v0.1.md`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

## Allowed Paths After Later Approval And Exact Execution Request

- `.ai/evidence/T-0034/t0034-l0r3-v0-4-fresh-independent-rereview.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-v0-4-fresh-independent-rereview-commands.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-v0-4-fresh-independent-rereview-validation.v0.1.md`
- `.ai/evidence/T-0034/t0034-l0r3-v0-4-fresh-independent-rereview-changed-path-manifest.v0.1.md`
- Minimal truthful execution projection in `.ai/gates.yaml`, `.ai/state.yaml`, and `.ai/HANDOFF.md`

## Reviewer Independence

The reviewer must be genuinely fresh and independent from the v0.4 repair author and must not be the same active thread/controller that authored the repair. The reviewer must disclose any context, identity, evidence, or scope limitation before verdict. If independence cannot be established, the verdict must be `BLOCKED` or `USER_DECISION_REQUIRED`.

## Preflight

Before content rereview, the reviewer must verify exact relative path, byte size, and SHA-256 for all nine frozen subjects. Any mismatch stops rereview before content analysis and returns `BLOCKED`.

## Substantive Rereview Plan

- `T0034-L0R3-RETRY1-F001-HF003`: independently verify that v0.4 makes `HF-003` reproducible under full-line marker cardinality and terminal-LF rules; verify the normal payload count/hash and adversarial vector outcomes.
- `T0034-L0R3-RETRY1-F002-DEFAULTS`: independently verify that v0.4 removes the conflict between `Verdict/v2.0` required fields and empty-list defaults / consumer defaulting; verify producer-required, consumer defaulting, missing-field, optional-extension, compatibility, and migration behavior.
- Cross-file consistency: verify v0.4 artifacts, execution evidence, changed-path manifest, protected baseline, and validation evidence agree with each other and with the source findings.

## Verdict Schema

Allowed verdicts:

- `PASS`
- `REPAIR_REQUIRED`
- `BLOCKED`
- `USER_DECISION_REQUIRED`
- `SCOPE_VIOLATION`

The verdict is evidence only. It is not user acceptance, T-0034 closeout, artifact PASS beyond the reviewed slice, project PASS, downstream authorization, implementation, installation, activation, runtime enablement, or real-project entry.

## Forbidden Effects

Do not modify, normalize, replace, rename, delete, or append to any frozen subject or existing review evidence. Do not repair. Do not close T-0034. Do not claim artifact PASS, T-0034 PASS, project PASS, or user acceptance. Do not install, activate, implement runtime behavior, create downstream tasks or Gates, enter a real project, deploy, migrate, change permissions, handle secrets, touch production data, or perform payment actions.

## Rollback And Failure Recovery

- Frozen subject mismatch returns `BLOCKED` before content rereview.
- Independence failure returns `BLOCKED` or `USER_DECISION_REQUIRED`.
- Path or forbidden-effect breach returns `SCOPE_VIOLATION`.
- Truthful partial additive evidence may be preserved if validation cannot complete.
- Historical evidence must not be deleted or overwritten.
- No destructive cleanup or rollback is authorized without a separate explicit recovery Gate.

Approval phrase: `批准 G-T-0034-FRESH-INDEPENDENT-REREVIEW-L0R3-RETRY1-V0-4`

Rejection phrase: `拒绝 G-T-0034-FRESH-INDEPENDENT-REREVIEW-L0R3-RETRY1-V0-4`

Later execution phrase: `执行 G-T-0034-FRESH-INDEPENDENT-REREVIEW-L0R3-RETRY1-V0-4`
