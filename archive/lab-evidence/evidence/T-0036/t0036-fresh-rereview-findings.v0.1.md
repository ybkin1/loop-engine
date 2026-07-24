# T-0036 Fresh Independent Rereview Findings

Independent reviewer verdict: `REPAIR_REQUIRED`. This is evidence only and does not mean user acceptance, installation approval, production readiness, or runtime activation.

| Finding | Original severity | Independent verdict | Closure status | Installation qualification impact |
|---|---|---|---|---|
| T0036-F001 | P1 | `SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE` | Secure containment only; production authority lifecycle unavailable | BLOCKED; no production authority claim |
| T0036-F002 | P1 | `SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE` | Secure containment and fixture lineage checks; trusted later-turn authority unavailable | BLOCKED; no production lifecycle claim |
| T0036-F003 | P1 | `REPAIR_REQUIRED` | Not closed: runner executes argv but accepts spoofed unittest-like stdout from a zero-test command; normal 58-test path passes after projection sync | BLOCKED; controlled validation evidence is not independently trustworthy |
| T0036-F004 | P1 | `PASS` | Closed at candidate component/fixture level; ProjectContinuity-derived orientation and fail-closed missing/drift behavior pass | No installation qualification; live continuity absent |
| T0036-F005 | P1 | `PASS` | Closed at candidate component/fixture level; current and approved execution Gate projections are distinct and auditor catches mutation | No installation qualification; live state remains unprovisioned |
| T0036-F006 | P1 | `PASS` | Closed at candidate component/fixture level; lifecycle fields retain explicit unverified/not-performed/not-authorized values | No installation qualification; production lifecycle unavailable |
| T0036-F007 | P1 | `PASS_FIXTURE_ONLY` | Fixture registry, quiescence, fence, evidence, and acknowledgment gates work; only `STABLE_FIXTURE_ONLY` is emitted | BLOCKED; no production Stable checkpoint |
| T0036-F008 | P2 | `PASS_STRUCTURAL` | Structural split and producer/auditor module independence verified; no runtime controller created | BLOCKED by F003 and unavailable production authority |
| T0036-F009 | P1 | `PASS` | Closed at candidate component/fixture level; bounded manifest streaming and path/reparse/identity checks pass | No installation qualification; evidence is candidate-only |

## Evidence By Finding

- F001/F002: `authority_records.py:18-31`, `:48-85`; capability command returns `SECURELY_ISOLATED_AUTHORITY_LIFECYCLE_UNAVAILABLE`, with no trusted host adapter.
- F003: `validation_runner.py:158-187`; adversarial temporary command printed `Ran 1 test in 0.001s` and `OK` without tests and was bound as success. Positive controlled path executed 58/58 after state projection sync.
- F004: `continuity_producer.py:49-106`, `:139-186`; PC schema/hash checks and missing continuity fail closed; PC tests pass.
- F005: `continuity_producer.py:146-155`, `continuity_auditor.py:149-179`; separate `current_gate_id` and `approved_execution_gate_id`; mutation rejection test passes.
- F006: `continuity_producer.py:120-136`; explicit lifecycle arrays; lifecycle test passes.
- F007: `transaction_registry.py:91-143`; missing/non-quiescent/ack transitions are bounded and fixture-only; TR tests pass.
- F008: `continuity_producer.py` and `continuity_auditor.py` are separate modules; auditor does not import producer; structural test passes.
- F009: `evidence_manifest.py:11-177`; hard caps, streaming, canonical paths, reparse rejection, and create-only manifest; HASH/EM tests pass.

## Residual Limits

Live `.ai/project_continuity.yaml` and `.ai/transaction_registry.yaml` remain absent, so candidate live validation returns `PROJECT_CONTINUITY_MISSING`. E2E-CURRENT-001 passed only as `PASS_FIXTURE_ONLY` after the allowed projection synchronization. No production authority lifecycle, controller runtime, installation, activation, or real-project entry exists.
