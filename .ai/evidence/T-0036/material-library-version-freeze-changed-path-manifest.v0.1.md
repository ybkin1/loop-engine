# T-0036 素材库版本冻结变更路径清单 v0.1

Gate: `G-T-0036-VERSION-FREEZE-RESEARCH-BASELINE-V0-1`

Execution: `version_freeze_completed`

本清单记录精确执行请求后的实际七路径前后指纹。工作树中的其他未提交变更均为既有变更并已保留，不归因于本次版本冻结。

| path | pre-state | pre size / SHA-256 | post size / SHA-256 |
| --- | --- | --- | --- |
| `.ai/evidence/T-0036/material-library-version-freeze-record.v0.1.md` | absent | - | 2061 / `FB092DA2110969070674A69A38FE938C2426AF904423288A285581D0CFD2925C` |
| `.ai/evidence/T-0036/material-library-version-freeze-manifest.v0.1.md` | absent | - | 10202 / `24DDC5434B0FFE3D078AED5B8A2101CF6A0A4C97DF73553E949FB668BDE98F20` |
| `.ai/evidence/T-0036/material-library-version-freeze-validation.v0.1.md` | absent | - | 2694 / `5D207772362ED9A86B5DEBDD6F69CD105E8E08CADB93FA548C1CB9F401ACDC99` |
| `.ai/evidence/T-0036/material-library-version-freeze-changed-path-manifest.v0.1.md` | absent | - | present; self fingerprint intentionally excluded |
| `.ai/gates.yaml` | present | 360019 / `B1764250277E6DB40433E6D3EA6B9EE806C51EAA2186837911A377EF53C53E09` | 361383 / `D2D7416EAA2D29773FB59B512CB2EB3F68C4AE6B6701C89C5C2C11E39EA1DC1D` |
| `.ai/state.yaml` | present | 17123 / `7EE86986F2A81707B9984FC8220311207EFA4219E363A2D37287E5F7309344B8` | 17925 / `0EF608D0F56D25DE5A443A43D6F341E0EE3219076C7B435495FC59506820C3D4` |
| `.ai/HANDOFF.md` | present | 22870 / `9AA8AF13ECE0AB918FFF5092BC36772F5070F7150336D10A23866A20BF7CD48F` | 23201 / `2632A41A23DC0C3AD425D86AD56BAD96BAF3FFC0DF6025B62AB4E512FF1F7780` |

## Allowlist Result

Gate 执行 allowlist count=`7`；实际归属 changed path count=`7`；outside allowlist=`0`。四个新增证据与三个治理投影正好构成完整执行路径集合。

## Protected Boundary

- 旧输入 manifest 保持 `9835` bytes / `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`。
- 65 个素材 subject 保持 `65/65` path、size、SHA-256 匹配，零漂移。
- 新旧 manifest 的 65 组三元组完全一致，differences=`0`。
- 未修改 T-0036 task、task graph、T-0037、候选/global Project Governor、测试、`codex_loop`、Runtime 或其他禁止路径。
- T-0036 保持 active；candidate-path gap 保持 open / unwaived；未创建或执行 T-0037 review，未进入 Host Integration。

本清单排除自身最终 size 和 SHA-256，以避免递归自引用。
