# Loopany - 持久记忆与自我改进 Skill

## Description

基于 [loopany](https://github.com/superdesigndev/loopany) 的持久记忆和自我迭代技能。解决"代理每次会话都从零开始"的问题——通过结构化的任务记录、结果追踪和 reflect 循环，让 Qoder 跨会话保持上下文并持续改进。

## When to Use

- 任务完成后，记录结果和经验供后续会话使用
- 新会话开始时，读取历史上下文避免重复犯错
- 定期触发 reflect 循环，提炼经验并改进工作方式
- 用户要求"记住这个"、"下次别再犯同样的错"
- 长周期任务跨会话延续时

## Project Root

`C:\Users\Administrator\.qoder-cn\loop-engine-lab`

## 数据模型

采用 loopany 的核心设计：Markdown + frontmatter 作为事实来源，append-only JSONL 保存引用图。

```
.ai/
├── loopany/
│   ├── tasks/          # 任务记录（每个任务一个 .md）
│   │   └── <task-id>.md
│   ├── outcomes/       # 任务结果（append-only）
│   │   └── outcomes.jsonl
│   ├── learnings/      # 提炼的经验
│   │   └── <learning-id>.md
│   ├── skill-proposals/ # 自我改进建议
│   │   └── <proposal-id>.md
│   └── index.md        # 任务索引（按状态分类）
```

## Execution

### 1. 任务记录（Task Capture）

每个任务完成后，在 `.ai/loopany/tasks/<task-id>.md` 写入：

```markdown
---
task_id: <id>
run_id: <run-id>
created_at: <timestamp>
completed_at: <timestamp>
status: done | blocked | abandoned
objective: <what was attempted>
outcome_ref: <path-to-outcome>
tags: [<relevant-tags>]
---

## What was done
<summary of actions taken>

## What happened
<outcome summary>

## Open items
- <anything still pending>
```

同时在 `outcomes.jsonl` 追加一行：

```json
{"task_id":"<id>","timestamp":"<ts>","outcome":"success|partial|failure","summary":"<one-line>","learnings":["<ref>"]}
```

### 2. 上下文恢复（Session Restore）

新会话开始时：

1. 读取 `.ai/loopany/index.md` 获取任务全景
2. 读取当前 `state.yaml` 和 `HANDOFF.md`
3. 读取最近 3-5 个任务的 outcomes
4. 读取相关的 learnings
5. 向用户报告："上次我们做到了 X，还有 Y 未完成"

### 3. Reflect 循环（Self-Improvement）

当积累足够结果（建议 5+ 个任务）后触发：

1. **读取** 所有 outcomes.jsonl 记录
2. **分析** 模式：
   - 哪些任务类型成功率高？
   - 哪些反复失败或阻塞？
   - 有没有重复的工作模式可以提炼？
3. **生成 learnings**：写入 `.ai/loopany/learnings/<id>.md`

```markdown
---
learning_id: <id>
created_at: <timestamp>
source_tasks: [<task-id>, ...]
confidence: high | medium | low
category: workflow | tool-usage | constraint | pattern
---

## Observation
<what pattern was noticed>

## Belief
<what we now believe to be true>

## Proposed action
<what should change - new constraint, skill update, workflow change>
```

4. **生成 skill-proposals**：如果 learning 建议改变工作方式，写入 `.ai/loopany/skill-proposals/<id>.md`

```markdown
---
proposal_id: <id>
created_at: <timestamp>
source_learnings: [<learning-id>, ...]
status: pending | accepted | rejected
target_skill: <which skill to modify>
---

## Current behavior
<what we do now>

## Proposed change
<what should change>

## Rationale
<why, with evidence from learnings>

## Diff
<specific changes to skill files>
```

5. **用户决策**：向用户展示 proposals，接受则合入对应 skill 文件

### 4. 与 Loop 工程集成

| Loop 阶段 | Loopany 的作用 |
|-----------|---------------|
| plan | 提供历史任务上下文，避免重复规划 |
| execute | 记录每步操作到 task capture |
| verify | 记录结果到 outcomes |
| iterate | reflect 循环触发改进 |
| handoff | 提供完整任务历史供下一会话恢复 |

## 输出

- 任务记录文件（`.ai/loopany/tasks/`）
- 结果日志（`.ai/loopany/outcomes/outcomes.jsonl`）
- 经验文档（`.ai/loopany/learnings/`）
- 改进建议（`.ai/loopany/skill-proposals/`）
- 任务索引（`.ai/loopany/index.md`）

## Constraints

- outcomes.jsonl 是 append-only，不可修改已有记录
- learnings 和 skill-proposals 只是建议，需要用户批准才能生效
- 不自动修改任何 skill 文件或治理文件
- 任务记录只记录事实，不做价值判断
- reflect 循环不频繁触发（建议每 5-10 个任务一次）
- 所有数据都是 Markdown，人类可读可编辑
