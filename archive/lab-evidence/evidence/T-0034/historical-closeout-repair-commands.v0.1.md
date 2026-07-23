# Historical Closeout Repair Commands

## Startup And Discovery

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
```

Startup result before repair: only the known historical task status mismatches were reported.

```powershell
Get-ChildItem .ai\tasks\T-*.md
```

Used to enumerate task files and identify task-file statuses.

```powershell
Get-Content -Raw .ai\task_graph.yaml
```

Used to compare task graph statuses with task-file statuses.

## Repair

Manual edits were applied with `apply_patch` only.

Changed task files:

- `.ai/tasks/T-0001.md`
- `.ai/tasks/T-0002.md`
- `.ai/tasks/T-0003.md`
- `.ai/tasks/T-0004.md`
- `.ai/tasks/T-0005.md`
- `.ai/tasks/T-0006.md`
- `.ai/tasks/T-0007.md`
- `.ai/tasks/T-0008.md`
- `.ai/tasks/T-0009.md`

Changed governance memory:

- `.ai/task_graph.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`
- `.ai/PROGRESS.md`
- `.ai/KNOWN_ISSUES.md`
- `.ai/DECISIONS.md`
- `.ai/gates.yaml`

Added evidence files under `.ai/evidence/T-0034/`.

