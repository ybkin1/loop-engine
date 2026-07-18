# Handoff Context Hygiene Checklist v0.1

Status: candidate repair evidence
Task: T-0010

## Purpose

Prevent stale chat context, test-case details, and unrelated project facts from contaminating the current mainline.

## Required Handoff Fields

`HANDOFF.md` should include only:

- current phase
- current task
- task status
- allowed scope
- forbidden scope
- recent changes
- verified items
- unverified items
- evidence location
- integration impact
- quarantined test cases and stale context warnings
- pending gates and blockers
- next session first step
- copyable startup prompt

## Contamination Checks

Before closing or resuming a session, check:

| Check | Pass Condition |
| --- | --- |
| Latest user request read | Work matches newest user request. |
| Mainline identified | Current phase and task are explicit. |
| Test cases quarantined | T-0007 or other samples are marked as non-mainline unless reopened. |
| Candidate/baseline/installed separated | No candidate is described as active or installed. |
| Pending gates visible | Pending gates are named and require user decision. |
| Forbidden scope preserved | No high-risk action is implied by handoff. |
| Evidence path clear | Next session can find source files. |
| Next step concrete | Startup command and first decision are copyable. |

## Quarantined Context Rule

Concrete product samples used to test a method must be labeled:

```text
quarantined_test_case: true
mainline: false
resume_only_if_user_explicitly_reopens: true
```

For this project, T-0007 remains quarantined as a discovery-method stress test.

## Handoff Anti-Patterns

Avoid:

- carrying a product sample forward as the current project
- saying a candidate method is active after a repair
- treating validation as user approval
- hiding unverified items
- burying next gates in long prose
- omitting forbidden high-risk actions

## Resume Checklist

At the next session start:

1. Read the latest user request.
2. Confirm project root.
3. Read `.ai/state.yaml`, `.ai/HANDOFF.md`, current task file, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
4. Run `validate_state.py`.
5. Stop on pending gates unless the user has explicitly approved or rejected them.
6. Continue only inside the approved task and gate scope.

## Candidate Boundary

This checklist is candidate evidence only. It does not modify installed startup rules or `AGENTS.md`.
