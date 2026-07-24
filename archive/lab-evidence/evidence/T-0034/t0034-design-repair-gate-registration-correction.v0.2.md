# T-0034 Pending Design Repair Gate Registration Correction v0.2

Target Gate: `G-T-0034-REPAIR-DESIGN-COVERAGE-AND-ASSURANCE-GAPS`

This additive record corrects registration quality only. It does not approve or execute the pending Gate and does not execute design repair.

## Corrections

1. The current Gate authorizes additive design repair and repair-execution evidence only.
2. Fresh independent L0 review is removed from `exact_allowed_paths` and requires a later separate pending review Gate.
3. Repair execution must stop after its artifacts and deterministic execution evidence are complete.
4. `.ai/tasks/T-0034.md` and `.ai/task_graph.yaml` are removed from future repair write authorization; T-0034 remains `active` and cannot be closed by this Gate.
5. `.ai/gates.yaml`, `.ai/state.yaml`, and `.ai/HANDOFF.md` remain limited to this Gate's decision/execution metadata, current-gate projection, evidence pointers, current result, verified/unverified status, and next action. They cannot change task scope, task status, downstream task existence, authorization boundaries, or user acceptance.
6. HANDOFF uses the exact next-action marker `approve or reject` while the Gate remains pending.
7. The complete immutable 15-file manifest is recorded in `t0034-design-repair-changed-path-baseline.v0.2.md`.

## Corrected Decision Phrases

Approval: `批准修正后的 G-T-0034-REPAIR-DESIGN-COVERAGE-AND-ASSURANCE-GAPS`

Rejection: `拒绝修正后的 G-T-0034-REPAIR-DESIGN-COVERAGE-AND-ASSURANCE-GAPS`

Independent review, artifact PASS, T-0034 PASS, project PASS, closeout, and user acceptance remain unauthorized and unasserted.
