# T-0036 HANDOFF Semantic Anchoring Decision Packet v0.1

Gate: `G-T-0036-REPAIR-HANDOFF-SEMANTIC-ANCHORING-V0-1`

Status: `pending`; registration only.

## Root Cause

`close_session.py` currently copies state/task text and a fixed startup template but does not load `.ai/PROJECT.md` or `AGENTS.md` semantic anchors. `audit_handoff.py` checks headings, task/status, evidence, and next-action markers but does not compare project anchors. Therefore mechanically valid HANDOFF output can misclassify local execution constraints as project stance.

## Scope

Future execution may modify only the two global scripts named in the Gate request and add the isolated semantic test module. The project candidate and governance source documents are protected.

## Quality/Progress Protection

The repair must preserve existing output sections, task/Gate state projection, transactional writes, pending-gate blocking, evidence checks, and audit exit behavior. No runtime or product behavior is changed.

## Rollback

Capture exact preimages and fingerprints. On any regression, restore only the two scripts and new test from preimages, rerun the existing validator/audit checks, and preserve this finding and its evidence.
