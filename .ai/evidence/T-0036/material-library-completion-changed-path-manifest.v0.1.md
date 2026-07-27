# T-0036 素材库候选交付包执行 Changed-Path Manifest v0.1

## Execution scope

本 manifest 只记录 `G-T-0036-COMPLETE-MATERIAL-LIBRARY-REVIEW-PACKET-V0-1` 的实际执行范围。项目在执行前已有其他未提交变更；本文件不把既有 dirty baseline 归因于本次执行。

## Paths created by this execution

- `materials/material-library-review-packet.md`
- `materials/coverage-duplication-review.md`
- `.ai/evidence/T-0036/material-library-completion-validation.v0.1.md`
- `.ai/evidence/T-0036/material-library-completion-changed-path-manifest.v0.1.md`

### Created file fingerprints

- path: materials/material-library-review-packet.md
  size: 7483
  sha256: 0ABBE5FE66A1C587D9DAC19C0A437A2C94EB60CA3B34FF8860FA924869F606ED
- path: materials/coverage-duplication-review.md
  size: 4231
  sha256: 634FE5CBA4AEF01CA48E3A2B8B9253BE8C7F23E3CD23D0531BCC91AB36204B0B
- path: .ai/evidence/T-0036/material-library-completion-validation.v0.1.md
  size: 3274
  sha256: 2EE186860313C3FAC77C37182D868A0D70DBDF45775B34B316C7AF3A909C4115

## Governance paths updated by this execution

- `.ai/evidence/T-0036/commands.md`
- `.ai/tasks/T-0036.md`
- `.ai/state.yaml`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/HANDOFF.md`

这些文件只记录本 Gate 的执行请求、完成证据、状态投影和后续独立评审边界。

## Protected paths checked

- `materials/catalog.yaml` 未修改。
- `materials/material-schema.yaml` 未修改。
- `materials/source-register.md` 未修改。
- `materials/coverage-matrix.md` 未修改。
- `materials/templates/`、`materials/frameworks/`、`materials/profiles/` 未修改。
- `.ai/evidence/T-0036/source-validation.v0.1.md`、`coverage-matrix.v0.1.md` 和 `simulation/` 未修改。
- `codex_loop/`、`tests/codex_loop/`、`docs/codex-loop/` 和 `.ai/evidence/T-0037/` 未修改。
- 全局 Codex 配置、`AGENTS.md`、skill、MCP、plugin、automation、hook、生产数据和外部业务项目未触碰。

当前结论：`scope-contained / protected-inputs-preserved / next-step-independent-review-gate-required`
