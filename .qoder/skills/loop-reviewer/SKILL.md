# Loop Reviewer - Qoder Loop 工程评审 Skill

## Description

Loop 工程的评审角色 Skill。包含两个子模式：reviewer-plan（生成评审方案）和 reviewer（执行中立评审）。

## When to Use

- 主线程调度 reviewer-plan 或 reviewer subagent 时
- 用户要求对候选文档进行评审
- 用户要求生成评审方案

## Project Root

`C:\Users\Administrator\.qoder-cn\loop-engine-lab`

## Mode 1: Reviewer-Plan（评审方案生成）

### Inputs
- 候选文档路径
- `roles/reviewer-plan-brief.md`

### Execution
1. 读取 `roles/reviewer-plan-brief.md`
2. 读取候选文档和上下文
3. 围绕以下核心生成评审方案：
   - 当前讨论主题
   - 用户出发点和立场
   - 当前要解决的问题
   - 最终目标
4. 输出可执行的评审方案

### Output
评审方案文件，包含：评审对象、评审目标、必须检查项、阻塞标准、非阻塞建议标准、PASS/FAIL/BLOCKED 判定规则

## Mode 2: Reviewer（中立评审执行）

### Inputs
- 候选文档路径
- 评审方案路径
- 任务卡
- `roles/reviewer-brief.md`

### Execution
1. 读取 `roles/reviewer-brief.md`
2. 按照评审方案逐项检查
3. 记录阻塞发现和非阻塞建议
4. 进行风险评估
5. 输出判定

### Output Format

```yaml
review_id: <review_id>
run_id: <run_id>
reviewed_doc: <doc_path>
status: PASS | FAIL | BLOCKED

blocking_findings:
  - id: <finding_id>
    severity: high | medium
    issue: <description>
    required_change: <what must change>

non_blocking_suggestions:
  - id: <suggestion_id>
    suggestion: <description>

risk_assessment:
  context_drift: low | medium | high
  authority_conflict: low | medium | high
  dirty_data_risk: low | medium | high
  user_gate_needed: true | false

verdict:
  next_action: <recommended_next_step>
```

## Constraints

- PASS 仅表示可候选提升，不等同于用户批准
- 不修改候选文档
- 不修改 stable/
- 评审必须中立，围绕用户目标而非个人偏好
