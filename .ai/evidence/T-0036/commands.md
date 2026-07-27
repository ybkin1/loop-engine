# Commands For T-0036

## Startup

- `python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab`
- Result: passed before research; no pending gate.

## Research

- `Invoke-WebRequest` HEAD/GET against the sources listed in `materials/source-register.md`.
- Result: status and final URL recorded; inaccessible sources remain explicitly flagged.

## Structure

- Python/PyYAML parse of every `materials/**/*.yaml`.
- Required-field check against `materials/material-schema.yaml`.
- Local-source existence check for `loop_adaptation` materials.
- Result: `parsed_yaml=13`, `catalog_materials=46`, `templates=28`, `yaml_and_catalog_checks=PASS`.

## Governance closeout checkpoint

- `python .../close_session.py ... --note 'T-0036 素材库研究基线已建立...'`
- Result: handoff regenerated for current task `T-0036`.
- `python .../audit_handoff.py C:\Users\Administrator\.codex\loop-engine-lab`
- Result: `handoff audit passed`.
- Final `validate_state.py`: passed; no pending Gate.
- `git diff --check`: passed.

## Loop simulation

- Python/PyYAML validation of simulation YAML, material IDs, task dependencies, role owners and critical path.
- Result: `simulation_yaml=5`, `roles=12`, `tasks=20`, `selected_materials=8`, `simulation_structure_and_dependency_check=PASS`.
- `validate_state.py`: passed after simulation artifacts.
- `git diff --check`: passed after simulation artifacts.

## Approved completion-package execution

- Gate: `G-T-0036-COMPLETE-MATERIAL-LIBRARY-REVIEW-PACKET-V0-1`
- User execution request: `执行 G-T-0036-COMPLETE-MATERIAL-LIBRARY-REVIEW-PACKET-V0-1`
- Action: generate `materials/material-library-review-packet.md` and `materials/coverage-duplication-review.md`; record validation and changed-path evidence.
- Catalog/schema parse: `PASS`; `material_count=46`; required fields `46/46`.
- Exact duplicate checks: material IDs `0`, titles `0`, source URLs `0`, four descriptive fields `0`.
- Similarity check: normalized `problem_solved + adaptation_notes`, threshold `0.72`, pairs `0`.
- Reference check: `67` references, `29` unique paths, missing paths `0`.
- Inventory: templates `28`, frameworks `3`, profiles `2`.
- Review packet and coverage/duplication report required-section checks: `PASS`.
- `git diff --check`: `PASS`.
- Protected T-0036 source/catalog/template/evidence inputs and all T-0037 implementation/evidence paths were not modified.
- Execution status: completion package complete; independent review, repair, rereview, candidate baseline decision and version freeze remain separate.
