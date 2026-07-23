# T-0034 L0R3 Retry1 P1 Repair Commands v0.1

- Read `$project-governor` instructions, `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/tasks/T-0034.md`, `.ai/gates.yaml`, and `.ai/task_graph.yaml`.
- Ran `validate_state.py` before execution: exit 1, only the six preserved historical mismatches.
- Read the Gate request, freeze manifest, retry rereview report, retry validation, and v0.3 repair subjects.
- Recomputed the 17 protected retry repair baseline sizes and SHA-256 values before repair; all matched the freeze manifest.
- Confirmed no existing `*v0.4*` repair artifacts were present before execution.
- Used `apply_patch` for all writes.
- Added exactly three v0.4 repair artifacts and six v0.4 execution evidence files under `.ai/evidence/T-0034/`.
- Updated only `.ai/gates.yaml`, `.ai/state.yaml`, and `.ai/HANDOFF.md` as governance projections.
- Ran local v0.4 checks for strict UTF-8/no BOM/no CR, hash-framing vectors, F001 marker cardinality behavior, F002 required/default behavior, and protected baseline hashes.
- Ran final `validate_state.py` and `audit_handoff.py` after projection; final outputs are recorded in `t0034-l0r3-retry1-p1-repair-validation.v0.1.md`.
