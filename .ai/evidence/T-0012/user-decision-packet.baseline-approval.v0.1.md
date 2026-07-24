# User Decision Packet: Baseline Approval v0.1

Status: pending user decision
Task: T-0012
Gate: G-T-0012-METHOD-BASELINE-APPROVAL

## Summary

- T-0010 repaired the Loop engineering method candidate.
- T-0011 reran review and recommended the repaired candidate for baseline consideration.
- The recommendation is not approval.
- This packet asks whether the method may become a baseline reference for later work.
- Baseline approval would still not install, enable, or apply the method to a real project.
- Installation, `AGENTS.md` modification, runtime behavior change, and real-project application remain separately gated.

## What AI Assumed

| ID | Assumption | Source | Confidence | Owner | Impact If Wrong |
| --- | --- | --- | --- | --- | --- |
| A-001 | The user wants a baseline decision path, not immediate installation. | Current user request and T-0011 handoff | High | user | If wrong, this gate should be rejected or redirected. |
| A-002 | T-0011 evidence is sufficient for the user to decide baseline approval. | T-0011 baseline-readiness review | High | AI evidence, user decision | If wrong, request another repair or review task. |
| A-003 | Baseline approval means reference approval only. | Project contracts and T-0011 boundaries | High | governance/audit | If confused with installation, later sessions may overstep. |

## Decisions Needed

| DEC ID | Decision | Options | Recommendation | Tradeoff | Gate Impact |
| --- | --- | --- | --- | --- | --- |
| DEC-001 | Should the repaired method be baseline-approved? | Approve / Reject / Repair first | Approve only if you accept the residual risks and boundaries | Approval creates a baseline reference; rejection or repair keeps the method non-baseline | Resolves `G-T-0012-METHOD-BASELINE-APPROVAL` |

## Risks Or Conflicts

| Risk ID | Issue | Severity | Options | Recommended Handling |
| --- | --- | --- | --- | --- |
| RR-001 | Schema catalog may still need worked examples. | P2 | Accept for baseline / repair first | Accept for baseline only if examples can wait until before installation or real-project use. |
| RR-002 | No full method dry-run was executed in T-0011. | P2 | Accept for baseline / require dry-run before baseline | Accept for baseline only if dry-run remains required before installation or real-project use. |
| RR-003 | Future sessions could confuse baseline approval with installation. | P3 | Mitigate in records / reject | Mitigate by keeping explicit forbidden scope and separate later gates. |

## Proposed Gate

Gate ID:

```text
G-T-0012-METHOD-BASELINE-APPROVAL
```

Gate type:

```text
baseline-approval-only
```

Allowed scope:

```text
Record the user's baseline decision in .ai governance records only.
```

Forbidden scope:

```text
No AGENTS.md modification, installation, enablement, real-project entry, implementation, build, deployment, rollback, database, permission, secret, payment, production-data, migration, or runtime behavior change.
```

What approval does not authorize:

```text
Baseline approval does not authorize installation, active operating rules, AGENTS.md changes, real-project application, or production work.
```

## User Reply Format

You can reply in natural language, for example:

```text
批准 G-T-0012-METHOD-BASELINE-APPROVAL
```

or:

```text
拒绝 G-T-0012-METHOD-BASELINE-APPROVAL，原因是...
```

or:

```text
先不要批准，进入修复路径：...
```

