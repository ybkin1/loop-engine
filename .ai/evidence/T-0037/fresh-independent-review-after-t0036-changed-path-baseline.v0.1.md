# T-0037 Fresh Independent Review After T-0036 Changed-Path Baseline v0.1

Recorded at: `2026-07-27T11:36:48+08:00`

Gate: `G-T-0037-FRESH-INDEPENDENT-REVIEW-AFTER-T0036-BASELINE-V0-1`

This byte-level baseline was captured before Gate registration. `absent` means the path did not exist. Existing dirty-worktree changes belong to prior work and must be preserved.

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/evidence/T-0037/fresh-independent-review-after-t0036-gate-request.v0.1.md` | absent | absent |
| `.ai/evidence/T-0037/fresh-independent-review-after-t0036-changed-path-baseline.v0.1.md` | absent | absent |
| `.ai/evidence/T-0037/fresh-independent-review-after-t0036-control-manifest.v0.1.md` | absent | absent |
| `.ai/evidence/T-0037/fresh-independent-review-after-t0036-registration-commands.v0.1.md` | absent | absent |
| `.ai/gates.yaml` | 368243 | `FA6CDCF3AB0860329FCC14CC267F271B8DE8015D4796B171C149A4292BBB094B` |
| `.ai/state.yaml` | 18988 | `6C12434D242764EF2C5DA4EEA61E3A7AE67B3F4CFB8516E8121B6FFC2DDF4CC8` |
| `.ai/HANDOFF.md` | 23902 | `B0E291AE81AA7C1BCD9E1798210245C8947EA2D71ADF3688AC7CDCBABC1BA74C` |

## Startup State

- `current_task_id=T-0036`, `current_gate_id=null`，pending Gate count `0`。
- `validate_state.py`: exit `0`, state usable。
- `audit_handoff.py`: exit `0`, audit passed。
- `git diff --check`: exit `0`, no output。
- T-0036 task/task graph 均为 `completed`。
- T-0036 final manifest 为 `10202` bytes / `24DDC5434B0FFE3D078AED5B8A2101CF6A0A4C97DF73553E949FB668BDE98F20`，65/65 match，mismatch `0`。
- T-0037 control subjects 预检为 `62` 个。
- Startup worktree 已非 clean；本注册仅声明七路径 allowlist 内的变更作者身份。

## Drift Rule

未来批准记录与审查执行必须重检适用的 preimage、T-0037 control manifest 和 T-0036 final manifest。任何无法解释的漂移返回 `BLOCKED`；路径或效果越界返回 `SCOPE_VIOLATION`。不授权自动删除、reset、checkout、破坏性 rollback 或静默重建基线。
