# T-0036 素材库版本冻结记录 v0.1

Gate: `G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`

Execution request: `执行 G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`

Execution status: `version_freeze_completed`

Version identity: `research-baseline-v0.1`

Executed at: `2026-07-27T10:38:54+08:00` to `2026-07-27T10:41:22+08:00`

## Frozen Content Snapshot

已将用户接受的 T-0036 素材库内容快照正式记录为不可漂移的 `research-baseline-v0.1`。

- 唯一输入 manifest：`.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md`
- 输入 fingerprint：`9835` bytes / `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`
- 最终 version-freeze manifest：`.ai/evidence/T-0036/material-library-version-freeze-manifest.v0.1.md`
- 最终 manifest fingerprint：`10202` bytes / `24DDC5434B0FFE3D078AED5B8A2101CF6A0A4C97DF73553E949FB668BDE98F20`
- 旧/新 manifest subject triples：`65/65` 完全一致；path、size、SHA-256 差异=`0`
- 最终 manifest 对磁盘验证：`65/65` 匹配；mismatches=`0`

旧 freeze manifest 保持只读且未被覆盖。版本冻结以最终 record、manifest、validation 和 changed-path manifest 为证据；未使用 Git tag、commit 或发布动作替代证据。

## Snapshot Boundary

- 本版本只冻结 65 个已接受的素材库 subject。
- decision record、review/rereview evidence、candidate-path gap、治理文件和 Gate 证据不纳入素材内容快照。
- isolated candidate-path verification gap 仍为 `open / unwaived`，未被本次冻结修复或豁免。
- isolated candidate、Runtime、Agent、Host 和真实项目行为未被冻结。
- T-0036 保持 `active`；本次不关闭 T-0036。
- 本次不创建或执行 T-0037 review，不进入 Host Integration。
- 本次不修改素材对象、catalog、register、profiles、templates、既有 review evidence、candidate/global Project Governor、测试、`codex_loop` 或 Runtime。

本记录只陈述已执行的素材内容版本冻结，不扩大任何下游授权。
