# T-0036 行政收口变更路径清单 v0.1

Gate: `G-T-0036-CLOSEOUT-DECISION-AND-EXECUTION-V0-1`

Execution: `closeout_completed`

本清单记录精确执行请求后的实际写入路径。执行前工作树已存在既有未提交变更；所有既有变更均保留。十条执行路径严格来自 Gate allowlist，未执行删除、reset、checkout 或静默重建。

| path | pre-state | post size / SHA-256 |
| --- | --- | --- |
| `.ai/tasks/T-0036.md` | present | 6879 / `8A9601C9141F9CCA91511B5D5593F68C5093A4E562528C4B9D90C98185B9BFC5` |
| `.ai/task_graph.yaml` | present | 11568 / `03AB232ABEE9B26F8C70C039142244EEDC8ADFC5D3CC8E42F76C12B1A1100B91` |
| `.ai/DECISIONS.md` | present | 13687 / `7871D3F76F8AD3B6671E33523EDB2CED5E09EC188897DDC624A2731F39EAA692` |
| `.ai/PROGRESS.md` | present | 35731 / `1A51A80F54D957B6418B783F6F45D6B941819C73E2D21534D6CF0AE9B243CC48` |
| `.ai/evidence/T-0036/material-library-closeout-record.v0.1.md` | absent | 1518 / `8606F944560D67C7E835563775E3A884370BE36A4BE087A05531E3464B5667F6` |
| `.ai/evidence/T-0036/material-library-closeout-validation.v0.1.md` | absent | 1884 / `8D0ADF6BE7267F018CB0700C46A9B85E5EFDFC03036D1D1FE2E182321E2E5E61` |
| `.ai/evidence/T-0036/material-library-closeout-changed-path-manifest.v0.1.md` | absent | present; self fingerprint intentionally excluded |
| `.ai/gates.yaml` | present | 368243 / `FA6CDCF3AB0860329FCC14CC267F271B8DE8015D4796B171C149A4292BBB094B` |
| `.ai/state.yaml` | present | 18988 / `6C12434D242764EF2C5DA4EEA61E3A7AE67B3F4CFB8516E8121B6FFC2DDF4CC8` |
| `.ai/HANDOFF.md` | present | 23902 / `B0E291AE81AA7C1BCD9E1798210245C8947EA2D71ADF3688AC7CDCBABC1BA74C` |

## Scope Result

Actual execution path count=`10`; Gate execution allowlist count=`10`; outside allowlist=`0`.

T-0036 task and task graph are both `completed`. Baseline acceptance and `research-baseline-v0.1` version-freeze pointers are recorded. `completed` is administrative/candidate-baseline-stage completion only; it is not product PASS, user-project acceptance, Runtime/Agent/Host completion, installation, activation, deployment, or T-0037 review authorization.

## Protected Boundary

- Final version-freeze manifest remains `10202` bytes / SHA-256 `24DDC5434B0FFE3D078AED5B8A2101CF6A0A4C97DF73553E949FB668BDE98F20`.
- Old/new subject triples remain `65/65` identical; disk verification remains `65/65`, zero drift.
- Isolated candidate-path verification remains `open / unwaived`.
- No `materials/**`, frozen subject, old evidence, candidate/global Project Governor, tests, `codex_loop`, Runtime, T-0037, Host Integration, installation, activation, deployment, migration, permission, secret, production-data, or real-project path was changed.

This manifest excludes its own final size and SHA-256 to avoid recursive self-reference.
