# T-0036 行政收口用户决策包 v0.1

Gate: `G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`

Status: `pending / user_decision_required`

## 一项用户决定

是否批准后续精确执行 T-0036 的行政收口，使任务和 task graph 记录为 `completed`。

## 已冻结的候选基线

| item | verified fact |
| --- | --- |
| baseline acceptance | 用户已接受候选素材基线 |
| version identity | `research-baseline-v0.1` |
| final manifest | `10202` bytes / `24DDC5434B0FFE3D078AED5B8A2101CF6A0A4C97DF73553E949FB668BDE98F20` |
| subject triples | 新旧 `65/65` 完全一致 |
| disk verification | `65/65`，零漂移 |
| current task | T-0036 `active` |
| candidate-path gap | `open / unwaived` |
| T-0037 review | 尚未创建或执行 |

## 预期执行结果

只在批准和后续精确执行请求均收到后：更新 `.ai/tasks/T-0036.md` 与 `.ai/task_graph.yaml` 为 `completed`，记录 baseline acceptance/version freeze 指针，并写入 closeout record、validation 和 changed-path manifest。

这不是产品 PASS、用户项目验收、Runtime/Agent/Host 完成、安装、激活、部署或真实项目授权。T-0037 必须等待后续独立 Gate。

## 严格禁止

不修改 `materials/**`、65 个冻结对象、任何旧证据、candidate/global Project Governor、tests、`codex_loop` 或 Runtime；不创建、修改或执行 T-0037 review；不执行 Host Integration、迁移、权限、密钥、生产数据或真实项目动作。

Gate 注册不等于批准，批准不等于执行。当前仅等待用户批准。
