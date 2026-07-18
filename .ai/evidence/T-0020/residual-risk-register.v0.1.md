# Residual Risk Register v0.1

Status: evidence
Task: T-0020

## Finding Counts

| Severity | Count |
| --- | ---: |
| P0 | 0 |
| P1 | 0 |
| P2 | 2 |
| P3 | 1 |

## Register

| ID | Severity | Risk | Handling | Blocks Baseline Consideration |
| --- | --- | --- | --- | --- |
| `FIND-T0020-P2-001` | P2 | Gate register schema is stronger at denying forbidden scope than positively proving allowed actions/tools. | Before implementation, add explicit `allowed_actions`, `allowed_action_classes`, `allowed_tools`, or a strict reference to the approving gate fields. | no |
| `FIND-T0020-P2-002` | P2 | Audit design does not yet specify a deterministic tamper-evidence mechanism for evidence locks. | Before implementation or installation, define hash manifests, append-only receipts, immutable snapshots, signed summaries, or equivalent. | no |
| `FIND-T0020-P3-001` | P3 | Guard decision enum and decision rules use one inconsistent value: `allow_gate_recording_only`. | Normalize the enum before implementation. | no |

## Continuing Known Risks

| ID | Severity | Risk | Handling |
| --- | --- | --- | --- |
| `RR-T0020-001` | P2 | No implementation exists. | Separate implementation-preparation and implementation gate required. |
| `RR-T0020-002` | P2 | No real-project dry run exists. | Later dry-run/example gate before real-project entry. |
| `RR-T0020-003` | P2 | No tool-entry hook, MCP, wrapper, skill, automation, protocol, runtime, or tool behavior is enabled. | Later runtime/tool enablement gate required if desired. |

## Non-Authorization

These residual risks do not authorize implementation, installation,
real-project entry, `AGENTS.md` modification, runtime/tool enablement,
deployment, rollback, database, permission, secret, payment, production-data,
or migration action.
