# T-0105 批 1：文档漂移修复证据（batch1-doc.md）

> 日期：2026-08-03 ｜ 执行者：developer 子代理

## A-1 finding 状态同步

**改动**：两个 finding 状态字段 `OPEN（待用户裁决…）` → `CLOSED`，并追加"关闭记录"行（其余内容原样保留）。

| 文件 | 状态改动 | 关闭记录 |
|------|----------|----------|
| `.ai/evidence/observability/finding-idle-semantics.md` | `OPEN（待用户裁决是否立项 T-0101）` → `CLOSED` | T-0101 已完成 idle 语义修复（NO_ACTIVE_TASK exit 3 分流 + 消费端对齐，v3.12.40） |
| `.ai/evidence/observability/finding-handoff-none-placeholder.md` | `OPEN（待用户裁决是否立项修复）` → `CLOSED` | T-0102 已完成 handoff 生成器 idle 占位缺陷修复（.ai/evidence/none/ 悬挂引用消除，v3.12.41） |

版本号经 CHANGELOG.md 核对（v3.12.40 = T-0101、v3.12.41 = T-0102）。

## A-2 KNOWN_ISSUES 收口

**改动**（`.ai/KNOWN_ISSUES.md`）：
- Open 区移除 2 项并移入 Recently Closed：
  - Bash command interception 项 → 注明 **T-0060 已实现 `bash_content_guard`**（Bash 写文件内容守卫，不再依赖通用命令拦截）
  - ProjectContinuity 自引用 timing issue 项 → 注明 **T-0049 已拆 continuity 自引用/炸弹**（源清单不再含自身，hash 自引用守卫 T-0058）
- Open 区保留仍有效的 2 项：seeded defects 手动验证、E2E lab fixture skipped

## A-3 HANDOFF-NEXT 处置

**引用检查**（grep 全库，含 .zcode/、tools/、scripts/、loop_core/、docs/、skills/、agents/）：
- 无任何 `.py` 代码引用（grep --include="*.py" 0 命中）
- 无活动文档引用：HANDOFF.md、CONTRACTS.md、CONVENTIONS.md、docs/、skills/、agents/ 均无引用
- 仅存历史性/生成式引用：历史任务卡（T-0034/T-0040/T-0046）、历史证据（T-0046 inventory、T-0101 证据、finding-idle-semantics.md 证据列表）、生成式 manifest（project_continuity.yaml 源清单、gates.yaml/task_graph.yaml scope 列表、state.yaml 描述）→ 判定：无活动引用

**处置**：归档移动（非删除）
- `mv .ai/HANDOFF-NEXT.md .ai/evidence/S6/handoff-next-archived-2026-07-23.md`（10988 字节，原样归档）
- 连续性同步（移动会使源清单漂移 → fail-closed 阻断）：
  1. `.ai/project_continuity.yaml` source_manifest 移除该条目，按官方算法重算 `source_sha256`（E9B685… → 981395…）；`semantic_sha256` 不变（payload 未动，4A628D… = 4A628D…）
  2. `repair_continuity.py .`（KNOWN_ISSUES.md 编辑漂移 1 项修复）
  3. `close_session.py .` 重生成 HANDOFF.md（内嵌 PROJECT-CONTINUITY 契约同步）

## A-4 历史任务卡状态收口

| 任务卡 | 改动前 `## Status` | task_graph | 改动后 |
|--------|--------------------|------------|--------|
| `.ai/tasks/T-0102.md` | in_progress | completed | **completed** |
| `.ai/tasks/T-0103.md` | completed | completed | 不动（已一致） |
| `.ai/tasks/T-0104.md` | in_progress | completed | **completed** |

表格区（基本信息等）其他内容未动。

## validate_state 前后对比

| 阶段 | 输出 | exit |
|------|------|------|
| 改动前（基线） | `[warn] [legacy] Historical task status mismatch: T-0102 task=in_progress task_graph=completed` + `T-0104 …` ×2 | 0（[ok] state is usable） |
| A-1/A-2/A-3 后 | 连续性漂移临时出现（KNOWN_ISSUES.md 编辑 + HANDOFF-NEXT 移动），经 repair_continuity + close_session 恢复 | — |
| 全部完成后 | **0 条 legacy warn、0 连续性错误、`[ok] state is usable`** | **0** |

**结论：validate_state legacy warn 已清零（A-4 目标达成），且无连续性漂移（A-3 归档未破坏 fail-closed 契约）。**
