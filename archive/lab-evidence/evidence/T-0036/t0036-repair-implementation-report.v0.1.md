# T-0036 Repair Implementation Report v0.1

Completed: `2026-07-20T15:28:40.9738138+08:00`

Gate: `G-T-0036-REPAIR-INDEPENDENT-REVIEW-FINDINGS-V0-1`

Result: `REPAIR_IMPLEMENTED_PENDING_FRESH_INDEPENDENT_REREVIEW`

## Finding Results

| Finding | Repair result | Evidence |
|---|---|---|
| T0036-F001 | PASS_SECURITY_CONTAINMENT | Inline authority/evidence interfaces removed; production transition returns `USER_DECISION_REQUIRED`; fixture `AuthorityEvent/v2` binds content hash and identity fields. |
| T0036-F002 | PASS_SECURITY_CONTAINMENT | Three production subprocesses cannot advance lifecycle; fixture lineage enforces predecessor, revision CAS, replay prevention, and strictly later turn. Production authority remains unavailable. |
| T0036-F003 | PASS | Controlled runner executes Gate argv with `shell=False`; binds environment/output/exit/test/time/manifest/pre-post fingerprints; fake success cannot override failure. |
| T0036-F004 | PASS | HANDOFF orientation is generated from ProjectContinuity/v1; missing/drifted continuity preserves old HANDOFF and fails closed. |
| T0036-F005 | PASS | `current_gate_id` copies state exactly; approved execution Gate has a separate structured field; independent auditor catches mutation. |
| T0036-F006 | PASS | Lifecycle `verified/unverified/not_performed/not_authorized` comes from structured state and Gate flags; no TBD scan. |
| T0036-F007 | PASS_FIXTURE_ONLY | Registry/quiescence/fence/evidence/ack checks gate checkpoint status. Fixture ack yields only `STABLE_FIXTURE_ONLY`; live production Stable remains unavailable. |
| T0036-F008 | PASS_STRUCTURAL | Six ownership modules added; `governor_lib.py` reduced to common primitives; auditor independently reconstructs expected state and does not import producer. |
| T0036-F009 | PASS | Closed EvidenceManifest/v1 with 256/16MiB/256MiB caps, 1MiB streaming, traversal/ADS/collision/reparse/identity-drift rejection. |

## Capability Classification

- Security containment: `PASS`.
- Production authority lifecycle: `BLOCKED / UNAVAILABLE`.
- Structured continuity/HANDOFF/lifecycle/checkpoint/controlled-validation fixture usability: `PASS`.
- Production Stable checkpoint: `BLOCKED / NOT PROVISIONED`.
- Installation eligibility: `BLOCKED`.

## Verification

- RED: 37 tests, 28 historical regressions passed, 9 repair assertions failed as expected.
- GREEN controlled final validation: 58 tests, exit `0`, status `bound`.
- `E2E-CURRENT-001`: `PASS_FIXTURE_ONLY` with real candidate subprocesses.
- Candidate final inventory: 16 files, 2 directories, 0 reparse, 0 compiled/cache.
- Protected baseline: 33 subjects, zero drift; runner pre/post also identical.
- Global validator and HANDOFF audit: exit `0`.
- Candidate live validator: expected fail closed on absent ProjectContinuity/v1.

## Final Candidate Fingerprints

| path | sha256 | size | mtime_ns |
|---|---|---:|---:|
| `BOUNDARY.md` | `009E749624A28BE4D7994D6AE64AFDCA06E3EA1AC7E571138056996B56DAE980` | 6827 | 1784531552502964500 |
| `NOT_ACTIVATED` | `9BBB093D9C5E6129B1CE440575E9D289366FCDC7223C944532376D0C2E033EAE` | 178 | 1784087348183686900 |
| `NOT_INSTALLED` | `CA19715176E4FD328515F5ECD36D1EB7B91AF7C70BC767C3F61EF9A52B2AB7E5` | 187 | 1784087348182704400 |
| `PROVENANCE.yaml` | `C32D077B0D80F368872DA5A729110D58C4200D40EF8E42D91D7C78A2388CF39F` | 12314 | 1784531808497949500 |
| `scripts/audit_handoff.py` | `7B39A404CD62F34F8D9932DAA1BAF5C04AB9292ED164C46404F216891C9132C7` | 1319 | 1784528061169364700 |
| `scripts/authority_records.py` | `C86E46645126B81E0BF69001493F6BE0593CBB64823AB012D09224556873CBB7` | 4491 | 1784530894270574800 |
| `scripts/close_session.py` | `C9D51DDE316FE834A66DF9887DAE5CBA98F44148A6568F14B5FF75CCB701CDB9` | 1333 | 1784528061163369000 |
| `scripts/continuity_auditor.py` | `F602700CF412D2D46AF94CF991B7A25D8A9AB6F51D7A1C4CE107DA8AA86BCB68` | 11650 | 1784529925029728000 |
| `scripts/continuity_producer.py` | `1E93F70AE7C8DABA33F7ED030972DFB02EB073AAF5A4054EADD90E9D931D1D17` | 12144 | 1784527871745791700 |
| `scripts/evidence_manifest.py` | `419CC01BE9BC4B9117C67CE75D13C6DD43860A27036ECCB0D31687E2C40EF7DD` | 9129 | 1784527469828371400 |
| `scripts/governance_action.py` | `4D2DA44D3FAA9A2D5FB35CA2E6BBA703E128D3DEE6A91B218FE08AA63F595206` | 1662 | 1784527304992011100 |
| `scripts/governor_lib.py` | `A629651AF28E6D933A13CDC130BC4696933B12253006C8FE125DE921EA644B62` | 12759 | 1784530852308118000 |
| `scripts/transaction_registry.py` | `32A26DFC6C10FDB0DE87D5E97EF529B33580D7AB2EAF766D5F809855CEDD347C` | 8154 | 1784527682788864200 |
| `scripts/validate_state.py` | `829DDDA23E958BFCD4B91381E0F0377FBDB67597F057B160251DAABE9E94CD9D` | 1869 | 1784528061175366600 |
| `scripts/validation_runner.py` | `86A28722EC65DE172555A0C30DBCFF7F4F675F9766D543E8ACDEE61BD1899E46` | 9802 | 1784531011772854200 |
| `tests/test_project_governor_consistency.py` | `BAAE16C83DFD1BC52ABB63C1B16617DF8F50121499C1492E4031136B40FA07F0` | 66442 | 1784531360479058000 |

## Stop Boundary

Repair execution stops here. No fresh independent rereview, installation, activation, T-0037, host identity integration, live structured-state provisioning, controller/runtime enablement, or real-project entry was performed or authorized.
