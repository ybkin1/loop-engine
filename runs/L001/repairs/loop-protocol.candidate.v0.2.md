# Loop Protocol Candidate v0.2

状态：candidate

## 目的

本协议用于让主线程编排一次性 subagent，完成文档生成、评审、修订和交接循环，同时防止文档混乱、权限扩大和候选产物冒充正式协议。

## 权威来源

只有同时满足以下条件的文档才是权威：

- 位于 `stable/`。
- 状态为 `approved`。
- 被 `registry/docs.yaml` 标记为 current。

`runs/` 中的所有文档默认都是过程产物。

## 文档状态

```text
draft -> candidate -> reviewed -> approved -> superseded -> archived
```

## 工作流

```text
writer -> reviewer-plan -> reviewer -> repair -> reviewer
```

默认最多 3 轮修订。达到上限仍未通过时，主线程停止并交给用户。

## 任务卡最小字段

每个 subagent 必须收到任务卡：

```yaml
task_id:
run_id:
role:
objective:
must_read:
allowed_write:
forbidden:
required_output:
pass_condition:
stop_conditions:
```

subagent 只能读取 `must_read` 所列上下文包，且只能写入 `allowed_write`。

## 输出清单

每个执行型 subagent 必须输出 write manifest：

```yaml
task_id:
role:
read:
written:
status:
```

主线程用它检查是否读写越权。

## Promotion Gate

reviewer 返回 `PASS` 只表示候选文档可进入 promotion 候选，不表示用户批准。

进入 `stable/` 前必须满足：

- reviewer 状态为 `PASS`。
- 没有 `BLOCKED` 项。
- 输出路径符合任务卡。
- registry 可追踪来源 run。
- 不涉及权限扩大。
- 若涉及协议安装、真实项目修改或生产动作，必须有用户明确批准。

## 刹车条件

主线程必须在以下情况停止 loop：

- subagent 写入非授权路径。
- 候选文档宣称自己已批准或已安装。
- review 把测试通过、CI 通过或评审通过等同于用户批准。
- 出现多个互相冲突的 current 文档。
- registry 无法追踪 current 来源。
- 旧工具、旧 skill、旧 MCP 抢协议权威。
- handoff 或 current 被用于扩大权限。

## Context Pack

每类 subagent 只读自己的 context pack：

- writer: 用户出发点、当前协议、writer brief、任务卡。
- reviewer-plan: 用户出发点、候选文档、reviewer-plan brief。
- reviewer: 用户出发点、评审方案、候选文档、reviewer brief。
- repair: 原候选文档、评审报告、repair brief、修订任务卡。

这能降低单个会话上下文压力，但不保证总 token 必然下降。只有当 context pack 足够短、权威且按需读取时，才会节约 token。

