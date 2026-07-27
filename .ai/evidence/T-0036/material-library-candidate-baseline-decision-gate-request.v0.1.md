# T-0036 候选素材基线决策 Gate 请求 v0.1

Gate: `G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1`

Status: `pending / user_decision_required`

## 唯一决策

是否接受当前冻结的 T-0036 素材库，作为 Codex Loop 的候选素材基线。

Gate 创建不等于用户接受。fresh independent rereview 的 `PASS`、测试结果和 validator 成功都只是证据，不能代替用户决定。

## 决策依据

- 当前候选身份：`candidate / research-baseline-v0.1`。
- 唯一证据基线：`.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md`。
- 冻结清单：`65` subjects；清单 SHA-256 为 `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`；`65/65` 匹配且零漂移。
- fresh independent rereview verdict=`PASS`；F-001..F-006 全部通过；catalog/register/coverage/freshness=`46/46`；strict subset 为 materials `8/17`、templates `7/9`。
- focused pytest=`28 passed`；full pytest=`41 passed, 5 subtests passed`。
- T-0036 仍为 `active / baseline_not_accepted`；isolated candidate-path verification gap 仍开放，但不是本次素材库 PASS 的阻塞 finding。
- T-0035 仅为行政完成；素材库仍不是 Runtime 规则、生产标准或用户项目配置。

## 边界

本 Gate 不执行版本冻结，不关闭 T-0036，不创建或执行 T-0037 review。T-0037 必须等待本次基线决策和后续独立版本冻结。

本 Gate 不授权 Host Integration、Runtime、Agent、安装、激活、部署、迁移、权限、密钥、生产数据或真实项目，也不允许修改 65 个冻结对象、冻结清单、素材内容、既有复审证据、candidate/global Project Governor、测试或 `codex_loop`。

## 用户选项

- 接受：将 T-0036 记录为 Codex Loop 候选素材基线，仅供后续独立版本冻结和实现规划使用。
- 拒绝：保持 `baseline_not_accepted`，记录拒绝原因。
- 要求修复：不得在本 Gate 内修复；另建独立 repair Gate。
- 暂缓：保持当前状态，不推进下游。

在用户明确作出上述决定前，Gate 保持 `pending / user_decision_required`。
