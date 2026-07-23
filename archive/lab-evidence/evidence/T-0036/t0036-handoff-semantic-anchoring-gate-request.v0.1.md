# T-0036 HANDOFF Semantic Anchoring Gate Request v0.1

Gate: `G-T-0036-REPAIR-HANDOFF-SEMANTIC-ANCHORING-V0-1`

This is a registration-only request. It does not modify the global Project Governor and does not execute the repair.

## Objective

Repair only the HANDOFF generation/audit mechanism so generated HANDOFF files preserve the authoritative project-level semantic anchors and distinguish them from current task scope and execution constraints.

## Authoritative Anchors

- `.ai/PROJECT.md:5`: project starting point and final outcome.
- `.ai/PROJECT.md:9`: user/Codex responsibility boundary.
- `.ai/PROJECT.md:22` and `AGENTS.md:24`: governance is a means/guardrail, not the product.

## Exact Future Targets

- `C:/Users/Administrator/.codex/skills/project-governor/scripts/close_session.py`
- `C:/Users/Administrator/.codex/skills/project-governor/scripts/audit_handoff.py`
- `C:/Users/Administrator/.codex/skills/project-governor/scripts/test_handoff_semantic_anchoring.py` (new isolated test)

No candidate, project `.ai` source, `AGENTS.md`, runtime, installation, activation, or production file is in scope for future execution.

## Required Future Behavior

- `close_session.py` reads the authoritative anchors from the project root and emits separate sections for project anchors, current topic, current problem, current state, and current execution constraints.
- `audit_handoff.py` compares the generated anchor fields to the authoritative source and fails closed on missing, swapped, paraphrased, or misclassified anchors.
- Repeated closeout generation is deterministic for semantic content and cannot reintroduce the former classification error.
- Existing task/Gate/state/evidence behavior, pending-gate blocking, transaction safety, and validator behavior remain unchanged.

## Required Tests

- Correct anchors are emitted from `PROJECT.md`/`AGENTS.md`.
- A HANDOFF that puts Gate constraints under project stance is rejected.
- A HANDOFF that replaces the project outcome with the current T-0036 topic is rejected.
- Two closeout runs preserve the same semantic anchor payload.
- Existing validator, audit structure checks, pending-gate behavior, and transaction recovery regressions remain passing.

## Explicit Non-Goals

- No change to Gate authority semantics.
- No change to candidate validation, `UnittestResultEnvelope/v1`, installation, activation, runtime/tool enablement, T-0037, or real-project entry.
- No automatic user acceptance or project PASS.

## Decision Phrases

Approval: `批准 G-T-0036-REPAIR-HANDOFF-SEMANTIC-ANCHORING-V0-1`

Rejection: `拒绝 G-T-0036-REPAIR-HANDOFF-SEMANTIC-ANCHORING-V0-1`

Later exact execution request: `执行已批准的 G-T-0036-REPAIR-HANDOFF-SEMANTIC-ANCHORING-V0-1`
