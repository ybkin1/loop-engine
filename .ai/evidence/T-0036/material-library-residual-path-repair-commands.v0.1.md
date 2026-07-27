# T-0036 Residual F-003/F-005 Path Repair Execution Commands v0.1

Gate: `G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`

Project root: `C:\Users\Administrator\.codex\loop-engine-lab`

Execution request: `执行 G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`

Execution mode: `bounded_exact_two_string_replacements`

## Startup And Preflight

- Read `$project-governor`, `.ai/state.yaml`, `.ai/HANDOFF.md`, `.ai/tasks/T-0036.md`, `.ai/gates.yaml`, `.ai/task_graph.yaml`, the Gate request, and the changed-path baseline.
- `validate_state.py` before execution: `PASS`; Gate was `approved / approved_not_started`.
- Existing freeze preflight: `65/65` path, size, and SHA-256 matches; manifest size `10029`; SHA-256 `1CE2751794FBF643CD68976A70EFBD31FF6CACD3EECB0F70746BE45F0236783F`.
- Target preimages:
  - `phase-profile.v0.1.yaml`: 9796 bytes; SHA-256 `94F2D296F869A84F7580CB7B8C3F67CA3344D6B1DE686323143AF0067DF583E9`.
  - `project-profile.v0.1.yaml`: 2051 bytes; SHA-256 `E87BC22D39EE5AA65B6B5580CF0D74A91B274AB67A234294EC19C0AB1B9C3C02`.
- Old F-003 and F-005 strings each occurred exactly once; their correct target paths existed.

## Exact Changes Performed

1. In `phase-profile.v0.1.yaml`, changed P1-P2 `human_decision.evidence_packet` from `.ai/evidence/T-0036/material-library-review-packet.md` to `materials/material-library-review-packet.md`.
2. In `project-profile.v0.1.yaml`, changed one `selected_templates` item from `materials/templates/material-selection-record.yaml` to `materials/profiles/material-selection-record.yaml`.

No other content, ordering, formatting, material, test, runtime, or governance file was changed as part of the two YAML replacements.

## Immediate Checks

- Target YAML parse: `PASS`.
- P1-P2 packet path exists and equals `materials/material-library-review-packet.md`: `PASS`.
- All 9 selected template paths exist; obsolete path absent: `PASS`.
- Existing repair validator: `PASS` (`catalog=46`, `register=46/46`, `coverage=46/46`, `freshness=46/46`, `phase_profile_ref=1/1`, `selection_materials=8/17`, `selection_templates=7/9`).

## Required Closeout Checks

- Record old-freeze post-repair mismatches only as the two approved target replacements.
- Old freeze post-repair: 65 records; exactly 2 expected mismatches, both approved YAML targets.
- New residual-path repair freeze: `65/65`; mismatches `0`.
- `validate_state.py`: `PASS`.
- `audit_handoff.py`: `PASS`.
- `git diff --check`: `PASS`.
- Stop immediately after bounded validation and governance closeout. Do not run fresh rereview, candidate-baseline acceptance, version freeze, T-0037 review, or Host Integration.
