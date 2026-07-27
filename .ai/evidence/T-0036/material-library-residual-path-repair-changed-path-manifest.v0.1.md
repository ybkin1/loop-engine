# T-0036 Residual F-003/F-005 Path Repair Changed-Path Manifest v0.1

Gate: `G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`

Execution request: `执行 G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`

Result: `scope-contained / exact-two-string-replacements / frozen-inputs-preserved / repair-completed`

This manifest excludes its own fingerprint to avoid self-reference.

## Repair Subject Changes

| path | before size | before SHA-256 | after size | after SHA-256 | change |
| --- | ---: | --- | ---: | --- | --- |
| `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml` | 9796 | `94F2D296F869A84F7580CB7B8C3F67CA3344D6B1DE686323143AF0067DF583E9` | 9786 | `18A8D935ED60878E1F05756A2E58A931CAAD628AFB4851F92A982C72B857DBE7` | P1-P2 packet path only |
| `.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml` | 2051 | `E87BC22D39EE5AA65B6B5580CF0D74A91B274AB67A234294EC19C0AB1B9C3C02` | 2050 | `C6C24678BD879B65562196BC3C286013568B9E24C0B43B214053DC1D0B5C09CC` | selected template path only |

## Execution Evidence And Governance Projection Changes

These paths were absent or already modified before execution and are within the approved post-approval allowlist. Governance projections were already dirty from registration/approval; the after fingerprints below include only this execution's bounded status/evidence projection.

| path | before execution status | after size | after SHA-256 |
| --- | --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-residual-path-repair-commands.v0.1.md` | absent | 2619 | `480E8EA1B4FE00A7F3F7C73C5D0B26FAA1BD5BC9C1452C0C15733E3AEBD817D4` |
| `.ai/evidence/T-0036/material-library-residual-path-repair-validation.v0.1.md` | absent | 1810 | `ECDFB315B90FFE34035EC4B43C6EB7A6A539493BBC222F992B5764E6F5EE209A` |
| `.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md` | absent | 9835 | `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC` |
| `.ai/gates.yaml` | present at approved checkpoint | 338986 | `8CF100214F6AA1CF74381A1D4170F47B801F3BF8B0F189A779049DE9A65EE38F8` |
| `.ai/state.yaml` | present at approved checkpoint | 14040 | `9E8B8633487D9E49A0D59760F9E782ADA4E9795472BCE571FAE65B7999C03E6B` |
| `.ai/HANDOFF.md` | present at approved checkpoint | 19874 | `964BB49F9BC68E0B9C052CFB3AFECF75BB5DACCD94AA29039C4897905B7B83BF` |

The fourth additive evidence path is this manifest itself; its fingerprint is intentionally excluded.

## Protected Paths And Scope

- Original `.ai/evidence/T-0036/material-library-repair-freeze-manifest.v0.1.md` remained unchanged.
- Its post-repair comparison reports exactly two expected mismatches, both listed repair subjects; no other frozen subject drifted.
- New `.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md` verifies 65 subjects with 65/65 path, size, and SHA-256 matches.
- Registration evidence, prior review/repair/rereview evidence, materials, tests, candidate, global Project Governor, T-0037/T-0038, `codex_loop`, and runtime paths were not modified by this execution.
- No fresh rereview, candidate-baseline acceptance, version freeze, T-0036 closeout, T-0037 review, Host Integration, installation, activation, deployment, database, permission, secret, payment, production-data, migration, or external-project action occurred.

Scope verdict: `PASS`; actual changed paths are within the exact Gate allowlist, and the repair is limited to the two specified YAML string replacements.
