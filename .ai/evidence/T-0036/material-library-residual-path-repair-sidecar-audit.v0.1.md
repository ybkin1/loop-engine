# T-0036 Residual Path Repair Sidecar Audit v0.1

Gate: `G-T-0036-REPAIR-F003-F005-PATH-CLOSURE-V0-1`

Purpose: bounded read-only audit evidence for Gate preparation. It does not approve the Gate or authorize repair.

## Confirmed Findings

- Fresh independent rereview verdict is `REPAIR_REQUIRED`; only residual F-003 and F-005 are blocking this path-closure step.
- F-003 source string occurs in the P1-P2 `human_decision.evidence_packet` entry of `.ai/evidence/T-0036/simulation/phase-profile.v0.1.yaml`.
- `.ai/evidence/T-0036/material-library-review-packet.md` does not exist; `materials/material-library-review-packet.md` exists and is already referenced by P7.
- F-005 source string occurs once in `selected_templates` in `.ai/evidence/T-0036/simulation/project-profile.v0.1.yaml`.
- `materials/templates/material-selection-record.yaml` does not exist; `materials/profiles/material-selection-record.yaml` exists.
- The two YAML preimages are 9796 / 2051 bytes with SHA-256 `94F2D296F869A84F7580CB7B8C3F67CA3344D6B1DE686323143AF0067DF583E9` / `E87BC22D39EE5AA65B6B5580CF0D74A91B274AB67A234294EC19C0AB1B9C3C02`.
- The existing post-repair freeze parses to 65 subjects with 65/65 path/size/SHA-256 matches and zero drift before registration.

## Minimal Repair Judgment

The sufficient future repair is exactly two YAML string substitutions. No schema, validator, test, catalog, register, profile template, task, task graph, candidate, global Project Governor, or runtime edit is supported by the residual findings.

The future execution must preserve byte ordering and formatting except for the changed string bytes, verify expected occurrence counts, and stop on any preimage drift.

## Independence And Limitations

No subagent was used for this registration audit. The audit is deterministic local evidence gathered by the main controller after startup validation; it is not a fresh rereview and makes no independent PASS claim.

No repair, network retrieval, candidate-baseline decision, version freeze, T-0037 review, Host Integration, installation, activation, or production action was performed.
