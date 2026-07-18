# Task Card: Writer

```yaml
task_id: L001-W001
run_id: L001
role: writer
objective: 生成 Loop 工程协议候选文本 v0.1，说明主线程如何编排一次性 subagent 完成写作、评审、修订和交接。

must_read:
  - ../../stable/user-origin.md
  - ../../stable/current-loop-protocol.md
  - ../../roles/writer-brief.md
  - ../../templates/task-card.template.md

allowed_write:
  - outputs/loop-protocol.candidate.v0.1.md
  - evidence/write-manifest.writer.yaml

forbidden:
  - 修改 ../../stable/
  - 修改 ../../registry/
  - 宣称候选文档已批准
  - 调用旧 Project Governor / codex-rule / validator

required_output:
  - candidate_document
  - write_manifest

pass_condition:
  - 候选文档覆盖目录、角色、任务卡、评审、修订、promotion、刹车条件。

stop_conditions:
  - 输入文档缺失
  - 任务目标与权限冲突
  - 需要用户 gate
```

