# Next Gate Recommendation v0.1

Status: evidence
Task: T-0009

## Recommendation

Open a repair-only gate next. Do not install or enable the T-0008 method yet.

Recommended gate:

```text
G-T-0010-METHOD-CANDIDATE-REPAIR
```

Recommended type:

```text
repair-only / candidate-update-only
```

## Proposed T-0010 Purpose

Repair the T-0008 candidate method based on T-0009 findings. The repair should update or add candidate method evidence only. It should not install the method, modify `AGENTS.md`, enter a real project, or change runtime behavior.

## Proposed Allowed Actions

- create `.ai/tasks/T-0010.md`
- create `.ai/evidence/T-0010/`
- read `.ai/evidence/T-0008/` and `.ai/evidence/T-0009/`
- update or add method candidate evidence under `.ai/evidence/T-0010/`
- optionally supersede T-0008 candidate documents by reference, not by installing them
- update `.ai/state.yaml`
- update `.ai/task_graph.yaml`
- update `.ai/gates.yaml`
- update `.ai/PROGRESS.md`
- update `.ai/HANDOFF.md`
- run `validate_state.py`

## Proposed Forbidden Actions

- do not continue T-0007 product sample
- do not modify Harness artifacts
- do not create a real product project
- do not enter a real business project root
- do not create or modify real business project files
- do not write business project code
- do not build, implement, deploy, or roll back
- do not modify `AGENTS.md`
- do not install or enable skill, MCP, agent, automation, or protocol behavior
- do not change global or project runtime behavior
- do not change database, permission, secret, payment, production data, or migration resources
- do not treat reviewer PASS, validator success, tests, or AI recommendations as user approval
- do not treat candidate repair as baseline approval

## Later Gates Still Required

After repair, later separate gates may be considered:

- baseline review rerun
- baseline approval
- `AGENTS.md` update candidate design
- installation or rule-change gate
- real-project application design gate

Each later gate must be explicit and separately approved by the user.
