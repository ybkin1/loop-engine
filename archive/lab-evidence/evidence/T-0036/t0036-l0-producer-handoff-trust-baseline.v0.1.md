# T-0036 L0 Producer Handoff Trust Baseline v0.1

Generated: `2026-07-20T00:10:58+08:00`.

## Controlling User Statements

### Root goal

> 帮助一个无代码能力、无项目管理背景的用户，使用 Codex 产出真实可用、可部署、可验收、可持续迭代的软件产品。

### Means/ends boundary

> Loop 工程规范、`.ai`、Gate、HANDOFF、`AGENTS.md`、review、evidence 都是为了让 Codex 可靠承担软件交付职责，而不是为了把治理系统做成一个自我循环的项目。

### Reliability correction

The user rejected recent controller framing and routing as unreliable and explicitly requested that the handoff be redone correctly.

## Reliability Matrix

| Class | Statement | Verification/authority |
|---|---|---|
| `USER_AUTHORED` | Root goal and means/ends boundary above | Latest user messages, preserved verbatim |
| `USER_AUTHORED` | Recent HANDOFF/controller interpretation is not trusted | Explicit user rejection |
| `DISK_VERIFIED` | `state.current_task_id: T-0036` | `.ai/state.yaml` |
| `DISK_VERIFIED` | T-0036 task and task graph are `completed` | `.ai/tasks/T-0036.md`, `.ai/task_graph.yaml` |
| `DISK_VERIFIED` | `state.current_gate_id: null`; pending Gate count is 0 | `.ai/state.yaml`, `.ai/gates.yaml` |
| `DISK_VERIFIED` | T-0037 task/evidence/Gate do not exist | exact path and Gate searches |
| `DISK_VERIFIED` | Four T-0036 core review evidence files retain historical manifest hashes | SHA-256 comparison below |
| `INDEPENDENT_EVIDENCE` | T-0036 review verdict is `REPAIR_REQUIRED`, 7 P1 and 2 P2 | fresh read-only review report/findings |
| `INDEPENDENT_EVIDENCE` | At review time: 28 tests passed, frozen subjects matched, candidate was not installed/activated | review report/validation; evidence only |
| `AI_DERIVED` | T-0037 should be repair architecture/design | predecessor recommendation, not approved and not trusted |
| `AI_DERIVED` | A specific repair architecture for F001-F009 | not yet established or user-approved |
| `REJECTED_OR_UNTRUSTED` | Governance repair, Project Governor, or a “delivery mechanism” is the root goal/final product | rejected by user; contradicts root goal |
| `REJECTED_OR_UNTRUSTED` | Prior controller HANDOFF summaries and prompts from this conversation | user rejection and self-reference risk |

## Preserved Independent-evidence Hashes

| Path | Current SHA-256 | Historical match |
|---|---|---|
| `.ai/evidence/T-0036/t0036-independent-review-report.v0.1.md` | `6D12AAEE64015B60051C912FA9CD53F1611E2432EF93073BD72E654E5FB1F36C` | yes |
| `.ai/evidence/T-0036/t0036-review-findings.v0.1.md` | `FDFF5BD279F341A743E1CCCF279A8D6755DC9A228372169EE451BF6492573DDE` | yes |
| `.ai/evidence/T-0036/t0036-review-validation.v0.1.md` | `B65D22A3C88538D8BB31348B113B28071B5585FD1DA06D844735078BEB5791D6` | yes |
| `.ai/evidence/T-0036/t0036-review-changed-path-manifest.v0.1.md` | `CE8BF10C02D75BCAF914130A7D7CCDA23BD6F65BF76F93D422983FAE0C29F3DE` | historical manifest self-hash retained from supplement evidence |

## Checkpoint Classification

- Last defensible **evidence checkpoint**: T-0036 independent review completion at `2026-07-18T23:55:52.5241301+08:00`, limited to its preserved report/findings/validation and their stated boundaries.
- Last defensible **operational Stable Checkpoint**: `UNKNOWN`. T0036-F007 specifically shows that the candidate could assert stability without proving it.
- Current candidate equivalence to all 60 frozen subjects: not recomputed in this producer turn.
- Current governance projections after the review: changed multiple times; do not use old projection manifests as current-state proof.

## Producer/Successor Boundary

- This file is producer evidence, not successor attestation.
- A fresh L0 must independently rerun startup checks, recompute the stated current facts, and return `RecoveredControllerState` plus a field-by-field comparison.
- A prose summary without the required reliability table and comparison is not a completed successor probe.
- No task/Gate creation, repair, installation, activation, or real-project action is authorized by this baseline.
