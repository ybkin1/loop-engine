# Commands For T-0035

## Registration Startup And Source Analysis

- Read `$project-governor` and `api-and-interface-design` instructions.
- Read `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/tasks/T-0034.md`, all of `.ai/gates.yaml`, and all of `.ai/task_graph.yaml`.
- Ran `python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`; result before registration: exit code `0`, state usable.
- Parsed all Gate and task-graph records with PyYAML; result: no pending Gate and no T-0035 record.
- Read the T-0030 implementation scope/tests/evidence, T-0031 findings/repair plan, T-0033 decision packet/PROVENANCE/BOUNDARY, T-0034 downstream plan/canonical requirements/additive repair/review/freeze/closeout chain.
- Read all current candidate files and global `C:\Users\Administrator\.codex\skills\project-governor\scripts\new_task.py`.
- Captured Git, registration-path, candidate, boundary-marker, and global Project Governor SHA-256/mtime baselines.

## Planned Registration Validation Commands

```powershell
python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab
python C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab
git status --short
git diff --name-only
```

The expected validator and audit result after registration is a nonzero pending-Gate blocker naming only the T-0035 Gate, with no additional warning/error.
