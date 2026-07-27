# T-0036 Continuity And Legacy Reconciliation Gate Registration v0.1

Recorded at: `2026-07-24T15:05:09+08:00`

## Deterministic Startup

```text
validate_state.py
[project-governor] phase: S0-method-repair
[project-governor] current_task_id: T-0036
[ok] state is usable

audit_handoff.py
[error] Semantic Classification mismatch: 当前问题与状态

git diff --check
exit 0; no output
```

`git status --porcelain -uall` was non-clean before registration. Pre-existing modified paths included `.ai/DECISIONS.md`, `.ai/HANDOFF.md`, `.ai/gates.yaml`, `.ai/state.yaml`, `.ai/task_graph.yaml`, `README.md`, and the candidate consistency test; numerous T-0035..T-0038 evidence, Loop candidate, material, docs, and tests paths were already untracked. This Gate preserves them and claims authorship only for its registration delta.

Startup pending Gate count: `0`.

## Read-Only Sidecar Results

- HANDOFF/state audit: P1 semantic mismatch at HANDOFF line 62; P1 stale repair/full-suite/allowed-scope statements; P2 stale direction, freeze label, gate list, integration snapshot, and T-0037 prerequisite wording.
- Historical-roadmap audit: P1 old T-0035..T-0039 Project Governor mapping was approved/preserved and never explicitly superseded before ID reuse; T-0035 meets content Acceptance and is recommended for administrative completion with new reproducible evidence.
- Candidate/freeze audit: candidate test hard-codes global scripts/templates; candidate/global `close_session.py` and `audit_handoff.py` differ; 65/65 frozen subjects match; manifest lines 1, 3, and 5 contain 82 ASCII `0x3F` bytes.

Sidecar conclusions are evidence only. They did not modify files, approve the Gate, or execute reconciliation.

## Candidate And Global Script Fingerprints

| script | candidate size / SHA-256 | global size / SHA-256 | result |
| --- | --- | --- | --- |
| `governor_lib.py` | 19247 / `7D0344AF52F46DED67F4328A016D17D81A921F4903EA6F126A06D02DD11FACEA` | 19247 / same | match |
| `validate_state.py` | 1926 / `D8C9834DC77CC208785811647A61AB7A3D2B7FB6D2D866C7B5602C1FF23EC5D2` | 1926 / same | match |
| `close_session.py` | 4828 / `28D562B5BB1B80F28589E25DCE355472F058D39C2F94680E309BAB36AEED19D4` | 6972 / `824AB98388BCDC9DA1E8D9ACF44003CA085D01ACD82EB927DB911D0AEE58C4B4` | differ |
| `audit_handoff.py` | 3529 / `92DFA111C209CEE7283B1451E947C4E94EB5067A34A8AC9EC97674A78CB12545` | 7315 / `5F22B6B0B4ED2DA8B9591ABD31985FE26571FFB2D4683CEF4BEBE7B5A4FCAD20` | differ |

## Registration Boundary

Created only the pending Gate and its decision evidence, then updated `state.yaml` and `HANDOFF.md` solely to project the pending decision. No requested reconciliation, freeze-manifest prose repair, T-0035 status change, roadmap decision execution, candidate repair, or independent rereview was performed.

## Post-Registration Validation

```text
YAML_PARSE=PASS
PENDING_COUNT=1
PENDING_IDS=G-T-0036-PRE-REREVIEW-CONTINUITY-LEGACY-RECONCILIATION-V0-1

validate_state.py actual exit=2
[error] Pending gate(s) require user decision before continuing: G-T-0036-PRE-REREVIEW-CONTINUITY-LEGACY-RECONCILIATION-V0-1

audit_handoff.py actual exit=2
[error] Pending gate(s) not resolved: G-T-0036-PRE-REREVIEW-CONTINUITY-LEGACY-RECONCILIATION-V0-1

git diff --check
exit 0; no output

planned unified diff syntax
git apply --numstat exit 0

freeze manifest
declared=65 parsed=65 match=65 mismatch=0
```

The former Semantic Classification mismatch no longer appears; the only validator/auditor blocker is the newly registered pending Gate, as required.

Registration delta is limited to `.ai/gates.yaml`, `.ai/state.yaml`, `.ai/HANDOFF.md`, and four additive `continuity-legacy-reconciliation-*` evidence files. The future execution evidence paths remain absent, and no file in the execution allowlist was reconciled or repaired.
