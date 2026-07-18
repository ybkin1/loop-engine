# T-0008 Commands And Validation Evidence

Status: evidence
Task: T-0008
Recorded at: 2026-07-07T18:17:41+08:00
Scope: Loop engineering method repair candidate design only

## User Gate

The user explicitly approved:

```text
必要时只读参考 Harness artifacts 目录作为目标设计深度标尺；不得修改该目录或任何真实业务项目文件。

T-0008 只产出 Loop 工程方法修复候选设计，不安装、不启用、不修改 AGENTS.md、不改变全局或项目运行行为。任何安装/启用/规则变更都需要后续单独 gate。
批准 G-T-0008-METHOD-REPAIR-DESIGN
```

Allowed updates:

- `.ai/tasks/T-0008.md`
- `.ai/evidence/T-0008/`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/PROGRESS.md`
- `.ai/HANDOFF.md`

Allowed read-only reference:

- `C:\Users\Administrator\Documents\trae_projects\yb\harness\.codex\tasks\tk-20260614-001-agentic-backend-orchestration-design\artifacts`

Forbidden scope:

- do not create a real product project
- do not enter a real business project root
- do not write real business project code
- do not build, implement, deploy, or roll back
- do not modify `AGENTS.md`
- do not install or enable skill/MCP/agent/automation/protocol behavior
- do not change global or project runtime behavior
- do not change database, permission, secret, payment, production data, or migration resources
- do not treat reviewer PASS, validator success, tests, or AI recommendations as user approval

## Startup Validation

```text
[project-governor] phase: S0-discovery
[project-governor] current_task_id: T-0007
[ok] state is usable
```

## Read-Only Reference Checks

Commands run against the Harness artifacts directory were read-only.

Observed benchmark:

- 48 files under the artifacts directory.
- Top line-count examples:
  - `api-contract-specification.md`: 3165 lines
  - `frontend-ux-specification.md`: 3148 lines
  - `design-supplements/design-o-mcp-integration-architecture.md`: 2030 lines
  - `design-supplements/design-v-field-service-dispatch-execution.md`: 1546 lines
  - `design-supplements/design-t-email-intake-deep-link.md`: 1526 lines
  - `design-supplements/design-r-end-to-end-functional-specification.md`: 1381 lines

## Completed Updates

- Created `.ai/tasks/T-0008.md`.
- Created `.ai/evidence/T-0008/commands.md`.
- Created `.ai/evidence/T-0008/reference-depth-benchmark.v0.1.md`.
- Created `.ai/evidence/T-0008/loop-engine-method-diagnosis.v0.1.md`.
- Created `.ai/evidence/T-0008/one-person-ai-team-premise.v0.1.md`.
- Created `.ai/evidence/T-0008/lifecycle-stage-map.v0.1.md`.
- Created `.ai/evidence/T-0008/stage-artifact-matrix.v0.1.md`.
- Created `.ai/evidence/T-0008/ai-role-review-loop.v0.1.md`.
- Created `.ai/evidence/T-0008/design-document-generation-loop.v0.1.md`.
- Created `.ai/evidence/T-0008/gate-and-handoff-protocol.v0.1.md`.
- Created `.ai/evidence/T-0008/next-gate-recommendation.v0.1.md`.
- Updated `.ai/state.yaml` to `current_task_id: T-0008`.
- Added T-0008 to `.ai/task_graph.yaml`.
- Recorded `G-T-0008-METHOD-REPAIR-DESIGN` in `.ai/gates.yaml`.
- Updated `.ai/PROGRESS.md`.
- Updated `.ai/HANDOFF.md`.

## Boundary Checks

- Harness artifacts modified: no.
- Real business project entered: no.
- Real business project files modified: no.
- Product project created: no.
- Business project code written: no.
- `AGENTS.md` modified: no.
- skill/MCP/agent/automation/protocol behavior enabled: no.
- global or project runtime behavior changed: no.
- build/implementation/deploy/rollback performed: no.
- database/permission/secret/payment/production-data/migration action performed: no.

## Post-T-0008 Validation

```text
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0008
[ok] state is usable
```

## Post-T-0008 File Checks

```text
T-0008 evidence files:
- ai-role-review-loop.v0.1.md
- commands.md
- design-document-generation-loop.v0.1.md
- gate-and-handoff-protocol.v0.1.md
- lifecycle-stage-map.v0.1.md
- loop-engine-method-diagnosis.v0.1.md
- next-gate-recommendation.v0.1.md
- one-person-ai-team-premise.v0.1.md
- reference-depth-benchmark.v0.1.md
- stage-artifact-matrix.v0.1.md
```
