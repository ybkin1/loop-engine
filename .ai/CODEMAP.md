# Codemap

## Important Paths

- `C:\Users\Administrator\.codex\skills\project-governor\scripts\close_session.py`: closeout and HANDOFF generator; currently mutates task graph status.
- `C:\Users\Administrator\.codex\skills\project-governor\scripts\governor_lib.py`: YAML/text I/O, gate/evidence helpers, and task graph update helper.
- `C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py`: shallow governance state validator.
- `C:\Users\Administrator\.codex\skills\project-governor\scripts\audit_handoff.py`: structural HANDOFF auditor.
- `.ai/evidence/T-0029/`: reproduced failure and repair-planning evidence.

## Ownership Boundaries

- Project Governor skill scripts and templates require a separate implementation gate before modification.
- Project-local `.ai/` records may document governance facts but do not install or enable skill/runtime behavior.
