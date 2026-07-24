# T-0036 Preliminary Finding Leads v0.1

Captured before T-0036 HANDOFF projection on `2026-07-18`.

Status: `PRELIMINARY_LEADS_ONLY`.

These are not formal findings or a verdict. They do not bind the future reviewer. The reviewer must independently reproduce, rebut, or adjust each lead and continue searching for other issues.

## Frozen Registration-time HANDOFF

- Path: `.ai/HANDOFF.md`
- Size: `11057`
- SHA-256: `5620CAE52FB8B661F470FCA305400B3A98C0108B6F16682FB6726F2A10CB1DBC`
- `mtime_ns`: `1784366152420580700`
- Candidate audit exit code: `0`; output included `[ok] handoff audit passed`.
- Global audit exit code: `0`; output included `[ok] handoff audit passed`.

## Lead 1: Main Controller Orientation Is Not Preserved

Observed fields:

- `Main Controller Orientation` heading present: `false`.
- `north star`, `north-star`, `north_star`, or `真实软件交付是` phrase present: `false`.
- `用户拥有 Gate 决策权` phrase present: `false`.
- Both candidate and global audits still passed.

Hypothesis only: `close_session.py` does not generate the canonical main-controller orientation and audits do not require it.

## Lead 2: Structured Gate Projection Differs From Canonical State

Observed fields:

- `state.current_gate_id`: `null`.
- structured `ProjectGovernorNextAction/v1.current_gate_id`: `G-T-0035-IMPLEMENT-T0030-REPAIR-AND-APPROVED-CONTINUITY-INTERFACES-IN-ISOLATED-CANDIDATE`.
- candidate audit exit code: `0`.

Hypothesis only: the structured HANDOFF uses the most recent approved Gate when canonical state has no current Gate.

## Lead 3: Unverified Projection Collapses To `none`

Observed fields:

- HANDOFF `## Unverified`: `- none`.
- `TBD` present in HANDOFF: `false`.
- `unknown` present in HANDOFF: `false`.
- Independent review, user acceptance, installation, and activation had not occurred.
- `close_session.py` derives `Unverified` only from selected documents containing literal `TBD`.

Hypothesis only: unverified lifecycle facts are incorrectly modeled as a selected-document placeholder scan, allowing `none` despite unperformed review/acceptance/install/activation.

## Preservation Boundary

The original HANDOFF bytes are not rewritten as old evidence. This record preserves its fingerprint, relevant fields, and read-only audit reproduction. The later `.ai/HANDOFF.md` update is only the T-0036 governance projection and does not claim any candidate defect was fixed.
