# 治理生命周期：任务 / Gate / 产物状态机

本文是 loop-governance 技能对 .ai 治理契约的精简引用。
完整契约以项目 `.ai/CONTRACTS.md`、`gates.yaml`、任务文件为准。

## 三套状态严格分离

### 1. 任务状态（执行态）

`pending → active → in_progress → completed`（另有 `blocked`、`rejected`、
`approved_not_started`）。记录在 `.ai/task_graph.yaml` 与 `.ai/tasks/T-XXXX.md`，
两者必须一致（validator 会校验）。

### 2. Gate 状态（用户决策态）

`pending → approved | rejected`（另有 `blocked`）。
- **pending gate 是全停信号**：存在时不得进行任何写入性工作
  （gate_guard hook 强制，唯一例外是 gates.yaml 决策记录）。
- approved 之后还有执行侧状态：`approved_not_started → in_progress → completed`。
- **批准 ≠ 执行**：批准后需要用户发出精确执行请求（如
  "执行已批准的 G-XXXX"）才能开始。

### 3. 产物生命周期

`candidate → reviewed → repair_required → repaired → baseline_candidate
→ baseline_approved → active_reference → installed → superseded`

每次转换需要对应 gate。`approved / active / installed` 三态不得混淆：
文档被批准不代表生效，生效不代表已安装。

## 证据规则

- 证据存 `.ai/evidence/<task-id>/`，每个任务至少要有 `commands.md`。
- 原始证据**只可 supersede 不可删除**；修订产生 additive 版本
  （v0.1 → v0.2，冻结旧版）。
- PASS 语义分层，互不推导：
  `LOCAL_SLICE_PASS`（本地片段）→ `TASK_REQUIREMENTS_PASS`（任务验收）
  → `USER_ACCEPTED`（用户接受）→ `TASK_CLOSED`（任务关闭）。
  **`USER_ACCEPTED` 前须完成 Human Review Packet"理解确认"节**：用户答对全部理解性问题
  （`user_comprehension_confirmed: true`）后才允许标记；用户拒绝回答则记录 false 并降级标记
  （"用户已接受（未做理解确认）"），如实呈现在下一阶段 Human Review Packet 中。

## HANDOFF 纪律

`.ai/HANDOFF.md` 是跨会话恢复的核心，只写：当前阶段、当前任务、允许范围、
禁止范围、证据、pending gates、阻塞、下一步。不写全史。
session_brief hook 会在每次会话启动时注入其摘要——但**注入只是提醒，
不替代你读取原始文件**。

## 磁盘事实优先级（冲突时从高到低）

1. 用户最新明确指令
2. 磁盘原始字节
3. canonical governance records（state.yaml / gates.yaml / task_graph.yaml）
4. 已批准基线
5. 确定性命令输出（validator）
6. HANDOFF 摘要
7. 聊天记忆
