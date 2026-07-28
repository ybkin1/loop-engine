# T-0055 基线审计：事实源与投影矩阵

## 当前事实源候选

| 数据 | 当前位置 | 观察 | 风险 |
|---|---|---|---|
| 当前任务/阶段 | `.ai/state.yaml` | 运行时读取 | 与 task graph、task file、HANDOFF 分散 |
| 任务注册 | `.ai/task_graph.yaml` | 任务状态另存 | 可能与 state/status 漂移 |
| Gate 注册 | `.ai/gates.yaml` | gate 生命周期另存 | `current_gate_id` 依赖交叉校验 |
| 任务正文 | `.ai/tasks/<id>.md` | 文档状态另存 | 与 task graph 可能不一致 |
| 交接渲染 | `.ai/HANDOFF.md` | 结构化投影 | auditor 会独立重建并拒绝漂移 |
| Continuity | `.ai/project_continuity.yaml` | manifest/hash 快照 | 当前 manifest 未包含 HANDOFF、state、task graph、gates 本身 |
| 交易/检查点 | `.ai/transaction_registry.yaml` | 另行记录 | 与 close_session/checkpoint 投影存在耦合 |

## 基线判断

当前实现更接近“多个持久化投影 + 交叉校验”，尚未证明存在一个可提交的 canonical aggregate。后续必须用代码和测试确认：

1. 哪个结构是唯一可变事实源；
2. 哪些文件只是派生投影；
3. 一次任务/gate 状态变化是否能原子提交；
4. 失败时是否能恢复到旧一致快照；
5. 投影生成是否幂等。

## 证据边界

本表是基线审计结果，不将设计怀疑直接标记为已证实缺陷；需在 finding register 中以 confirmed/disproved/not_verified 分类。
