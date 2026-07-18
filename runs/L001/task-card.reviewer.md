# Task Card: Reviewer R001

```yaml
task_id: L001-R001
run_id: L001
role: reviewer
objective: 按 review-plan.v0.1.md 评审候选协议 v0.1。

must_read:
  - ../../stable/user-origin.md
  - ../../roles/reviewer-brief.md
  - reviews/review-plan.v0.1.md
  - outputs/loop-protocol.candidate.v0.1.md

allowed_write:
  - reviews/review-report.R001.yaml

forbidden:
  - 修改候选文档
  - 修改 stable/
  - 将 review 通过等同用户批准

required_output:
  - review_report
```

