# T-0036 素材库版本冻结用户决策包 v0.1

Gate: `G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`

Status: `pending / user_decision_required`

## 当前事实

| assertion | current fact |
| --- | --- |
| candidate decision | `approved / accepted_candidate_baseline` |
| candidate identity | `candidate / research-baseline-v0.1` |
| only input manifest | `material-library-residual-path-repair-freeze-manifest.v0.1.md` |
| input manifest fingerprint | `9835` bytes / `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC` |
| content subjects | `65/65` path、size、SHA-256 匹配；零漂移 |
| task status | T-0036 `active` |
| isolated candidate-path gap | `open / unwaived` |
| downstream status | T-0037 review 未启动；Host Integration 未进入 |

## 用户本次决定

是否批准后续在单独精确执行请求下，把这 65 个素材库 subject 的当前内容快照正式记录为不可漂移的 `research-baseline-v0.1` 版本。

批准只允许后续执行请求进入本 Gate 的精确执行 allowlist。批准本身不生成最终 version-freeze manifest、不写冻结记录、不改变 65 个 subject，也不关闭 T-0036。

## 后续执行契约

只有在批准后再收到精确短语 `执行 G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`，才允许新增最终冻结记录、最终 version-freeze manifest、冻结验证和执行 changed-path manifest。最终 manifest 必须从唯一输入 manifest 派生，并证明 `65/65` path、size、SHA-256 完全一致；旧 manifest 保持只读。

版本冻结内容不包括 decision record、review evidence、candidate-path gap、治理文件或 Gate 证据。isolated candidate-path gap 必须继续明确记录且不得视为已修复或豁免。

## 不授权事项

本 Gate 不冻结 isolated candidate、Runtime、Agent、Host 或真实项目行为；不修改 catalog、register、profiles、templates、既有 review evidence、candidate/global Project Governor、测试、`codex_loop` 或 Runtime；不关闭 T-0036；不创建或执行 T-0037 review；不进入 Host Integration、部署、迁移、权限、密钥或真实项目。

Git tag、commit 或发布动作不能替代版本冻结证据，且均不在本 Gate 授权范围内。

批准短语：`批准 G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`

批准后仍需单独执行短语：`执行 G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`
