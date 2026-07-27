# T-0036 候选素材基线决策变更路径清单 v0.1

Gate: `G-T-0036-CANDIDATE-BASELINE-DECISION-V0-1`

Decision: `accepted_candidate_baseline`

本清单记录用户明确接受后实际允许路径的前后指纹。工作树中的其他未提交变更均为既有变更并已保留，不归因于本次决策。

| path | pre-state | pre size / SHA-256 | post size / SHA-256 |
| --- | --- | --- | --- |
| `.ai/evidence/T-0036/material-library-candidate-baseline-decision-record.v0.1.md` | absent | - | 1474 / `4231D3B2F75B53D926A8D85F8DC363C8A60E1790D47D46ABDB8A080B0B781254` |
| `.ai/evidence/T-0036/material-library-candidate-baseline-decision-validation.v0.1.md` | absent | - | 1756 / `EB5DA88928824790D8F0FD60B405873D7F59E931526FAFAD20D7232F7AE48EDB` |
| `.ai/evidence/T-0036/material-library-candidate-baseline-decision-changed-path-manifest.v0.1.md` | absent | - | present; self fingerprint intentionally excluded |
| `.ai/gates.yaml` | present | 352809 / `3F253C5A8859686834C9E905B9E4E6F11120AAF291A1413E1C73BE94DF6E91E5` | 353663 / `334FC0BBA473680873CF4A58D6FB11DF99EC4761BB41BF3E5EB7FB0FEE7FBA21` |
| `.ai/state.yaml` | present | 16112 / `C18ECB47926AAFDCDF31FFE9CB28A169A5B40F78F3F5C942A3A58BCE647D7FBF` | 16133 / `32725D9101E4DA9004B695DDE0837DD6F51BED8E9DBA65A4BB0EE4B7D010AA28` |
| `.ai/HANDOFF.md` | present | 22388 / `9C0EF7E484123F55225A7ACC79C5C9FDC051D0EFEF2D9898A3484F948085C4B9` | 21877 / `D1006CA3004FC390E10EBD2B71ACFE9668F3F8EDB4C208A851C76D0DF601C337` |

## Protected Boundary

The 65-subject freeze manifest and every frozen subject remained unchanged: `65/65`, zero path/size/SHA-256 mismatches; manifest SHA-256 remains `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC`.

No material content, prior review evidence, candidate/global Project Governor, tests, `codex_loop`, Runtime, T-0036 task, task graph, T-0037 review, version freeze, Host Integration, installation, activation, deployment, migration, permission, secret, production-data, or real-project path was changed by this decision.

This manifest excludes its own final size and SHA-256 to avoid recursive self-reference.
