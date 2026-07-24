# T-0036 Registration Changed-path Baseline v0.1

Captured before T-0036 registration writes on `2026-07-18`.

## Existing Registration Targets

| Path | Size | SHA-256 | mtime_ns |
|---|---:|---|---:|
| `.ai/state.yaml` | 8775 | `8F301E820CFC56E69521F48A69BE51BA4C710C051119874DF4569F716B360D42` | 1784365949531713800 |
| `.ai/HANDOFF.md` | 11057 | `5620CAE52FB8B661F470FCA305400B3A98C0108B6F16682FB6726F2A10CB1DBC` | 1784366152420580700 |
| `.ai/gates.yaml` | 283530 | `350671917D1402B0788F167178473C4EEA0811B54D5E463A7CE7A9D853810E8A` | 1784365859727940700 |
| `.ai/task_graph.yaml` | 10698 | `5CAAB140DBC12A0A83520132ADD759DFB74BF88C834D6C910AD54B7D827EFC36` | 1784365859725943900 |

## Absent New Targets

- `.ai/tasks/T-0036.md`: absent.
- `.ai/evidence/T-0036/`: absent.
- No T-0036 Gate record or task_graph node existed.
- `gates.yaml` contained 56 unique Gate IDs and zero pending Gates.

## Startup State

- `state.current_task_id`: `T-0035`.
- `state.current_gate_id`: `null`.
- T-0035 task and task_graph status: `completed`.
- T-0035 Gate `execution_status`: `implementation_completed_pending_independent_review`.
- Global `validate_state.py`: exit code `0`, `[ok] state is usable`.

## Git Baseline

Pre-existing changed paths belonged to T-0035 and were preserved:

- `.ai/HANDOFF.md`, `.ai/gates.yaml`, `.ai/state.yaml`, `.ai/task_graph.yaml`.
- `.ai/evidence/T-0035/`, `.ai/tasks/T-0035.md`.
- Eight T-0035 candidate implementation paths.

No pre-existing T-0036 path was present. Registration containment is evaluated as the delta from this baseline, not against a clean worktree assumption.
