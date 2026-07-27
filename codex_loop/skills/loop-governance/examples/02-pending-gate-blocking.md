# 示例二：Pending Gate 阻断写入的完整过程

> 本示例展示当存在 pending gate（待用户决策的质量门）时，
> AI 试图执行写入操作被 gate_guard hook 阻断的完整过程。
> 这是 Loop 治理中最核心的安全机制之一。

---

## 场景设定

- **当前状态**：任务 T-0002（架构设计）已完成，AI 产出了架构文档。
- **Gate 状态**：G-T-0002-ARCH-APPROVAL 处于 **pending** 状态，等待用户确认架构方案。
- **用户**：小王，正在手机上查看 AI 的进度，还没有回复。
- **AI 的行为**：AI 在等待用户回复期间，试图"提前开始"写一些代码。

---

## 完整交互过程

### 第一步：AI 完成架构任务，创建 Gate

AI 刚刚完成了 T-0002（架构设计），产出了架构文档，内容存放在 `.ai/evidence/T-0002/` 目录下。

AI 在 `gates.yaml` 中注册了一个新的 Gate：

```yaml
# .ai/gates.yaml（节选）
gates:
  - id: G-T-0002-ARCH-APPROVAL
    type: approval
    status: pending
    title: "T-0002 架构设计审批"
    description: "用户需确认待办事项应用的架构方案（单页应用 + 本地存储 + 组件化结构）"
    created: "2026-07-22T10:30:00"
    task_id: T-0002
    decisions: []
```

**AI 向用户汇报**：

> 我已经完成了待办事项应用的架构设计。简单说就是：
>
> - 整个应用是一个网页，不需要后端服务器
> - 页面分成几个区域：顶部输入区、中间事项列表、底部筛选栏
> - 数据保存在您浏览器里，不会上传到任何地方
>
> 详细设计文档在 `.ai/evidence/T-0002/` 目录下。
>
> 请您确认这个方案是否合适，确认后我就可以开始写代码了。

### 第二步：用户尚未回复，AI 试图"抢先"写代码

在等待期间，AI 的另一个实例（或同一实例在新会话中）被唤醒。

该实例读取项目状态后发现：架构设计已经产出、证据完整。于是它觉得
"架构已经很清楚了，用户肯定没意见"，试图直接开始写代码。

**AI 内部推理（错误示范）**：
> 架构文档已经完成，证据齐全，质量检查通过。我可以开始实现第一个组件了。
> 我先创建一个 HTML 文件作为应用入口。

### 第三步：Gate Guard 阻断

当 AI 尝试执行 `Write` 工具创建 `index.html` 时，**gate_guard hook** 介入：

**Hook 执行过程**（发生在工具调用之前，AI 和用户都看不到细节）：

1. `gate_guard.py` 被 PreToolUse 事件触发（matcher: `Write|Edit`）
2. 脚本读取 `.ai/gates.yaml`
3. 发现存在 `status: pending` 的 Gate（G-T-0002-ARCH-APPROVAL）
4. 目标路径 `index.html` 不在决策记录豁免列表中（豁免列表只有 `.ai/gates.yaml`）
5. **退出码 2** —— 阻断写入

**AI 收到的结果**：
```
[error] PreToolUse blocked by gate_guard:
  Pending gate(s): G-T-0002-ARCH-APPROVAL (T-0002 架构设计审批)
  Reason: 存在待用户决策的 Gate，禁止写入操作。
  请先向用户展示 pending gate 内容，等待用户明确决策。
```

### 第四步：AI 向用户展示被阻断信息

被阻断后，AI 应该按治理程序执行——而不是抱怨或尝试绕过：

**AI 输出（正确做法）**：

> [loop-governance] project_root: C:\Users\Administrator\ZCodeProject\loop-engine
> [loop-governance] phase: 架构设计
> [loop-governance] current_task_id: T-0002
> [error] Pending gate(s) require user decision: G-T-0002-ARCH-APPROVAL
>
> 小王，这里有一个需要您决定的事情：
>
> **等待您确认：架构设计方案**
>
> 我之前已经完成了待办事项应用的架构设计。方案摘要：
> - 单网页应用，不需要后端
> - 数据存浏览器本地
> - 代码分成几个独立的组件（输入组件、列表组件、筛选组件）
>
> 在您确认之前，我不能继续写代码。这确保了您对项目的每一步都有掌控。
>
> 您可以回复：
> - "同意"或"批准 G-T-0002-ARCH-APPROVAL"—— 我就进入开发阶段
> - "我有疑问"—— 告诉我哪里需要修改
> - "先等一下"—— 我会保持当前状态，不做任何改动

### 第五步：用户做出决策

**用户回复**：
> 同意，继续吧。

### 第六步：AI 记录决策并解除阻断

**AI 操作**（写入 `gates.yaml` 是唯一被豁免的写入操作）：

```yaml
# .ai/gates.yaml（更新后）
gates:
  - id: G-T-0002-ARCH-APPROVAL
    type: approval
    status: approved
    title: "T-0002 架构设计审批"
    description: "用户需确认待办事项应用的架构方案"
    created: "2026-07-22T10:30:00"
    task_id: T-0002
    decisions:
      - decision: approved
        approved_by: user
        approval_text: "同意，继续吧。"
        approved_at: "2026-07-22T14:15:00"
```

**AI 向用户确认**：

> 收到，架构方案已批准。G-T-0002-ARCH-APPROVAL 状态变为"已批准"。
>
> 不过，批准不等于我就自动开始写代码——需要您说一句"开始开发"或"执行 G-T-0002-ARCH-APPROVAL"，我才会动手。这是双段确认机制，防止我自作主张。
>
> 您准备好了就告诉我。

**用户回复**：
> 开始开发吧。

**AI 输出**：
> 好的，开始执行 T-0003（功能开发）。我先创建任务卡，然后开始写代码。

---

## 关键要点

1. **Gate 是用户的决策，不是 AI 的结论** —— 即使架构文档"看起来没问题"，AI 也不能跳过用户确认直接写代码。
2. **阻断发生在工具层面** —— gate_guard hook 在 `PreToolUse` 事件触发，在工具真正执行之前拦截。AI 无法绕过。
3. **唯一的豁免** —— 只有 `.ai/gates.yaml` 可以在 pending 期间写入。这是为了避免死锁：如果用户批准了但无法记录决策，Gate 永远无法解除。
4. **双段确认** —— 批准（approved）和执行（in_progress）是两步。用户说"同意"只是批准，还需要"开始"才执行。防止滑坡。
5. **AI 不应该抱怨被阻断** —— 被阻断后 AI 应该**立即向用户汇报**，而不是尝试换个方式绕过。治理程序的正确行为是：展示 pending gate -> 等待用户决策 -> 记录决策 -> 等待执行指令。
6. **即使用户没看到技术细节** —— 用户小王只看到了"架构方案摘要"，没有看到技术文档本身。但 Gate 机制确保了他的决策权：他不需要看懂代码也能决定"这个方向对不对"。
