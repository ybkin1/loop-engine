# T-0036 Fresh Independent Rereview Gate Approval Record v0.1

Gate ID: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

Decision: `approved`

Approval actor: `user`

Approval source: `explicit_user_message`

Approval text: `批准 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

Approved at: `2026-07-24T16:12:13+08:00`

## Boundary

This record approves only the previously registered Gate for a future fresh, independent, read-only rereview of the repaired T-0036 material-library candidate.

It does not execute rereview. Execution still requires the later exact phrase:

`执行 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

This approval does not authorize repair, candidate-baseline acceptance, version freeze, T-0036 closeout, T-0037 review, Codex Host Integration, or any installation, activation, runtime, production, database, permission, secret, payment, migration, or external-project action.

The 65 frozen subjects, freeze manifest, control manifest, and all prior evidence remain read-only. `rereview_authorized` remains `false` until the later exact execution request is received.

Current status: `approved / approved_not_started / rereview_execution_not_authorized`

## Approval Projection Drift Record

The approval transition changed only the authorized governance projections and this additive approval record. The frozen review object and control manifest remain unchanged.

| path | size after approval | SHA-256 after approval |
| --- | ---: | --- |
| `.ai/state.yaml` | 12835 | `13772A5C6E5E6FD467C16F79F55CA2DC381DB572D9D68E1B967E749CC3FE24B4` |
| `.ai/gates.yaml` | 330561 | `76EBE4DF7FC4772331DEE59A882C83AD3BE65FF6D4F6B00E638778A74682814F` |
| `.ai/HANDOFF.md` | 19015 | `AC670657DC69422820AD8BA100E034EE123AA50BA64AC6C5CD3244E047992892` |

Post-approval freeze verification remains `65/65`; the freeze manifest remains `10029` bytes with SHA-256 `1CE2751794FBF643CD68976A70EFBD31FF6CACD3EECB0F70746BE45F0236783F` and ASCII `?` count `0`.
