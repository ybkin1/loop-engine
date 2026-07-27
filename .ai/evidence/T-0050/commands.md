# T-0050 Commands

- config.yaml: expanded decision_recording_exempt to 4 files
- repair_continuity.py: full implementation (was placeholder)
- validate_state.py: added REPAIR_MODE (--repair flag / LOOP_REPAIR_CONTINUITY=1)
- continuity_auditor.py: _approved_gate matches completed/legacy gates
- hook_common.py: added load_gates_full() with execution_status
- task_contract.py: deployed to .zcode/tools/
