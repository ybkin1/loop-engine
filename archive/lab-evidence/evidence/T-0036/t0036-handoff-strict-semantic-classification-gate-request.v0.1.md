# T-0036 HANDOFF Strict Semantic Classification Repair Gate Request v0.1

Gate: `G-HANDOFF-STRICT-SEMANTIC-CLASSIFICATION-REPAIR-V0-1`

This is a registration-only request for a new repair boundary discovered after T-0036 task closeout. It does not reopen T-0036, create T-0037, or execute implementation.

## Defect

The current HANDOFF generator and auditor implement a four-field `Project Anchors` contract, but do not persistently generate and verify the required five semantic classifications:

1. `出发点与最终目标`
2. `基本立场与职责`
3. `手段边界`
4. `当前讨论主题`
5. `当前问题与状态`

Manual correction of `.ai/HANDOFF.md` is insufficient because the next `close_session.py` run can overwrite the classification. The repair must cover canonical source mapping, generation, audit, and regression tests.

## Exact Scope

- Define the canonical five-part schema and source mapping.
- Make `close_session.py` generate all five classifications on every regeneration.
- Make `audit_handoff.py` validate exact presence, ordering, source values, separation, and stale completed-task contamination.
- Extend the semantic regression suite for merged fields, swapped fields, paraphrase drift, missing fields, stale task contamination, and repeated regeneration.
- Preserve the existing four `Project Anchors` contract as a compatibility layer unless the approved implementation plan proves a narrower replacement is required.

## Explicit Non-goals

- No changes to `.ai/PROJECT.md`, `AGENTS.md`, candidate code, candidate tests, runtime, installation, activation, or discovery behavior.
- No hooks as a substitute for the schema/generator/auditor/tests.
- No T-0037, downstream task, real-project entry, user acceptance, or project PASS.
- No deletion or rewriting of historical evidence.

## Decision Required

Approval: `批准 G-HANDOFF-STRICT-SEMANTIC-CLASSIFICATION-REPAIR-V0-1`

Rejection: `拒绝 G-HANDOFF-STRICT-SEMANTIC-CLASSIFICATION-REPAIR-V0-1`

After approval, a later exact execution request remains required:

`执行已批准的 G-HANDOFF-STRICT-SEMANTIC-CLASSIFICATION-REPAIR-V0-1`
