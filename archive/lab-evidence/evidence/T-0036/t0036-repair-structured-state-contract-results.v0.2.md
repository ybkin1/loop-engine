# T-0036 Structured State Contract Results v0.2

Completed: `2026-07-20T15:28:40.9738138+08:00`

## ProjectContinuity/v1

- `PC-001`: PASS - exact closed schema, four required decision IDs, source/semantic/file hashes, and independent reconstruction.
- `PC-002`: PASS - missing live continuity returns `PROJECT_CONTINUITY_MISSING`; close preserves existing HANDOFF bytes.
- `PC-003`: PASS - protected source drift blocks HANDOFF replacement.
- `PC-004`: PASS - semantic payload drift without hash update is rejected.
- `PC-005`: PASS - unknown fields and invalid protected decisions are rejected.

## TransactionRegistry/v1

- `TR-001`: PASS - missing registry never emits Stable; recovery status is `NOT_ESTABLISHED`.
- `TR-002`: PASS - quiescent fixture without acknowledgment is `PENDING_SUCCESSOR_ACK`.
- `TR-003`: PASS - matching fixture acknowledgment preserves checkpoint ID and yields only `STABLE_FIXTURE_ONLY`.
- `TR-004`: PASS - in-flight actor and other non-quiescent sets block stability.
- `TR-005`: PASS - fixture status and installation eligibility remain explicitly bounded; production Stable is not claimed.

## EvidenceManifest/v1

- `EM-001`: PASS - file count, total bytes, ordered entries, semantic/file hashes, and subject fingerprints bind.
- `EM-002`: PASS - missing manifest raises `EVIDENCE_MANIFEST_REQUIRED`.
- `EM-003`: PASS - manifest create-only conflict preserves old bytes.
- `EM-004`: PASS - subject tamper and metadata mismatch fail closed.
- `EM-005`: PASS - immutable persistence conflict tested.
- `HASH-001` through `HASH-005`: PASS - count/file bounds, traversal/ADS, reparse, and streaming identity drift tested.

Live `.ai/project_continuity.yaml` and `.ai/transaction_registry.yaml` remain absent. These results prove reader/fixture behavior only and do not provision a controller or production authority lifecycle.
