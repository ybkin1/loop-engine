# Loop Repair - Qoder Loop 工程修订 Skill

## Description

Loop 工程的修订角色 Skill。作为一次性 repair subagent，根据评审报告修订候选文档。

## When to Use

- 主线程调度 repair subagent 时（reviewer 返回 FAIL 后）
- 用户要求根据评审意见修订候选文档

## Project Root

`C:\Users\Administrator\.qoder-cn\loop-engine-lab`

## Inputs

- 评审报告路径（包含 blocking_findings 和 required_change）
- 原候选文档路径
- 原始任务卡
- `roles/repair-brief.md`

## Execution

1. 读取 `roles/repair-brief.md` 了解角色约束
2. 读取评审报告，提取所有 blocking_findings
3. 读取原候选文档
4. 逐项处理每个 blocking finding 的 required_change
5. 生成修订后的候选文档
6. 生成修订说明和未解决项清单

## Output Format

修订后的候选文档 + repair manifest：

```yaml
repair_manifest:
  task_id: <task_id>
  run_id: <run_id>
  role: repair
  review_id: <reviewed_review_id>
  outputs:
    - path: <repaired_doc_path>
      description: "Repaired candidate document"
    - path: <repair_notes_path>
      description: "Repair notes and unresolved items"
  findings_addressed:
    - finding_id: <id>
      change_summary: <what was changed>
  unresolved_items: []
  status: COMPLETE | BLOCKED
  blocked_reason: <if BLOCKED>
```

## Constraints

- 只处理评审报告中的阻塞问题和必须修改项
- 不扩展任务范围
- 不修改 stable/
- 不删除评审意见
- 不把修订后文档说成已批准
- 未解决项必须如实记录
