# User Decision Packet: Method Operating Rules Installation v0.1

Status: pending user decision
Task: T-0014
Gate: G-T-0014-METHOD-OPERATING-RULES-INSTALLATION

## Summary

- T-0012 baseline-approved the repaired Loop engineering method as reference only.
- T-0013 accepted the operating-rules design package as candidate evidence only.
- The repaired Loop engineering method is still not installed or enabled.
- `AGENTS.md` has not been changed for the repaired method.
- T-0014 prepares the exact installation / rule-change package and stops at a pending gate.
- The proposed `AGENTS.md` change is stored only as `.ai/evidence/T-0014/agents-md.proposed-diff.v0.1.patch`.

## Decision Options

| Option | User Meaning | Result |
| --- | --- | --- |
| Approve | Accept the exact T-0014 package as the basis for a later separate execution task. | T-0015 or a new phase should record the approval and rerun validation before any write. |
| Reject | Do not use this package. | The repaired method remains uninstalled and not enabled. |
| Repair | Request specific changes to the package. | A repair task or revised evidence should be created before any approval. |

## Exact Future Target File List

Future target:

```text
AGENTS.md
```

No other target is part of this package.

## Package Contents To Decide On

| Artifact | Purpose | Applies Now? |
| --- | --- | --- |
| `agents-md.proposed-diff.v0.1.patch` | Exact proposed unified diff for `AGENTS.md`. | No |
| `changed-path-baseline.v0.1.md` | Baseline of target and governance files before T-0014 writes. | Evidence only |
| `rollback-recovery-plan.v0.1.md` | Recovery plan for T-0014 and future installation execution. | Evidence only |
| `validation-plan.v0.1.md` | Pre/post validation and evidence plan. | Evidence only |
| `installation-risk-review.v0.1.md` | Risk review and forbidden-scope check. | Evidence only |
| `lifecycle-boundary-review.v0.1.md` | Lifecycle, approval, activation, installation, and real-project separation. | Evidence only |
| `startup-behavior-verification-plan.v0.1.md` | How a future execution task should verify startup behavior. | Evidence only |
| `failure-recovery-steps.v0.1.md` | How to stop and recover if future execution fails. | Evidence only |

## Key Risks

| Risk | Severity | Handling |
| --- | --- | --- |
| The package could be misread as already installed. | P1 | Every T-0014 artifact states that the diff is evidence only and `AGENTS.md` is unchanged. |
| Approval could be misread as permission for broad runtime changes. | P1 | Target path is exactly `AGENTS.md`. The proposed text would add project-local operating rules, including evidence-only subagent dispatch guidance, but it would not install or enable any external skill, MCP, agent runtime, automation, protocol service, tool behavior, or real project. |
| A later execution could apply a stale diff after `AGENTS.md` changes. | P1 | T-0015/new phase must re-check the target hash and stop if it differs from the baseline. |
| Startup behavior could become too governance-heavy. | P2 | Proposed rules preserve simple Q&A and temporary read-only command exceptions. |

## Recommendation

Approve only if the user accepts:

- exact target path: `AGENTS.md`
- exact proposed diff path: `.ai/evidence/T-0014/agents-md.proposed-diff.v0.1.patch`
- actual write, if any, should be handled by T-0015 or a new phase with fresh validation
- the future write would be a project-local `AGENTS.md` startup / operating-rule change only
- no real-project entry, external agent runtime, skill, MCP, automation, protocol service, or tool enablement is included

## Reply Formats

Approve:

```text
APPROVE G-T-0014-METHOD-OPERATING-RULES-INSTALLATION
```

Reject:

```text
REJECT G-T-0014-METHOD-OPERATING-RULES-INSTALLATION because ...
```

Request repair:

```text
REPAIR T-0014 before approval: ...
```

## Explicit Boundary

This packet does not approve the gate. It does not modify `AGENTS.md`, install or enable the repaired method, change runtime behavior now, enable tools or external agent runtimes, or authorize real-project application. If later executed under a separate approval, the change would be limited to project-local `AGENTS.md` startup / operating-rule text.
