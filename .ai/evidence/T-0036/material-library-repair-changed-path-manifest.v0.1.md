# T-0036 Repair Changed-Path Manifest v0.1

Gate: `G-T-0036-REPAIR-F001-F006-V0-1`
Execution request: `执行 G-T-0036-REPAIR-F001-F006-V0-1`
This manifest records actual repair changes. It excludes its own fingerprint and the post-repair freeze manifest to avoid self-reference.

## Execution result

`scope-contained / repair-evidence-recorded / repair-completed / rereview-not-started`

The pre-registration baseline is `.ai/evidence/T-0036/material-library-repair-changed-path-baseline.v0.1.md`. Existing user changes remain un-attributed. Every changed path below is in the approved execution allowlist.

## Existing paths changed from the pre-registration baseline

| path | before size | before SHA-256 | after size | after SHA-256 | reason |
| --- | ---: | --- | ---: | --- | --- |
| `materials/README.md` | 2983 | `9D8E7BFD1CE594AD4E49BFEFCE901DE098CAE5C9D6A6DBC270B0FFAD5E6EC372` | 3176 | `E647B997894B04A62B12C7B286A7AD54A73A4D4C21A7CECEC7B66433686585BB` | F-002/F-006 canonical register pointer |
| `materials/catalog.yaml` | 53145 | `B8F2675C4C6E1D41BCC67A542304A9DD1C9CE2D7A5DF322C91A849C694D34C7F` | 61396 | `C3A84E6FE21487DDC44923249603AC25EA6C23DC68BE85EDE3EF5764410ABC23` | F-001, F-002, F-006 status/observation projection |
| `materials/source-register.md` | 5760 | `599A96F287CE87CF72A709AE6D853F4FE602B9E154292CC2C750E0E9A91FECBB` | 11814 | `8D80A8036F66D3A9F20009A82121B4588C4E04DE0EDFA542E0D6863EBACC5F6D` | F-002/F-006 human projection |
| `materials/coverage-matrix.md` | 3377 | `D210B5B19B2573A90431C62A20948F9B07CAF7D32762294AA68BFE764B6F18B6` | 3377 | `F837B151A13A3732A82DF3F8C67DACF7957C4F359C4F981B791F3070B98C445A` | F-004 ARCH-004 coverage |
| `materials/profiles/project-profile.yaml` | 826 | `4F3F30BA67E862D2D0F669B634CB62DC07BB0A63BD0909C8319C01E18F6A6B1E` | 1008 | `B5212BA4E8C155C257110B49AE306C794335C2A9E5C5E3B5CB757567DB5EEEA8` | F-005 generic project selection contract |
| `materials/profiles/material-selection-record.yaml` | 829 | `8A45CA458D6CE935253E7F602FBDA373EE9E441F57CAA34825F579557E43FED9` | 1060 | `4E6A52279A834BED05FEF7243859C6DAFEB05A69EBC7E2C2A23E055CDBA17E59` | F-005 generic phase selection contract |
| `materials/templates/phase-profile.yaml` | 734 | `E1E7839FA997066FE4AD64BFDA3BF255427CE99647D8D972FE9E9993703F5A57` | 958 | `B391D6F59B04C754BCFA341CE77AD7905FDF8B5DFE474DB4A06FBCE65831F66D` | F-003 aggregate profile shape |
| `.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml` | 1728 | `03D29A11A9C1C990B778CC1B2B8E6180889C2A3049BA04E05F56C72B0023D33B` | 2051 | `E87BC22D39EE5AA65B6B5580CF0D74A91B274AB67A234294EC19C0AB1B9C3C02` | F-003/F-005 project instance |
| `.ai/evidence/T-0036/simulation/material-selection.v0.1.yaml` | 4518 | `76AD8F9A563E2CFF088DE701AF3084B75F93121F8967B3860266ABD91916CEC2` | 4724 | `C703F2103EEB1D78CF2EA4C8A80A68A4365498CB56296C07CE14DC365FB8C4E7` | F-005 phase selection instance |

## New paths created

| path | before | after size | after SHA-256 | reason |
| --- | --- | ---: | --- |
| `materials/source-register.yaml` | absent | 28885 | `607927ACAA85D7332116A921479D53B269AD1E8868F911BB6B5CDE9D18739345` | F-002/F-006 canonical register |
| `materials/source-register-schema.yaml` | absent | 1370 | `58C02665FBC502313B37F01F2FDDBA549D9B5B155ABF69D5D283D6A4B76177D1` | F-006 constraints |
| `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml` | absent | 9796 | `94F2D296F869A84F7580CB7B8C3F67CA3344D6B1DE686323143AF0067DF583E9` | F-003 concrete aggregate instance |
| `.ai/evidence/T-0036/material-library-repair-validator.v0.1.py` | absent | 8303 | `825B600EC61E6B08E299B7BA127BFFA8C8297A5917139BF724351AF2C8652E1D` | deterministic repair validator |
| `.ai/evidence/T-0036/material-library-repair-commands.v0.1.md` | absent | 3301 | `DA81F031F317C121AFED5AEC9AC773D32E65CE5DFE2144E2F0FD8024E3F5B1F0` | execution commands/evidence |
| `.ai/evidence/T-0036/material-library-repair-validation.v0.1.md` | absent | 2578 | `B22F91FD320D6F4FCECF826CE52BB3EB65D60468904B36CB0A7CBD6EA8D0E5A1` | acceptance and limitation evidence |

The new changed-path manifest and the later post-repair freeze manifest are additive evidence. Their own fingerprints are recorded only after content is final.

## Governance projections

These paths were already modified before this Gate and remain modified after Gate execution; their pre-registration fingerprints are in the baseline. Gate execution only adds approval/execution status and evidence pointers:

- `.ai/gates.yaml`
- `.ai/state.yaml`
- `.ai/HANDOFF.md`

No `.ai/tasks/T-0036.md`, `.ai/task_graph.yaml`, `.ai/DECISIONS.md`, or `materials/material-schema.yaml` change belongs to this execution.

## Old freeze preservation proof

The old 58-input manifest was checked before repair at `58/58` with zero mismatches. After repair, exactly 9 old frozen subjects changed and all 9 are explicitly approved repair paths listed above; the remaining `49/49` old frozen subjects remain byte-for-byte unchanged. No old independent-review report, review command, review validation, old changed-path manifest, or old freeze manifest changed.

## Forbidden effects not observed

No deletion, destructive rollback, T-0037/T-0038 modification, runtime behavior change, Host Integration, baseline acceptance, version freeze, independent rereview, deployment, migration, database, permissions, secrets, payment, production-data, or external business-project action occurred.
