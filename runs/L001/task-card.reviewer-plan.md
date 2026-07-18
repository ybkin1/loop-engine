# Task Card: Reviewer Plan

```yaml
task_id: L001-P001
run_id: L001
role: reviewer-plan
objective: 基于用户出发点、当前讨论主题和候选文档，生成本轮评审方案。

must_read:
  - ../../stable/user-origin.md
  - ../../roles/reviewer-plan-brief.md
  - outputs/loop-protocol.candidate.v0.1.md

allowed_write:
  - reviews/review-plan.v0.1.md

forbidden:
  - 修改候选文档
  - 修改 stable/
  - 直接给出最终评审结论

required_output:
  - review_plan
```

