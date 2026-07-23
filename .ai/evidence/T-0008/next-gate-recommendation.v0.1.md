# Next Gate Recommendation v0.1

Status: candidate design
Task: T-0008

## Recommendation

Do not install or enable this repaired method yet.

The recommended next step is a review-only task:

```text
T-0009: Loop Method Candidate Review And Repair
G-T-0009-METHOD-CANDIDATE-REVIEW
```

## Proposed T-0009 Scope

Allowed:

- review T-0008 evidence documents
- run a role-based critique of the candidate method
- identify contradictions, missing artifacts, and unsafe gate logic
- compare the method against the Harness design-depth benchmark
- produce repair recommendations
- update T-0009 evidence, progress, handoff, gates, and task graph
- run `validate_state.py`

Forbidden:

- do not install or modify `AGENTS.md`
- do not enable skill/MCP/agent/automation/protocol behavior
- do not change global or project runtime behavior
- do not enter a real business project
- do not create a real product project
- do not build, implement, deploy, roll back, migrate, change permissions, handle secrets, touch payment, or touch production data

## Possible Later Gates

Only after T-0009 review and repair, the user may choose one of these later paths:

| Gate | Purpose | Still Candidate? |
| --- | --- | --- |
| `G-T-0010-METHOD-FORMALIZE-CANDIDATE` | consolidate repaired method into a formal candidate spec | yes |
| `G-T-0011-AGENTS-MD-UPDATE-CANDIDATE` | design a proposed `AGENTS.md` update without applying it | yes |
| `G-T-0012-INSTALL-METHOD-RULES` | actually update installed project rules | no, requires explicit installation gate |
| `G-T-0013-REAL-PROJECT-APPLICATION-DESIGN` | design how to apply the method to a named real project | yes |

## Baseline Approval Criteria

Before any installation or rule update, the method should pass:

- no unresolved P0/P1 review findings
- artifact matrix covers idea-to-release lifecycle
- user responsibilities are narrow and realistic
- AI responsibilities are explicit
- gate protocol prevents implicit approvals
- handoff protocol prevents context pollution
- real-project entry remains separately gated
- installation and runtime behavior changes remain separately gated

## Current Recommendation To User

Approve only a review/repair gate next. Do not approve installation or real-project application yet.
