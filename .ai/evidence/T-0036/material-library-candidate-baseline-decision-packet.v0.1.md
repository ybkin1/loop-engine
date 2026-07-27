# T-0036 候选素材基线用户决策包 v0.1

Gate: `G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1`

Status: `pending / user_decision_required`

## 当前候选与证据

当前候选身份是 `candidate / research-baseline-v0.1`。唯一证据基线是 `.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md`：冻结 `65` subjects，清单 SHA-256 为 `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`，复审前后 `65/65` 完整匹配、零漂移。

| evidence | result |
| --- | --- |
| fresh independent rereview | `PASS`；无新 P0/P1/P2 finding |
| F-001..F-006 | 全部 `PASS` |
| catalog/register/coverage/freshness | `46/46` |
| strict subsets | materials `8/17`；templates `7/9` |
| focused pytest | `28 passed` |
| full pytest | `41 passed, 5 subtests passed` |

reviewer PASS、测试和 validator 只是决策证据，不是用户接受。当前仍是 T-0036 `active / baseline_not_accepted`。

## 尚未关闭的边界

- isolated candidate-path verification gap 仍开放；它不属于本次素材库 PASS 的阻塞 finding，也没有被 PASS 修复或豁免。
- T-0035 仅为行政完成，不代表产品 PASS、用户接受、Runtime 实现、安装、激活或 Host Integration。
- 素材库仍不是 Runtime 规则、生产标准或用户项目配置。
- T-0037 必须等待本次基线决策和后续独立版本冻结。

## 仅需决定一件事

是否接受当前冻结的 T-0036 素材库，作为 Codex Loop 的候选素材基线。

| 选项 | 结果 |
| --- | --- |
| 接受 | 将 T-0036 记录为候选素材基线，仅供后续独立版本冻结和实现规划使用；本 Gate 本身不冻结版本、不关闭任务。 |
| 拒绝 | 保持 `baseline_not_accepted`，记录拒绝原因。 |
| 要求修复 | 本 Gate 内不修复；另建独立 repair Gate 后再处理。 |
| 暂缓 | 保持当前状态，不推进下游。 |

## 明确不授权

Gate 创建不等于接受。本 Gate 不执行版本冻结、不关闭 T-0036、不创建或执行 T-0037 review，也不授权 Host Integration、Runtime、Agent、安装、激活、部署、迁移、权限、密钥、生产数据或真实项目。

可用回复：`接受 G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1`、`拒绝 G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1，原因：...`、`要求修复 G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1，原因：...` 或 `暂缓 G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1`。
