# T-0034 L0R2 P1 Repair Commands v0.1

- Ran `validate_state.py` before execution: exit 2, only six preserved historical mismatches.
- Recomputed 14/14 frozen subject hashes, 13/13 candidate/global hashes, and 2/2 task/task-graph hashes.
- Reproduced the F001 review result and inspected both conflicting v0.2 schema definitions.
- Used `apply_patch` for every allowed write.
- Ran strict UTF-8/LF/BOM, canonical payload extraction, YAML parse, canonical-owner uniqueness, compatibility/migration, and frozen-hash checks.
- Ran `validate_state.py` and `audit_handoff.py`; both exit 2 with only the six preserved historical mismatches.
