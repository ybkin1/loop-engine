# Structured State Results

Independent code and test review confirms the following bounded behavior:

- `ProjectContinuity/v1`: producer requires exact closed schema, PCC identity, protected decision IDs, source/semantic hashes, and source drift checks. Missing live continuity returns `PROJECT_CONTINUITY_MISSING` and preserves existing HANDOFF bytes.
- `TransactionRegistry/v1`: registry reader enforces exact schema, bounded lists, generation fence, and semantic hash. Missing/non-quiescent registry yields `NOT_ESTABLISHED`; matching fixture acknowledgment yields only `STABLE_FIXTURE_ONLY`.
- `EvidenceManifest/v1`: approved closed manifest, exact subjects, streaming hashes, count/size caps, traversal/ADS/collision/reparse/identity-drift rejection, and create-only persistence are implemented and covered by tests.
- Producer/auditor are separate modules; `continuity_auditor.py` does not import `continuity_producer.py` and independently reconstructs projection/checkpoint/lifecycle expectations.
- `governor_lib.py` is reduced to common state, serialization, path, YAML, and transaction primitives.

Live `.ai/project_continuity.yaml` and `.ai/transaction_registry.yaml` are absent. Candidate live validation therefore exits `2` with `PROJECT_CONTINUITY_MISSING`; this is containment and not a production continuity validation path.

The independent controlled-runner adversarial result remains a residual F003 gap despite the structured-state checks passing.
