# Task Card: Reviewer R002

```yaml
task_id: L001-R002
run_id: L001
role: reviewer
objective: 按 review-plan.v0.1.md 复评修订后的候选协议 v0.2。

must_read:
  - ../../stable/user-origin.md
  - ../../roles/reviewer-brief.md
  - reviews/review-plan.v0.1.md
  - repairs/loop-protocol.candidate.v0.2.md
  - reviews/review-report.R001.yaml

allowed_write:
  - reviews/review-report.R002.yaml

forbidden:
  - 修改候选文档
  - 修改 stable/
  - 将 review 通过等同用户批准

required_output:
  - review_report
```

