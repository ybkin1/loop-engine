# T-0036 素材库版本冻结 Gate 请求 v0.1

Gate: `G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`

Status: `pending / user_decision_required`

## Gate 目标

请求用户决定是否允许在后续单独精确执行请求下，将已接受的 T-0036 素材库内容快照正式记录为不可漂移的 `research-baseline-v0.1` 版本。

Gate 创建不等于版本冻结。用户批准也不等于冻结执行；批准后仍需用户单独发送 `执行 G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`，才允许执行冻结。

## 输入与冻结对象

- 候选身份：`candidate / research-baseline-v0.1`。
- 用户已接受的候选基线 Gate：`G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1 = approved / accepted_candidate_baseline`。
- 唯一输入：`.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md`。
- 输入清单：`9835` bytes；SHA-256 `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`。
- 冻结对象：清单中的 `65` 个已接受素材库 subject；当前 path、size、SHA-256 为 `65/65` 完全匹配，零漂移。

后续获准执行时必须新增最终 `.ai/evidence/T-0036/material-library-version-freeze-manifest.v0.1.md`，不得覆盖旧 freeze manifest；新 manifest 必须证明全部 `65/65` path、size、SHA-256 与输入完全一致。

## 明确排除

本 Gate 只冻结素材库内容快照。decision record、review evidence、candidate-path gap、治理文件和本 Gate 证据不纳入素材内容快照。

本 Gate 不冻结 isolated candidate、Runtime、Agent、Host 或真实项目行为；不关闭 T-0036；不创建或执行 T-0037 review；不进入 Host Integration。

## 决策与停止条件

- 批准：只把后续精确版本冻结执行置为可请求状态，不立即生成最终 version-freeze manifest 或冻结记录。
- 拒绝：不执行版本冻结，保持 T-0036 `active`。
- 任一输入发生 path、size 或 SHA-256 漂移：后续执行必须停止并记录 `BLOCKED`，不得静默重建或重定基线。
- 任一路径或效果超出 Gate allowlist：必须停止并记录 `SCOPE_VIOLATION`。

批准短语：`批准 G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`

执行短语：`执行 G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`
