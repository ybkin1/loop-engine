# T-0036 素材库版本冻结验证 v0.1

Gate: `G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`

Version identity: `research-baseline-v0.1`

Result: `PASS / version_freeze_completed`

## Freeze Assertions

| assertion | result | observed |
| --- | --- | --- |
| explicit approval | PASS | `批准 G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1` recorded before execution |
| separate exact execution request | PASS | `执行 G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1` |
| input manifest identity | PASS | `9835` bytes / `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC` |
| pre-execution input disk check | PASS | declared/parsed/unique/matched=`65/65/65/65`; mismatches=`0` |
| final manifest identity | PASS | `10202` bytes / `24DDC5434B0FFE3D078AED5B8A2101CF6A0A4C97DF73553E949FB668BDE98F20` |
| old/new subject triples | PASS | `65/65` identical path、size、SHA-256；differences=`0` |
| post-execution final disk check | PASS | `65/65` matches；mismatches=`0` |
| version identity consistency | PASS | record、manifest、Gate、state、HANDOFF 均为 `research-baseline-v0.1` |
| old manifest preservation | PASS | 仍为 `9835` bytes / `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC` |
| T-0036 status | PASS | `active`；未关闭 |
| isolated candidate-path gap | PASS | `open / unwaived`；未修复、未豁免 |
| T-0037 review | PASS | 未创建或执行 |
| downstream boundary | PASS | 未进入 Host Integration；未冻结 Runtime、Agent、Host 或真实项目行为 |

## Governance Commands

| command | exit | result |
| --- | ---: | --- |
| `validate_state.py` | 0 | `[ok] state is usable` |
| `audit_handoff.py` | 0 | handoff audit passed |
| UTF-8 YAML and Gate assertions | 0 | governance projection PASS |
| `git diff --check` | 0 | no output |

## Changed-Path And Scope Validation

执行前七路径 preimage 已捕获。实际执行只新增四个版本冻结证据并更新 `.ai/gates.yaml`、`.ai/state.yaml`、`.ai/HANDOFF.md`；changed-path manifest 自身排除递归 fingerprint。实际路径正好等于 Gate 的七路径执行 allowlist，越界路径=`0`。

未修改 65 个素材对象、旧 freeze manifest、catalog、register、profiles、templates、既有 review evidence、candidate/global Project Governor、测试、`codex_loop`、Runtime、T-0036 task 或 task graph。未使用 Git tag、commit 或发布动作替代冻结证据。

## Conclusion

已接受的 T-0036 素材库内容快照已被正式记录为不可漂移的 `research-baseline-v0.1`。该结论只覆盖 65 个素材库 subject，不关闭 T-0036，不解决 candidate-path gap，不授权 T-0037 review 或 Host Integration。
