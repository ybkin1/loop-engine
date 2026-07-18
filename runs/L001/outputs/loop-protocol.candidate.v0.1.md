# Loop Protocol Candidate v0.1

状态：candidate

## 目的

本协议用于让主线程编排一次性 subagent，完成文档生成、评审、修订和交接循环。

## 工作流

```text
writer -> reviewer-plan -> reviewer -> repair -> reviewer
```

## 主线程

主线程创建 run、分配任务卡、指定输入输出路径，并根据评审结论决定下一步。

## Agent

每个 subagent 只做任务卡指定的一件事。

## 文档

- `stable/` 保存权威入口。
- `roles/` 保存角色提示词。
- `templates/` 保存模板。
- `runs/` 保存过程产物。
- `registry/` 保存索引。

## 评审

评审 agent 输出 `PASS`、`FAIL` 或 `BLOCKED`。

## 修订

若评审失败，repair agent 根据评审报告修改候选文档。

## 刹车

当任务越权、输入缺失或需要用户批准时停止。

