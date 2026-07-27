# T-0036 Fresh Independent Rereview Changed-Path Manifest v0.1

Gate: `G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

Execution request: `执行 G-T-0036-FRESH-INDEPENDENT-REREVIEW-AFTER-REPAIR-V0-1`

Result: `scope-contained / frozen-inputs-preserved / rereview-evidence-recorded / repair-required`

This manifest excludes its own fingerprint to avoid self-reference. The reviewer was a fresh read-only context and created no files; the main controller recorded the evidence within the approved execution allowlist.

## Paths Created By This Execution

| path | before | after size | after SHA-256 |
| --- | --- | ---: | --- |
| `.ai/evidence/T-0036/material-library-fresh-rereview.v0.1.md` | absent | 7068 | `F1191DA068700C9E7489F1F534837CC41BF1FFD3D12BB6338CF83631D47953D5` |
| `.ai/evidence/T-0036/material-library-fresh-rereview-commands.v0.1.md` | absent | 1944 | `CE4DAF5511233E7E71121938B90EF7415602D8F1A18EC1A6EAFD71FDB40B457B` |
| `.ai/evidence/T-0036/material-library-fresh-rereview-validation.v0.1.md` | absent | 2901 | `A76CFD7365F604DD044F6D73470F330BB7F866389709A1F9C33CC3A5877C983F` |

The fourth created path is this manifest itself; its fingerprint is intentionally excluded.

## Governance Paths Updated

These paths were already modified by Gate registration and approval. Their pre-execution fingerprints were captured before rereview evidence recording:

| path | before size | before SHA-256 |
| --- | ---: | --- |
| `.ai/gates.yaml` | 330561 | `76EBE4DF7FC4772331DEE59A882C83AD3BE65FF6D4F6B00E638778A74682814F` |
| `.ai/state.yaml` | 12835 | `13772A5C6E5E6FD467C16F79F55CA2DC381DB572D9D68E1B967E749CC3FE24B4` |
| `.ai/HANDOFF.md` | 19015 | `AC670657DC69422820AD8BA100E034EE123AA50BA64AC6C5CD3244E047992892` |

| post-execution `.ai/gates.yaml` | 331910 | `B368ABA14195BE70A422A1384408787B11AA88C4825F7D95BF04F72B90A34885` |
| post-execution `.ai/state.yaml` | 13146 | `010B2F856309AF78E9AF285F31B3F17063674B9AE5670653917BFD1C709C64F8` |
| post-execution `.ai/HANDOFF.md` | 19352 | `B75ACCCF6664670CC0FE6625E6503D7995CAF551BCED4C46BA7954B948D54527` |

The actual governance projection changed only within the approved execution allowlist.

## Protected Paths

- All 65 frozen subjects and the freeze manifest remained byte-identical.
- The control manifest, original review, repair, full-suite, and reconciliation evidence remained unchanged.
- No materials, candidate, global Project Governor, task graph, T-0036 task, T-0037/T-0038 artifact, skill, MCP, agent, plugin, hook, automation, protocol, runtime, deployment, database, permission, secret, payment, production-data, migration, or external-project path was changed.

## Scope Verdict

The actual review evidence is a strict subset of the Gate execution allowlist. No repair was performed. The evidence-only verdict is `REPAIR_REQUIRED` for residual F-003 and F-005 path/reference closure findings.
