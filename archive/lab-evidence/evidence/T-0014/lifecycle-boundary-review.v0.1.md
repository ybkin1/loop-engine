# Lifecycle / Boundary Review v0.1

Task: T-0014

## Lifecycle State Separation

| Item | State | Meaning | Not Authorized |
| --- | --- | --- | --- |
| T-0012 repaired method baseline | `baseline_approved_reference_only` | The method may be cited as reference evidence. | Installation, activation, runtime behavior, real-project application. |
| T-0013 operating-rules design | `operating_rules_design_candidate_accepted` | The design package may be used as candidate evidence. | `AGENTS.md` modification or active operating rules. |
| T-0014 installation package | `pending user decision` | Exact package is prepared for user approval, rejection, or repair. | Applying the diff during T-0014. |
| Future T-0015/new phase | not started | Could execute only after explicit user approval and fresh validation. | Any action outside exact approved scope. |

## Approval Boundary

Only the user may approve:

```text
G-T-0014-METHOD-OPERATING-RULES-INSTALLATION
```

These are evidence only and cannot approve the gate:

```text
reviewer PASS
validator success
tests
AI recommendation
subagent review
T-0012 baseline approval
T-0013 design approval
```

## Installation Boundary

During T-0014:

```text
installed=false
active operating rules for repaired method=false
runtime behavior changed=false
AGENTS.md modified=false
```

Future installation target:

```text
AGENTS.md
```

Future target does not include:

```text
skills
MCP servers
agents
automations
protocols
tools
real business projects
production resources
```

## Result

The T-0014 package preserves the distinction between reference, candidate design, pending installation decision, future installation execution, runtime behavior, and real-project application.
