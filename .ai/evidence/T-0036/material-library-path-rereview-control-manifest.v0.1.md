# T-0036 Path-Closure Fresh Rereview Control Manifest v0.1

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-PATH-CLOSURE-REPAIR-V0-1`

Recorded at: `2026-07-24T17:48:00+08:00`

Purpose: freeze the post-path-closure-repair review object and the post-registration governance control plane. This manifest is evidence, not approval, execution, or a rereview verdict.

## Only Rereview Baseline

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-residual-path-repair-freeze-manifest.v0.1.md` | 9835 | `DEF89CBB72A5A910CCC0A8C519F03C2B4E8F1526962B2415DB4DE893DFA13CFC` |

| check | result |
| --- | --- |
| declared subjects | `65` |
| parsed subjects | `65` |
| unique relative paths | `65` |
| path/size/full-SHA-256 matches | `65/65` |
| mismatches | `0` |

No earlier freeze manifest is an alternate baseline for this Gate. Any mismatch or drift before or after future rereview requires `BLOCKED`.

## Repaired Path Precheck

| finding | location | required value | result |
| --- | --- | --- | --- |
| F-003 | P1-P2 `human_decision.evidence_packet` | `materials/material-library-review-packet.md` | PASS, two exact occurrences |
| F-005 | `selected_templates` | `materials/profiles/material-selection-record.yaml` | PASS, one exact occurrence |

The repair validator returned `PASS` with catalog `46`, authority violations `0`, register `46/46`, status conflicts `0`, Markdown IDs `46`, coverage `46/46`, freshness `46/46`, phase-profile reference `1/1`, selection materials `8/17`, and selection templates `7/9`.

## Repair Evidence Fingerprints

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-residual-path-repair-validation.v0.1.md` | 1810 | `ECDFB315B90FFE34035EC4B43C6EB7A6A539493BBC222F992B5764E6F5EE209A` |
| `.ai/evidence/T-0036/material-library-residual-path-repair-changed-path-manifest.v0.1.md` | 3467 | `9DDF542FEB000F7F98388715232604D17B227DC4B7574D323E0357208802DB79` |

These are background evidence only. The future reviewer must independently reconstruct all conclusions.

## Post-Registration Governance Fingerprints

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/gates.yaml` | 345784 | `8A968A7F02B5CD073409FAEEA931B8A6F5E714FC9D4A1C6E53850D98B4286483` |
| `.ai/state.yaml` | 14582 | `F746C3C09F42F70903F5979D3D206E50D81D89AFF92B8C89880D462BBF6CA21E` |
| `.ai/HANDOFF.md` | 21288 | `739861A03C5D27AE7B33621DCADB57667F1FD89FDAF781CCBD098895B5CF2C91` |
| `.ai/tasks/T-0036.md` | 5647 | `27FA02DFEB80BA045F70F6A0F03C41588805281ADEDE521CF9C64C262F23F777` |
| `.ai/task_graph.yaml` | 11490 | `94DC8AD16905EE6CAF2DD2679D764578D3762FADB702F67B89C79D3022C5F278` |

The first three fingerprints are the registration checkpoint before the control and commands evidence files were added; those additive files do not alter governance projections. Future approval may change only the explicitly authorized decision projection and must record that drift.

## Gate Preparation Fingerprints

| path | size | SHA-256 |
| --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-path-rereview-gate-request.v0.1.md` | 6340 | `F9AE9396F733FD7A0D95014745A4CA573ED446B281FFFE0AD86A3BA734F134A8` |
| `.ai/evidence/T-0036/material-library-path-rereview-changed-path-baseline.v0.1.md` | 2132 | `A8CFD4368E86696AB1986BA155D1C64CC2C53B3599DEE5412696BE3894D76BA4` |

The four future rereview output paths were absent at registration and remain unauthorized.

## Independence, Drift, And Scope Rules

- A future reviewer must be a fresh-context independent reviewer subagent uninvolved in earlier repair, review, rereview, coordination, or Gate preparation.
- Before and after future rereview, require the only 65-subject baseline to match `65/65` and this control manifest to remain byte-identical.
- The future verdict is evidence only; it cannot approve, accept, freeze, close, or authorize downstream actions.
- The actual changed set must remain within the exact registration or execution allowlist for the active phase.
- Freeze/control drift returns `BLOCKED`; an unauthorized path or effect returns `SCOPE_VIOLATION`.
- Do not repair findings, modify protected inputs/evidence, auto-delete partial evidence, silently rebaseline, or perform destructive recovery.

## Open Boundaries

- Fresh rereview has not executed.
- Candidate-path verification remains open and is not repaired by this Gate.
- T-0035 is administratively completed only; no product PASS or baseline acceptance is implied.
- The old roadmap is superseded only as governance sequencing; no false remediation-completion claim is allowed.
- Candidate-baseline acceptance, version freeze, T-0036 closeout, T-0037 review, Host Integration, Runtime, Agent, deployment, and real-project entry remain unauthorized.
