# Changed-Path Baseline v0.1

Task: T-0014
Captured at: 2026-07-08T15:01:30+08:00

## Baseline Method

This workspace is not a git repository. Baseline evidence therefore uses path existence, file length, last-write time, and SHA256 where available.

## Target And Governance Paths

| Kind | Path | Exists Before T-0014 Writes | Length | Last Write Time | SHA256 |
| --- | --- | --- | --- | --- | --- |
| future target | `AGENTS.md` | true | 1574 | 2026-07-07T10:43:16.1314406+08:00 | DE7270D5793EFDBAC0B0EC4CCF8BD4A5ADEA721029F9940408585BA6D0B69C87 |
| task | `.ai/tasks/T-0014.md` | false | n/a | n/a | n/a |
| evidence dir | `.ai/evidence/T-0014` | false | n/a | n/a | n/a |
| governance | `.ai/state.yaml` | true | 217 | 2026-07-08T14:25:49.9587580+08:00 | E2FC1961059951C81224AE5BA7069E19D8C2D50BB229886B596FD60757CE77E5 |
| governance | `.ai/gates.yaml` | true | 38069 | 2026-07-08T14:28:14.3971841+08:00 | 40AA38C19539D4F695FB78B49853146C52FF751C063EB21DCC1092CD55DB17C0 |
| governance | `.ai/task_graph.yaml` | true | 3137 | 2026-07-08T14:25:49.9597584+08:00 | 0700B61CC0604EB9F632377A8DE6C37277D3CD4AFFBC0B44A6735947861EF9EF |
| governance | `.ai/PROGRESS.md` | true | 9223 | 2026-07-08T14:28:14.3991842+08:00 | FBAE2D269C2F902507A998C7D99BBC7CA884415146CB0EAF68B1D064C5AD0449 |
| governance | `.ai/HANDOFF.md` | true | 7034 | 2026-07-08T14:28:14.4001844+08:00 | FF679B6F8A6DD3BB77F7B06A17EF0F4726A232977156542A182C8F43419865CD |

## Git Baseline

Commands:

```powershell
git status --short
git log -1 --oneline
```

Result:

```text
fatal: not a git repository (or any of the parent directories): .git
fatal: not a git repository (or any of the parent directories): .git
```

## T-0014 Change Boundary

T-0014 may create or update only:

```text
.ai/tasks/T-0014.md
.ai/evidence/T-0014/
.ai/state.yaml
.ai/gates.yaml
.ai/task_graph.yaml
.ai/PROGRESS.md
.ai/HANDOFF.md
```

T-0014 must not modify:

```text
AGENTS.md
```

The future installation target is `AGENTS.md` only, but the proposed change is evidence only during T-0014.
