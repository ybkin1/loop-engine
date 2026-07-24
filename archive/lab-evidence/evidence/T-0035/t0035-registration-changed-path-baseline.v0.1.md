# T-0035 Registration Changed-Path Baseline v0.1

Captured: `2026-07-18T15:20:38.7983203+08:00`

Git baseline: branch `main`, clean worktree, checkpoint commit `f95cca5 chore: checkpoint through T-0034`.

| Registration path | Pre-registration state | Size | Last write time | SHA-256 |
|---|---|---:|---|---|
| `.ai/tasks/T-0035.md` | absent | n/a | n/a | n/a |
| `.ai/evidence/T-0035/` | absent | n/a | n/a | n/a |
| `.ai/task_graph.yaml` | present | 10218 | `2026-07-17T16:48:02.8036328+08:00` | `F58EB1CE27BFF29DBC29C02FD0EBAD30468D6501EE733BB5DECB71287616ED3E` |
| `.ai/gates.yaml` | present | 271656 | `2026-07-17T16:55:50.9459086+08:00` | `EA536B4835D0347E82BFCBDB913CD140C63BA437E72EB17BC510BEFD4E4C4DFD` |
| `.ai/state.yaml` | present | 7929 | `2026-07-17T17:49:26.5556933+08:00` | `F28E616721E8BDD2137BFEBE2C652C593AEEB719A621FF3F5C26EC796A083491` |
| `.ai/HANDOFF.md` | present | 7982 | `2026-07-18T15:15:18.8032326+08:00` | `4A464450C8638F9D7AE9879B806A7A226DE706C1D8F2B5EBBD89DF1577CBE344` |

Preconditions verified:

- `T-0034` task and task graph status are `completed`.
- `current_gate_id: null`; no Gate has `status: pending`.
- No T-0035 task file, evidence directory, Gate record, or task-graph node exists.
- `validate_state.py` passed cleanly.

Registration writes are limited to the five governance paths above and the eight exact evidence files named by this package.
