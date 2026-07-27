# T-0036 Fresh Independent Rereview Control Manifest v0.1

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

Recorded at: `2026-07-24T15:56:12+08:00`

Purpose: freeze the post-repair review object and the post-registration governance control plane. This manifest is evidence, not a rereview verdict or user approval.

## 65-Subject Freeze Result

| check | result |
| --- | --- |
| declared subjects | `65` |
| parsed subjects | `65` |
| unique relative paths | `65` |
| path/size/full-SHA-256 matches | `65/65` |
| mismatches | `0` |
| freeze manifest ASCII `?` count | `0` |

Any mismatch before or after future rereview requires `BLOCKED`. The 65 subjects and the freeze manifest are read-only.

## Frozen Baseline And Background Fingerprints

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-repair-freeze-manifest.v0.1.md` | 10029 | `1CE2751794FBF643CD68976A70EFBD31FF6CACD3EECB0F70746BE45F0236783F` |
| `.ai/evidence/T-0036/material-library-independent-review.v0.1.md` | 8639 | `805441888530854A04AE6E228B0BACC83A5184945F59FC2CE80EB10E81234186` |
| `.ai/evidence/T-0036/material-library-repair-validation.v0.1.md` | 2578 | `B22F91FD320D6F4FCECF826CE52BB3EB65D60468904B36CB0A7CBD6EA8D0E5A1` |
| `.ai/evidence/T-0036/material-library-repair-commands.v0.1.md` | 3301 | `DA81F031F317C121AFED5AEC9AC773D32E65CE5DFE2144E2F0FD8024E3F5B1F0` |
| `.ai/evidence/T-0036/material-library-repair-changed-path-manifest.v0.1.md` | 5414 | `841BC3561390E451B4977A936D771C1C1F7667774732045D5D0E3FE8D6E06611` |
| `.ai/evidence/T-0036/continuity-legacy-reconciliation-validation.v0.1.md` | 5791 | `4CFBBD78EDA89EDA67E6059DAC2559688F128D46D15EF0BE142CC160F6880D35` |

These files may inform the future rereview but may not be treated as `PASS` and may not be modified.

## Post-Registration Governance Control Fingerprints

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/state.yaml` | 12624 | `6DB6E7A534F6DD942F611D41A338D0D1B943EFF0E3BA1C3C0099E522C0CD1BB6` |
| `.ai/tasks/T-0036.md` | 5647 | `27FA02DFEB80BA045F70F6A0F03C41588805281ADEDE521CF9C64C262F23F777` |
| `.ai/gates.yaml` | 330244 | `61B0A1A0EDCF64009912D9CFC9A9F4CEE8B5AC37C590160907805B87082EC655` |
| `.ai/task_graph.yaml` | 11490 | `94DC8AD16905EE6CAF2DD2679D764578D3762FADB702F67B89C79D3022C5F278` |
| `.ai/HANDOFF.md` | 19016 | `E4D97453668ED08E8940BDFCEAB3DD949EFF30E15DCBA88C3C8AD265E5FDD982` |

The governance fingerprints are the registration checkpoint. A later explicit approval may change only the authorized approval projection and must record that drift. Future rereview must compare against the approved control checkpoint before execution and must not silently rebaseline.

## Gate Preparation Fingerprints

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-fresh-rereview-gate-request.v0.1.md` | 7742 | `0432EA85A607904A74DD9456AE5C854FD12EBBF72B832DAE80C7EA6B6E304032` |
| `.ai/evidence/T-0036/material-library-fresh-rereview-changed-path-baseline.v0.1.md` | 2331 | `9BFEC2DBAD44BBE0BD5E6E2AA714731E12E77CDB8135C096F357C4A0347A0EB4` |

The approval record is absent by design. It may be created only after the user says the exact approval phrase.

## Known Excluded Gap

The isolated-candidate verification gap remains open: existing global and repository test passes do not prove the isolated candidate path. This gap is known but is not part of the T-0036 material-library rereview verdict and must not be repaired or folded into that verdict.

## Drift And Scope Rules

- Before and after future rereview, require the 65-subject freeze to match `65/65` and this control manifest to remain byte-identical.
- The future actual changed set must be a strict subset of the seven-path execution allowlist in the Gate request.
- Freeze drift returns `BLOCKED`; an unauthorized path or effect returns `SCOPE_VIOLATION`.
- Do not modify findings during rereview, auto-delete partial evidence, or perform destructive recovery.
