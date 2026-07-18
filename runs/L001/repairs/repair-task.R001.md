# Repair Task R001

```yaml
task_id: L001-X001
run_id: L001
role: repair
objective: 根据 review-report.R001.yaml 修订候选协议，输出 v0.2。

must_read:
  - ../../roles/repair-brief.md
  - task-card.writer.md
  - outputs/loop-protocol.candidate.v0.1.md
  - reviews/review-report.R001.yaml

allowed_write:
  - repairs/loop-protocol.candidate.v0.2.md
  - evidence/repair-manifest.R001.yaml

repair_scope:
  - BF-001
  - BF-002
  - BF-003
  - NBS-001

forbidden:
  - 修改 stable/
  - 修改 registry/
  - 扩展到真实项目安装
```

