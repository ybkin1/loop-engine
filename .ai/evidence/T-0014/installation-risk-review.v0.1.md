# Installation Risk Review v0.1

Task: T-0014
Gate: G-T-0014-METHOD-OPERATING-RULES-INSTALLATION

## Review Scope

This review covers the prepared installation / rule-change package only. T-0014 does not apply the package.

## Risk Register

| ID | Risk | Severity | Status | Mitigation |
| --- | --- | --- | --- | --- |
| IR-001 | `AGENTS.md` proposed diff may be mistaken for an applied change. | P1 | Open until user decision | Store diff only under evidence and state repeatedly that `AGENTS.md` is unchanged. |
| IR-002 | Approval may be misread as broad runtime/tool enablement. | P1 | Mitigated in packet | Exact target list is `AGENTS.md` only; skills, MCPs, agents, automations, protocols, and tools are excluded. |
| IR-003 | Future patch may be stale if `AGENTS.md` changes before execution. | P1 | Mitigated by validation plan | Future execution must compare fresh hash with T-0014 baseline and stop on mismatch. |
| IR-004 | Startup behavior may over-load governance for simple requests. | P2 | Mitigated in proposed diff | Proposed rules exempt simple Q&A, single-file explanation, and temporary read-only commands unless governance is requested. |
| IR-005 | Future installation changes startup behavior. | P1 | Requires explicit user decision | Runtime behavior is false for T-0014 preparation and true only for a later approved execution task. |

## Forbidden Scope Review

T-0014 does not authorize or perform:

```text
AGENTS.md modification
proposed diff application
skill/MCP/agent/automation/protocol/tool enablement
real business project entry
business code
implementation
build
deployment
release
rollback
database change
permission change
secret handling
payment action
production-data action
migration
```

## Result

No installation or runtime behavior change has occurred in T-0014. The package is ready for user decision only if `AGENTS.md` remains unchanged and final validation blocks on the pending gate.
