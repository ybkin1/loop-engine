# T-0049 Commands Execution Log

## P0 Fixes

### P0-1: repair_continuity.py
- Created `.zcode/tools/repair_continuity.py` — official hash drift repair tool
- Usage: `python .zcode/tools/repair_continuity.py <project_root>`

### P0-2: 扩大 decision_recording_exempt
- `hook_common.py` DEFAULT_CONFIG: added `.ai/state.yaml` and `.ai/task_graph.yaml`
- Prevents fail-closed deadlock when gate is missing/rejected

### P0-3: 统一 gate_id→id + EnforcementLevel
- `state_machine.py` init_project(): `gate_id` → `id` (matching all consumers)
- `enforcement.py`: Unified `EnforcementLevel` with HARD/STRONG + PARTIAL/MEDIUM + ADVISORY
- `enforcement_hub.py`: Removed duplicate enum, imports from enforcement.py

## Test Results

```
pytest --tb=line -q
2276 passed, 1 failed (pre-existing lab test), 61 skipped
```
