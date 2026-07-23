# Commands

```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\init_project.py' 'C:\Users\Administrator\.codex\loop-engine-lab' --title 'Codex 一人研发团队式 Loop 软件交付系统'
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\new_task.py' 'C:\Users\Administrator\.codex\loop-engine-lab' --title '汇总并设计 Loop 工程工作模式与规范架构'
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

## 2026-07-06 Handoff Generation

Read before writing:
- `.ai/state.yaml`
- `.ai/HANDOFF.md`
- `.ai/tasks/T-0001.md`
- `.ai/evidence/T-0001/generic-handoff-spec.candidate.v0.1.md`

Generated:
- `.ai/HANDOFF.md`

Validation:
```powershell
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
& 'C:\Python312\python.exe' 'C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py' 'C:\Users\Administrator\.codex\loop-engine-lab'
```

Results:
- `validate_state.py`: passed.
- `audit_handoff.py`: passed after adding legacy-compatible handoff headings while preserving the candidate spec status boundaries.
- No skill/MCP/agent/protocol was installed.
- No protocol/spec/workflow artifact was marked approved, active, or installed.
