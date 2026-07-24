# User Decision Packet: Method Operating Rules / Installation Design v0.1

Status: pending user decision
Task: T-0013
Gate: G-T-0013-METHOD-OPERATING-RULES-DESIGN

## Summary

- T-0012 baseline-approved the repaired Loop engineering method as a reference only.
- The method is still not installed, enabled, active as operating rules, reflected in `AGENTS.md`, or applied to a real project.
- T-0013 designs how the method could later become explicit operating rules after a separate installation/rule-change gate.
- The design covers startup rules, session lifecycle rules, gate rules, subagent dispatch rules, validation rules, handoff rules, and real-project-entry separation.
- The `AGENTS.md` text in this package is a candidate draft only and has not been written to `AGENTS.md`.
- Approval of this T-0013 gate would accept the design package as candidate evidence only.
- A later separate gate would still be required before any installation, `AGENTS.md` modification, runtime behavior change, or real-project application.

## What AI Assumed

| ID | Assumption | Source | Confidence | Owner | Impact If Wrong |
| --- | --- | --- | --- | --- | --- |
| A-001 | The user wants an installation / operating-rules design package, not immediate installation. | Current user request | High | user | If wrong, reject this gate or request a different path. |
| A-002 | T-0012 baseline approval may be used as reference evidence for designing candidate rules. | T-0012 baseline approval record | High | governance/audit | If wrong, T-0013 should be repaired or superseded. |
| A-003 | The next useful step is to design future startup/session/gate/subagent/validation/handoff behavior before modifying `AGENTS.md`. | Current user request and T-0011/T-0012 boundaries | High | user + AI | If wrong, request a narrower or different gate. |
| A-004 | The design must keep the real goal centered: helping non-technical users get usable, deployable, acceptable, iterable software. | HANDOFF.md and ACCEPTANCE.md | High | user | If wrong, the method may drift back into governance for its own sake. |

## Decisions Needed

| DEC ID | Decision | Options | Recommendation | Tradeoff | Gate Impact |
| --- | --- | --- | --- | --- | --- |
| DEC-001 | Should T-0013 operating-rules design be accepted as a candidate package? | Approve / Reject / Repair first | Approve only if the boundaries and later-gate requirements are acceptable | Approval gives a clean design basis for a later installation gate; rejection or repair keeps the package non-accepted | Resolves `G-T-0013-METHOD-OPERATING-RULES-DESIGN` |
| DEC-002 | Should a later task prepare an installation/rule-change gate from this design? | Later installation design / More dry-run validation first / Stop here | More dry-run validation first if confidence in real delivery behavior is still low | Validation reduces risk but delays operating-rule installation | Does not happen under T-0013 without a later gate |

## Risks Or Conflicts

| Risk ID | Issue | Severity | Options | Recommended Handling |
| --- | --- | --- | --- | --- |
| RR-001 | Future sessions may read a candidate `AGENTS.md` draft as permission to modify the real file. | P1 | Repair wording / Reject / Accept with strict labels | Keep explicit "evidence only" labels and require a later installation gate. |
| RR-002 | The method may over-focus on governance instead of real software delivery. | P1 | Repair design / Accept with goal guardrail | Keep the startup rules centered on product delivery, not document production. |
| RR-003 | Subagent dispatch could be misread as permission to install or enable agent behavior. | P1 | Repair wording / Accept with strict separation | Treat subagent use as per-session tool use only, never installed automation. |
| RR-004 | No full real-project dry run has validated the operating rules. | P2 | Require dry run before installation / Accept design only | Defer installation until dry-run validation or a later user-approved risk decision. |

## Proposed Gate

Gate ID:

```text
G-T-0013-METHOD-OPERATING-RULES-DESIGN
```

Gate type:

```text
installation-operating-rules-design-only
```

Allowed scope:

```text
Accept, reject, or request repair of the T-0013 candidate operating-rules design package.
```

Forbidden scope:

```text
No AGENTS.md modification, installation, enablement, activation, runtime behavior change, real-project entry, business code, build, deployment, release, rollback, skill/MCP/agent/automation/protocol enablement, database, permission, secret, payment, production-data, or migration action.
```

What approval does not authorize:

```text
Approval does not authorize installation, active operating rules, runtime behavior changes, real-project application, or any production work.
```

## User Reply Format

Approve:

```text
批准 G-T-0013-METHOD-OPERATING-RULES-DESIGN
```

Reject:

```text
拒绝 G-T-0013-METHOD-OPERATING-RULES-DESIGN，原因是...
```

Repair first:

```text
先不要批准，修复 T-0013：...
```
