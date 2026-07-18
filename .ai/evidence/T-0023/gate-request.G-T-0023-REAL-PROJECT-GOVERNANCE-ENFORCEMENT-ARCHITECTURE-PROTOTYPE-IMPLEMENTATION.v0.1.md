# Gate Request: G-T-0023-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-PROTOTYPE-IMPLEMENTATION

## Gate ID

```text
G-T-0023-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-PROTOTYPE-IMPLEMENTATION
```

## Gate Type

```text
real-project-governance-enforcement-architecture-prototype-implementation
```

## Status

```text
pending
```

## Purpose

Allow the user to decide whether Codex may implement a lab-local prototype of
the T-0019 real project governance enforcement architecture, using the T-0022
planning package as input.

## Source Facts

- T-0019 produced the candidate enforcement architecture.
- T-0020 completed with `PASS_FOR_BASELINE_CONSIDERATION`.
- T-0021 recorded T-0019 as a baseline reference/candidate for later
  implementation planning only.
- T-0022 produced implementation-planning evidence only.
- T-0022 recommends a later separate T-0023 prototype implementation gate.

## Allowed Before Explicit User Decision

- Create `.ai/tasks/T-0023.md`.
- Create `.ai/evidence/T-0023/`.
- Create T-0023 startup validation evidence.
- Create this T-0023 gate request evidence.
- Create T-0023 user decision packet.
- Record this gate as `pending`.
- Update `.ai/state.yaml`, `.ai/task_graph.yaml`, `.ai/gates.yaml`,
  `.ai/PROGRESS.md`, and `.ai/HANDOFF.md`.
- Run `validate_state.py` after gate registration and expect a pending gate
  blocker for T-0023.
- Stop and ask the user to approve, reject, or request repair.

## Potential Scope After Explicit Approval Only

- Create lab-local prototype schema files.
- Create lab-local checker catalog and validator scripts.
- Create lab-local policy guard simulation files.
- Create sample test fixtures.
- Run prototype validation against governance-lab samples only.
- Write evidence under `.ai/evidence/T-0023/`.

## Candidate Future Write Targets After Approval Only

- `.ai/schemas/gate-register.schema.yaml`
- `.ai/schemas/checker-result.schema.yaml`
- `.ai/checkers/catalog.yaml`
- `.ai/checkers/validate_gate_register.py`
- `.ai/checkers/run_governance_checks.py`
- `.ai/policies/tool-entry-restrictions.yaml`
- `.ai/guards/policy_guard.py`
- `.ai/guards/guard_decision.schema.yaml`
- `.ai/tests/samples/`
- `.ai/tests/test_governance_checks.py`
- `.ai/evidence/T-0023/`

## Forbidden Scope

- Do not treat this prompt as approval.
- Do not implement while this gate is pending.
- Do not modify `AGENTS.md`.
- Do not write outside lab-local approved target paths.
- Do not install or enable MCP, skill, policy guard, wrapper, automation,
  protocol, runtime, hook, plugin, or tool behavior.
- Do not enter, create, or modify a real business project.
- Do not write business code.
- Do not build, deploy, release, or roll back.
- Do not change databases, permissions, secrets, payment systems, production
  data, or migrations.
- Do not treat T-0022 planning evidence, validator success, tests, AI
  recommendation, or this prompt as user approval.

## Required User Decision

The user must explicitly approve, reject, or request repair.

Exact approval phrase:

```text
批准 G-T-0023-REAL-PROJECT-GOVERNANCE-ENFORCEMENT-ARCHITECTURE-PROTOTYPE-IMPLEMENTATION
```
