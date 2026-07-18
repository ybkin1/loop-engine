# T-0034 Fresh L0 Review Changed-Path Manifest v0.1

## Authorized Changed Paths

| Path | Change | Purpose |
|---|---|---|
| `.ai/evidence/T-0034/t0034-repair-independent-l0-review.v0.2.md` | created | Independent findings and evidence-only verdict. |
| `.ai/evidence/T-0034/t0034-fresh-l0-review-commands.v0.1.md` | created | Truthful command and exit-code record. |
| `.ai/evidence/T-0034/t0034-fresh-l0-review-validation.v0.1.md` | created | Deterministic and boundary validation. |
| `.ai/evidence/T-0034/t0034-fresh-l0-review-changed-path-manifest.v0.1.md` | created | This exact containment record. |
| `.ai/gates.yaml` | modified | Execution request, timing, evidence pointers, and evidence-only verdict. |
| `.ai/state.yaml` | modified | Review execution checkpoint and completion note. |
| `.ai/HANDOFF.md` | modified | Current result, findings, boundaries, and next safe action. |

All changed paths are within the Gate's `exact_allowed_paths`. Frozen subjects, `.ai/tasks/T-0034.md`, `.ai/task_graph.yaml`, repair artifacts outside the frozen set, candidate/global Project Governor, and downstream task records were not written.

## Protected Baseline

| Path | Size | SHA-256 |
|---|---:|---|
| `.ai/tasks/T-0034.md` | 3897 | `932053AC7325AF3BC4BC6212F5F91705423527C8FDD3922EF876C64B4125D905` |
| `.ai/task_graph.yaml` | 10191 | `4D5BA7A55F613D1E08A9EE81DC67FADDA0D149F589C079B6CB18347BF8CC2C14` |

The fourteen frozen subject hashes remain governed by `t0034-fresh-l0-review-freeze-manifest.v0.1.md` and must match again after final projection.
