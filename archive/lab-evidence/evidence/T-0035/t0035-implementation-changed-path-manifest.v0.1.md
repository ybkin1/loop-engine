# T-0035 Implementation Changed-Path Manifest v0.1

## Candidate Paths

| Path | Size | SHA-256 |
|---|---:|---|
| `candidates/T-0030-project-governor-repair/BOUNDARY.md` | 4439 | `7CB056EEDF1C9DDFEC6A8B1BCCF688B26270E4F6498AAF92F1F6835FBC931DAB` |
| `candidates/T-0030-project-governor-repair/PROVENANCE.yaml` | 8338 | `51FC07BC36C044CE5DD443349ABD09708C0B8AF6848766E70582F049D97E0BB2` |
| `candidates/T-0030-project-governor-repair/scripts/governor_lib.py` | 57743 | `94B4FA1E6BED24A4E5083D1FD4008199897EE177368893F04FAAE5FB00FBACEA` |
| `candidates/T-0030-project-governor-repair/scripts/governance_action.py` | 4379 | `3FCAA031424656F7FAC29BACC61FEC2D4E036A20C5035F9066097D28BB683A1B` |
| `candidates/T-0030-project-governor-repair/scripts/close_session.py` | 4671 | `F22CFB814C43073562B95B96AA385374569E7C2EE5E670711D0C1029AABA0EBD` |
| `candidates/T-0030-project-governor-repair/scripts/validate_state.py` | 2004 | `BF533B91F5B32F1F21986271C8D0FDF678B2E31EBDE4B42F42F02144583B3525` |
| `candidates/T-0030-project-governor-repair/scripts/audit_handoff.py` | 2900 | `30243CED5234ABBC62F2C56ED03B3FCDCE86BA7DE62AA6982831D29E8EDA0D6B` |
| `candidates/T-0030-project-governor-repair/tests/test_project_governor_consistency.py` | 38049 | `BB6AE651979E5ADE29FA396A7C4922EE158EFE05E7B16E3C57B1CB5F9251219C` |

## Governance And Evidence Paths

- `.ai/tasks/T-0035.md`
- `.ai/task_graph.yaml`
- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`
- `.ai/evidence/T-0035/` exact registration, approval, and execution evidence files listed by the Gate

## Containment

`PASS`: all changed paths are inside the phase-specific T-0035 allowed lists. No global Project Governor file, `AGENTS.md`, protected marker, old task/evidence, downstream task, or real-project path changed.

The final manifest binds candidate target/test/protected fingerprints. Governance closeout files are intentionally written after candidate freeze and are validated separately by global/candidate state and HANDOFF audits.
