# Next Gate Recommendation v0.1

Status: evidence
Task: T-0011

## Recommendation

Because T-0011 passes review-rerun, recommend a later separate baseline approval gate.

Recommended gate name:

```text
G-T-0012-METHOD-BASELINE-APPROVAL
```

Recommended type:

```text
baseline-approval-only
```

This gate is recommended only. It is not created, approved, or executed by T-0011.

## Proposed Purpose

Ask the user whether to approve the repaired Loop engineering method package as a baseline reference after reviewing T-0011 evidence and residual risks.

## Proposed Allowed Scope

- read T-0008, T-0009, T-0010, and T-0011 evidence
- decide whether to baseline-approve, reject, or request another repair
- update `.ai` governance records only if explicitly approved
- run `validate_state.py`

## Proposed Forbidden Scope

- do not install or enable the method
- do not modify `AGENTS.md`
- do not enter or modify a real business project
- do not implement, build, deploy, roll back, migrate, change permissions, handle secrets, process payments, or touch production data
- do not treat baseline approval as installation or real-project application

## Not Recommended Next

Do not recommend installation, `AGENTS.md` modification, or real-project application as the next gate.
