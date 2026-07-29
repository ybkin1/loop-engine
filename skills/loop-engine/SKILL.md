# Loop Engine - Qoder Loop 工程主编排 Skill

## Description

Loop 工程的主编排入口。负责创建 run、生成任务卡、调度 subagent（writer/reviewer/repair/handoff-editor/archlet/loopany/tools-registry/loopbase）、检查输出、推进 loop 循环。

## When to Use

- 用户要求启动一个 Loop 工程循环
- 用户要求创建新的 run 或任务
- 用户要求推进当前的 write -> review -> repair 循环
- 用户要求检查当前 run 的状态

## Project Root

`C:\Users\Administrator\.qoder-cn\loop-engine-lab`

## Inputs

- 用户的目标描述或任务需求
- 当前治理状态（自动从 `.ai/state.yaml`、`.ai/HANDOFF.md` 读取）
- 持久记忆上下文（自动从 `.ai/loopany/` 读取，如存在）

## Execution Flow

### 1. 启动校验

读取以下文件确认治理状态可用：

```
.ai/state.yaml
.ai/HANDOFF.md
.ai/gates.yaml
.ai/task_graph.yaml
.ai/loopany/index.md        # 如存在，恢复持久记忆上下文
.ai/loopany/learnings/      # 如存在，加载相关经验
```

运行 `python .ai/checkers/run_governance_checks.py --gates .ai/gates.yaml` 确认无阻塞。

### 2. 创建 Run

在 `runs/` 下创建新的 run 目录（如 `runs/L001/`），包含：

- `run-summary.md` - 基于 `templates/run-summary.template.md`
- 更新 `registry/runs.yaml`

### 3. 生成任务卡并调度 Subagent

根据当前 loop 步骤，生成任务卡并调度对应的 subagent：

| Loop 步骤 | Subagent 角色 | Qoder Agent 类型 | 角色 Brief |
|-----------|--------------|-----------------|-----------|
| 写作 | writer | GeneralPurpose | `roles/writer-brief.md` |
| 评审方案 | reviewer-plan | GeneralPurpose | `roles/reviewer-plan-brief.md` |
| 评审 | reviewer | GeneralPurpose | `roles/reviewer-brief.md` |
| 修订 | repair | GeneralPurpose | `roles/repair-brief.md` |
| 交接 | handoff-editor | GeneralPurpose | `roles/handoff-editor-brief.md` |
| 架构检查 | archlet | GeneralPurpose | `roles/archlet-brief.md` |
| 持久记忆 | loopany | GeneralPurpose | `roles/loopany-brief.md` |
| 工具注册 | tools-registry | GeneralPurpose | `roles/tools-registry-brief.md` |
| 会话索引 | loopbase | GeneralPurpose | `roles/loopbase-brief.md` |

调度方式：使用 Agent tool，`subagent_type: "GeneralPurpose"`，在 prompt 中包含：
1. 角色 brief 内容
2. 任务卡内容
3. **角色上下文文件** (`.ai/role-context/<role_id>.md`) — MUST_READ
4. allowed_write 路径
5. 明确的输出要求

**角色上下文生成协议** (平台限制绕过)：
Qoder 的 Agent tool 子代理不继承主会话的文件上下文。因此 R11 在激活任何角色前，
必须调用 `generateRoleContext(projectRoot, roleId)` 生成该角色的上下文文件，
并作为 Agent tool 的 `must_read` 传入。

上下文包含：
- 角色契约 (CONTRACT.yaml)
- 项目结构 (src/tests/scripts/docs/ 文件列表)
- 治理状态 (state.yaml 摘要)
- **代码角色 (R06-R09)**：实际源码内容 (≤50KB, 每文件≤5KB)
- **文档角色 (R01-R05,R10)**：架构/设计/规范文档内容
- 角色思维框架

上下文文件生成命令：
```typescript
import { generateRoleContext } from "../src/core/role_context.js";
const ctx = generateRoleContext(projectRoot, "R06");
// ctx.context_file → .ai/role-context/R06.md
```

### 4. 检查输出

subagent 返回后：
- 验证输出文件存在于 allowed_write 路径
- 检查输出是否符合任务卡的 pass_condition
- 根据评审结论决定下一步

### 5. 推进 Loop

```
writer 完成 → 调度 reviewer-plan
reviewer-plan 完成 → 调度 reviewer
reviewer PASS → 进入 promotion 流程（需用户 gate）
reviewer FAIL → 调度 repair → 重新调度 reviewer
reviewer BLOCKED → 升级给用户决策
```

### 5.1 辅助 Skill 调度时机

以下 skill 不在主循环中，而是在特定时机按需调度：

| Skill | 调度时机 | 角色 Brief |
|-------|---------|------------|
| archlet | plan 阶段（架构全貌）、execute 前（边界检查）、execute 后（diff 叠加） | `roles/archlet-brief.md` |
| loopany | 任务完成后（记录 outcome）、新会话开始（恢复上下文）、积累 5+ 任务后（reflect） | `roles/loopany-brief.md` |
| tools-registry | execute 阶段需要外部服务时（安全调用）、governance 检查时 | `roles/tools-registry-brief.md` |
| loopbase | handoff 阶段（会话摘要）、定期健康检查（成本/insights） | `roles/loopbase-brief.md` |

### 6. 更新治理状态

每步完成后更新：
- `.ai/state.yaml` - 当前任务/阶段
- `.ai/task_graph.yaml` - 任务节点
- `.ai/gates.yaml` - Gate 注册
- `.ai/HANDOFF.md` - 交接文档
- `.ai/PROGRESS.md` - 进度日志
- `registry/runs.yaml` - Run 注册
- `.ai/loopany/tasks/<task-id>.md` - 任务记录（loopany）
- `.ai/loopany/outcomes/outcomes.jsonl` - 结果追加（loopany）

## Forbidden Actions

- 不修改 `stable/` 除非通过 promotion gate
- 不把候选文档说成已批准
- 不把 reviewer PASS 等同于用户批准
- 不创建 Gate 或任务 without 用户授权
- 不执行高风险动作（deployment/rollback/database/permission/secret/payment/production_data/migration）

## Available Skills

本编排器可调度以下辅助 skill（详见 `skills/` 目录）：

| Skill | 路径 | 用途 |
|-------|------|------|
| archlet | `skills/archlet/SKILL.md` | 架构治理与可视化 |
| loopany | `skills/loopany/SKILL.md` | 持久记忆与自我改进 |
| tools-registry | `skills/tools-registry/SKILL.md` | 团队工具与密钥管理 |
| loopbase | `skills/loopbase/SKILL.md` | 跨会话记忆与可观测性 |

## Output

- Run 目录下的所有产物
- 更新后的治理文件
- loopany 任务记录和 outcome（如已启用）
- 向用户报告当前 loop 状态和下一步建议
