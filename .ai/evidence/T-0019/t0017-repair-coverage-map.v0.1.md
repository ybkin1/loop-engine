# T-0017 Repair Coverage Map v0.1

Status: evidence
Task: T-0019

## Purpose

Map T-0018 findings and T-0017 known gaps to T-0019 candidate repair coverage.

## Coverage

| Source | Issue | T-0019 Coverage |
| --- | --- | --- |
| `FIND-T0018-P1-001` | T-0017 controls are Markdown-only and lack concrete enforcement architecture. | `enforcement-architecture`, `machine-readable-gate-register-schema`, `policy-guard-and-wrapper-design`, `tool-entry-restriction-model`. |
| `FIND-T0018-P2-002` | Contract/checker mapping is descriptive, not executable. | `checker-catalog-and-blocking-semantics`, `machine-readable-gate-register-schema`. |
| `RR-T0018-001` | T-0017 relies on assistant self-discipline. | Enforcement layer split into L0 self-discipline, L1 scripts, L2 wrappers, L3 tool-entry enforcement. |
| `RR-T0018-003` | Contract/checker mapping is not wired to scripts or guards. | Defines checker result shape, gate binding, direct/indirect/advisory blocking, and future validator consumption. |
| T-0017 Known Gap | Markdown rules are not machine-enforced validation. | Gate register with pending-is-blocking and evidence lock. |
| T-0017 Gate Protocol | Gate records exist but do not drive blocking beyond current pending gate validation. | Required gate fields and gate receipt schema. |
| T-0017 Traceability Schema | Traceability completeness checks are listed but not executable. | Traceability closure checker and artifact schema checker. |
| T-0017 Implementation Readiness | Build gate fields exist but no tool-entry guard consumes them. | Tool-entry authorization checker and sensitive action classes. |
| T-0017 Risk Rules | High-risk actions require separate gates but enforcement is manual. | Tool entry restriction model with deny-by-default sensitive classes. |
| T-0017 Handoff Protocol | Handoff must not become authority but no stale-handoff checker exists. | Stale handoff checker and closeout audit design. |
| T-0017 Exception Register | Exceptions are documented but not connected to checker availability. | Unavailable checker semantics and exception validation rules. |

## Residual Gaps After T-0019

| Gap | Why It Remains | Recommended Handling |
| --- | --- | --- |
| No implementation exists. | T-0019 is design-only. | Separate implementation gate after review. |
| No real-project dry run exists. | T-0019 does not enter a real project. | Later dry-run/example gate after enforcement review. |
| No tool-entry hook is enabled. | Runtime/tool behavior enablement is forbidden in T-0019. | Later tool enablement gate if implementation is approved. |
| No AGENTS.md change occurs. | T-0019 forbids rule installation. | Later installation/rule-change gate if needed. |

## Verdict

T-0019 candidate design directly covers the T-0018 P1 enforcement architecture
gap at design level. It does not close the gap at implementation or runtime
level.
