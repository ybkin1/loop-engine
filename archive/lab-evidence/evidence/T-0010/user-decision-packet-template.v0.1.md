# User Decision Packet Template v0.1

Status: candidate repair evidence
Task: T-0010

## Purpose

Keep the non-technical solo user in the right role: business truth owner and gate decision maker, not project manager, architect, QA lead, or documentation author.

## Interaction Budget

Default budget per stage:

| Stage | Default User Interaction |
| --- | --- |
| Idea intake | 1 concise confirmation or correction |
| Domain model | 1 batch correction packet |
| Discovery baseline | 1 scope/tradeoff decision packet |
| PRD baseline | 1 product decision packet |
| Architecture baseline | 1 tradeoff decision packet |
| Detailed design baseline | 1 risk and baseline decision packet |
| Implementation planning | 1 proceed/hold decision packet |
| Release | 1 release/hold decision packet |

Question limits:

- Ask at most 3 direct questions in one packet.
- Prefer multiple-choice with tradeoffs when the decision space is known.
- Do not ask the user to enumerate all requirements, schemas, APIs, tests, security controls, or operational checks.
- AI should draft the model first, mark assumptions, and ask for corrections.
- If more than 3 questions are needed, group them into assumptions and ask for "correct what is wrong".

## Packet Structure

```markdown
# Decision Packet: <stage or gate>

## Summary

<5-10 bullets maximum>

## What AI Assumed

| ID | Assumption | Source | Confidence | Owner | Impact If Wrong |
| --- | --- | --- | --- | --- | --- |

## Decisions Needed

| DEC ID | Decision | Options | Recommendation | Tradeoff | Deadline/Gate Impact |
| --- | --- | --- | --- | --- | --- |

## Risks Or Conflicts

| Risk/Finding ID | Issue | Severity | Options | Recommended Handling |
| --- | --- | --- | --- | --- |

## Proposed Gate

Gate ID:
Gate type:
Allowed scope:
Forbidden scope:
What approval does not authorize:

## User Reply Format

Approve / reject / choose option / correct assumptions in natural language.
```

## Required Fields

Every decision row must include:

- decision ID
- owner
- source
- confidence
- affected artifacts
- recommended option
- alternative options
- consequence of no decision
- gate impact

## AI Responsibilities

Before asking the user:

- produce candidate artifacts
- run role review
- identify assumptions
- isolate true user decisions from AI-solvable gaps
- repair structural gaps without asking the user
- summarize only material tradeoffs and blockers

## User Responsibilities

The user decides:

- business truth corrections
- scope tradeoffs
- budget/time/value priorities
- risk acceptance
- gate approval or rejection

The user should not be asked to:

- design the architecture
- write API specs
- define every database field
- write test plans
- author security controls
- write runbooks
- maintain traceability manually

## Batch Correction Rule

When the user responds, AI must:

- update all affected artifacts
- record the correction source
- update confidence
- resolve or create conflict rows
- rerun affected traceability checks
- summarize what changed

## Candidate Boundary

This template is candidate evidence only. It does not change installed interaction behavior until a later explicit installation or rule-change gate.
