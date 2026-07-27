# T-0036 行政收口 Gate 注册前变更路径基线 v0.1

Gate: `G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`

Captured at: `2026-07-27T10:50:36+08:00`

本基线记录收口 Gate 注册允许路径在写入前的状态。工作树中其他未提交变更均为既有变更并保留，不归因于本 Gate。

| path | pre-state | size | SHA-256 |
| --- | --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-closeout-gate-request.v0.1.md` | absent | - | - |
| `.ai/evidence/T-0036/material-library-closeout-decision-packet.v0.1.md` | absent | - | - |
| `.ai/evidence/T-0036/material-library-closeout-changed-path-baseline.v0.1.md` | absent | - | - |
| `.ai/evidence/T-0036/material-library-closeout-registration-commands.v0.1.md` | absent | - | - |
| `.ai/gates.yaml` | present | 361383 | `D2D7416EAA2D29773FB59B512CB2EB3F68C4AE6B6701C89C5C2C11E39EA1DC1D` |
| `.ai/state.yaml` | present | 17925 | `0EF608D0F56D25DE5A443A43D6F341E0EE3219076C7B435495FC59506820C3D4` |
| `.ai/HANDOFF.md` | present | 23201 | `2632A41A23DC0C3AD425D86AD56BAD96BAF3FFC0DF6025B62AB4E512FF1F7780` |

前置版本基线仍为 `.ai/evidence/T-0036/material-library-version-freeze-manifest.v0.1.md`，`10202` bytes / SHA-256 `24DDC5434B0FFE3D078AED5B8A2101CF6A0A4C97DF73553E949FB668BDE98F20`，65/65 磁盘匹配、零漂移。

本文件只记录可恢复的 preimage 指纹；不执行行政收口、不修改任务状态，也不授权删除、reset、checkout 或重建冻结基线。
