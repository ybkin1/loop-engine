# T-0036 Residual Path Repair Changed-Path Baseline v0.1

Gate: `G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`

Captured: `2026-07-24T17:12:44+08:00`

This pre-registration baseline does not authorize repair. Existing user changes are preserved and are not attributed to this Gate.

## Git Baseline

- Branch: `checkpoint-through-T-0034`
- HEAD: `eb07a30`
- `git status --porcelain=v1 -uall`: 183 lines; staged 0; tracked worktree modifications 9; untracked entries 174.
- The worktree was already dirty across governance, evidence, materials, tests, candidate, docs, and runtime paths. Registration must not revert or claim those changes.

## Registration Path Preimages

| path | before status | before size | before SHA-256 |
| --- | --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-residual-path-repair-gate-request.v0.1.md` | absent | absent | absent |
| `.ai/evidence/T-0036/material-library-residual-path-repair-changed-path-baseline.v0.1.md` | absent | absent | absent |
| `.ai/evidence/T-0036/material-library-residual-path-repair-registration-commands.v0.1.md` | absent | absent | absent |
| `.ai/evidence/T-0036/material-library-residual-path-repair-sidecar-audit.v0.1.md` | absent | absent | absent |
| `.ai/gates.yaml` | tracked, unstaged modified | 331910 | `B368ABA14195BE70A422A1384408787B11AA88C4825F7D95BF04F72B90A34885` |
| `.ai/state.yaml` | tracked, unstaged modified | 13146 | `010B2F856309AF78E9AF285F31B3F17063674B9AE5670653917BFD1C709C64F8` |
| `.ai/HANDOFF.md` | tracked, unstaged modified | 19352 | `B75ACCCF6664670CC0FE6625E6503D7995CAF551BCED4C46BA7954B948D54527` |

## Future Repair Target Preimages

These files remain unchanged during registration.

| path | before size | before SHA-256 | exact future replacement |
| --- | ---: | --- | --- |
| `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml` | 9796 | `94F2D296F869A84F7580CB7B8C3F67CA3344D6B1DE686323143AF0067DF583E9` | P1-P2 packet path only |
| `.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml` | 2051 | `E87BC22D39EE5AA65B6B5580CF0D74A91B274AB67A234294EC19C0AB1B9C3C02` | selected template path only |

## Residual Path Existence Check

| path | exists before registration |
| --- | --- |
| `.ai/evidence/T-0036/material-library-review-packet.md` | no |
| `materials/material-library-review-packet.md` | yes |
| `materials/templates/material-selection-record.yaml` | no |
| `materials/profiles/material-selection-record.yaml` | yes |

## Frozen Baseline

- Existing manifest: `.ai/evidence/T-0036/material-library-repair-freeze-manifest.v0.1.md`
- Manifest size: 10029 bytes
- Manifest SHA-256: `1CE2751794FBF643CD68976A70EFBD31FF6CACD3EECB0F70746BE45F0236783F`
- Parsed subjects: 65; path/size/SHA-256 matches: 65/65; mismatches: 0.

The existing freeze manifest and all 65 subjects remain read-only during registration. Future execution may change only the two explicitly listed YAML subjects after both approval and the later exact execution request, and must create a new freeze manifest rather than rewriting this baseline.
