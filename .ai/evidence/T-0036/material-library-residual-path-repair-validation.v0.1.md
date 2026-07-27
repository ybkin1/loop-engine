# T-0036 Residual F-003/F-005 Path Repair Validation v0.1

Gate: `G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`

## Exact Repair Assertions

| assertion | result |
| --- | --- |
| old F-003 packet path absent from phase profile | PASS |
| P1-P2 packet path equals `materials/material-library-review-packet.md` | PASS |
| old F-005 template path absent from project profile | PASS |
| replacement path equals `materials/profiles/material-selection-record.yaml` | PASS |
| target YAML parse | PASS |
| material-library repair validator | PASS |

## Resulting Target Fingerprints

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml` | 9786 | `18A8D935ED60878E1F05756A2E58A931CAAD628AFB4851F92A982C72B857DBE7` |
| `.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml` | 2050 | `C6C24678BD879B65562196BC3C286013568B9E24C0B43B214053DC1D0B5C09CC` |

## Validator Output

- `catalog=46`
- `authority_violations=0`
- `register=46/46`
- `status_conflicts=0`
- `markdown_ids=46`
- `coverage=46/46`
- `freshness=46/46`
- `phase_profile_ref=1/1`
- `selection_materials=8/17`
- `selection_templates=7/9`
- result: `PASS`

## Freeze And Governance Checks

- The original 65-subject freeze remains unchanged and is not overwritten. Its expected post-repair mismatches are exactly the two approved YAML targets.
- Original freeze post-repair: exactly 2 expected mismatches, limited to the two approved YAML targets; no other frozen subject drift.
- New residual-path repair freeze: `65/65`, mismatches `0`.
- `validate_state.py`: `PASS` (`state is usable`).
- `audit_handoff.py`: `PASS`.
- `git diff --check`: `PASS`.

No fresh rereview, candidate-baseline acceptance, version freeze, T-0036 closeout, T-0037 review, or Host Integration is included in this validation.
