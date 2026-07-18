# Repair Task Template

```yaml
task_id:
run_id:
role: repair
objective:

must_read:
  - review_report:
  - candidate_doc:
  - original_task_card:

allowed_write:
  - repaired_candidate:
  - repair_notes:

repair_scope:
  - 只处理 blocking_findings 和 required_change

stop_conditions:
  - 评审报告缺失
  - 原候选文档缺失
  - 修改要求超出任务权限
```

