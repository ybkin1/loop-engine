# T-0036 候选素材基线决策记录 v0.1

Gate: `G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1`

Decision: `accepted_candidate_baseline`

Decision status: `user_accepted / recorded`

Decision actor: `user`

Decision source: explicit user message at `2026-07-27T10:10:36+08:00`

Decision text: `接受 G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1`

## Recorded Decision

用户接受当前冻结的 T-0036 素材库，作为 Codex Loop 的候选素材基线，身份为 `candidate / research-baseline-v0.1`。该接受仅供后续独立版本冻结和实现规划使用。

唯一证据基线仍为 `.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md`：`65` subjects，SHA-256 `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`，`65/65` 零漂移。

## Decision Boundaries

- 接受不等于版本冻结；本记录不执行版本冻结。
- T-0036 仍保持 `active`，本记录不关闭 T-0036。
- 本记录不创建或执行 T-0037 review；T-0037 必须等待后续独立版本冻结。
- isolated candidate-path verification gap 仍开放，未被本接受决定修复或豁免。
- 素材库仍不是 Runtime 规则、生产标准或用户项目配置。
- 本决定不授权 Host Integration、Runtime、Agent、安装、激活、部署、迁移、权限、密钥、生产数据或真实项目。

本记录是用户决策事实，不把 reviewer PASS、测试或 validator 结果升级为用户接受以外的授权。
