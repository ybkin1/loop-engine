# T-0036 Repair Commands v0.1

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

The following are execution evidence, not user authority:

- `python C:\Users\Administrator\.codex\skills\project-governor\scripts\validate_state.py C:\Users\Administrator\.codex\loop-engine-lab` -> exit `0`.
- Candidate/protected baseline recomputation -> 43 subjects, 0 SHA-256/size/mtime mismatches.
- Candidate inventory check -> 10 files, 2 directories, 0 reparse, 0 compiled/cache artifacts.
- Recovery preimages copied before candidate writes -> 8 files.

## Preimage Fingerprints

| path | sha256 | size | mtime_ns source |
|---|---|---:|---:|
| `BOUNDARY.md` | `7CB056EEDF1C9DDFEC6A8B1BCCF688B26270E4F6498AAF92F1F6835FBC931DAB` | 4439 | baseline |
| `PROVENANCE.yaml` | `51FC07BC36C044CE5DD443349ABD09708C0B8AF6848766E70582F049D97E0BB2` | 8338 | baseline |
| `scripts/audit_handoff.py` | `30243CED5234ABBC62F2C56ED03B3FCDCE86BA7DE62AA6982831D29E8EDA0D6B` | 2900 | baseline |
| `scripts/close_session.py` | `F22CFB814C43073562B95B96AA385374569E7C2EE5E670711D0C1029AABA0EBD` | 4671 | baseline |
| `scripts/governance_action.py` | `3FCAA031424656F7FAC29BACC61FEC2D4E036A20C5035F9066097D28BB683A1B` | 4379 | baseline |
| `scripts/governor_lib.py` | `94B4FA1E6BED24A4E5083D1FD4008199897EE177368893F04FAAE5FB00FBACEA` | 57743 | baseline |
| `scripts/validate_state.py` | `BF533B91F5B32F1F21986271C8D0FDF678B2E31EBDE4B42F42F02144583B3525` | 2004 | baseline |
| `tests/test_project_governor_consistency.py` | `BB6AE651979E5ADE29FA396A7C4922EE158EFE05E7B16E3C57B1CB5F9251219C` | 38049 | baseline |
