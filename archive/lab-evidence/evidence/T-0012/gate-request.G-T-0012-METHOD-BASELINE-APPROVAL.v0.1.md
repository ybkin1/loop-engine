# Gate Request: G-T-0012-METHOD-BASELINE-APPROVAL v0.1

Status: pending user decision
Task: T-0012
Requested at: 2026-07-08T12:06:08+08:00

## Purpose

Ask the user whether to baseline-approve the repaired Loop engineering method candidate after T-0011 recommended `repaired -> baseline_candidate`.

This request is a decision package only. It is not approval.

## Basis

- T-0010 produced the repaired candidate method package.
- T-0011 completed review-rerun and baseline-readiness review.
- T-0011 result: `PASS_RECOMMENDED_FOR_BASELINE_CANDIDATE`.
- T-0011 found no unresolved P0 or P1.
- Major T-0009 P2 findings were accepted or explicitly deferred.
- Residual risks are non-blocking for baseline consideration but still relevant before installation or real-project application.

## Requested Lifecycle Transition

```text
baseline_candidate -> baseline_approved
```

Artifact:

```text
loop-engineering-method.repaired-candidate
```

## Allowed Scope If Approved

- Record the user's baseline approval decision in `.ai/gates.yaml`.
- Update `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/PROGRESS.md`, and `.ai/HANDOFF.md`.
- Add decision evidence under `.ai/evidence/T-0012/`.
- Run `validate_state.py`.

## Forbidden Scope

- Do not approve this gate without explicit user approval.
- Do not treat this pending request as approval.
- Do not install or enable the repaired method.
- Do not modify `AGENTS.md`.
- Do not create, enter, or modify a real business project.
- Do not write business project code.
- Do not build, implement, deploy, or roll back.
- Do not install or enable skill, MCP, agent, automation, protocol, or runtime behavior.
- Do not change databases, permissions, secrets, payment systems, production data, or migrations.
- Do not treat baseline approval, if later granted, as installation or real-project application.

## High-Risk Flags

| Flag | Value |
| --- | --- |
| deployment | false |
| rollback | false |
| database | false |
| permission | false |
| secret | false |
| payment | false |
| production_data | false |
| migration | false |
| runtime_behavior | false |

## Evidence Required

- `.ai/evidence/T-0012/commands.md`
- `.ai/evidence/T-0012/gate-request.G-T-0012-METHOD-BASELINE-APPROVAL.v0.1.md`
- `.ai/evidence/T-0012/user-decision-packet.baseline-approval.v0.1.md`

## Validation

While this gate remains pending, `validate_state.py` should block with:

```text
Pending gate(s) require user decision before continuing: G-T-0012-METHOD-BASELINE-APPROVAL
```

After the user explicitly approves or rejects the gate, validation must be rerun.

## User Decision Needed

Please choose one:

1. Approve `G-T-0012-METHOD-BASELINE-APPROVAL`.
2. Reject `G-T-0012-METHOD-BASELINE-APPROVAL`.
3. Request another repair path before baseline approval.

