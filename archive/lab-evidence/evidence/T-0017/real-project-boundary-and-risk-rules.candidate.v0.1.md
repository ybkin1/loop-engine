# Real Project Boundary And Risk Rules Candidate v0.1

Status: candidate
Task: T-0017

## Purpose

Define the risk boundaries Codex must preserve when helping with real software
projects.

## Default Boundary

If scope is unclear, Codex must choose the narrower interpretation and record
the assumption. If the uncertainty touches high-risk actions or real project
write access, Codex must stop for a user gate.

## Separate Explicit Gates Required

The following always require separate explicit user approval:

- real-project entry
- implementation
- build or release preparation when it writes files or changes behavior
- deployment
- rollback
- database change
- permission or authorization change
- secret handling
- payment action
- production-data action
- migration
- AGENTS.md change
- skill, MCP, external agent runtime, automation, protocol service, or tool
  behavior enablement
- global or project runtime behavior change

## Security And Privacy Baseline

Design artifacts must identify:

- external inputs and validation rules
- authn/authz expectations
- RBAC/ABAC or permission matrix when relevant
- sensitive data and PII classification
- secrets handling policy
- logging and redaction rules
- abuse cases and rate-limit expectations
- audit logging needs

No design may recommend hardcoded secrets, unvalidated external input, direct
SQL string construction, front-end-only permission checks, or PII in logs.

## Data And Migration Baseline

When persisted data exists, design must define:

- entity catalog
- ownership and source of truth
- retention and deletion expectations
- privacy classification
- migration candidate notes
- indexes and constraints
- audit requirements

Any actual schema or migration change requires a later separate gate. Direct
destructive changes are forbidden unless a specific approved high-risk plan
allows them.

## Deployment And Rollback Baseline

Release planning must include:

- environment assumptions
- artifact immutability expectations
- preflight checks
- smoke tests
- monitoring window
- rollback or forward-fix plan
- no-go conditions
- approval requirements

Deployment and rollback remain separate gates even if the release plan is
approved.

## Subagent Boundary

Subagents may:

- read approved evidence
- summarize risks
- perform bounded review
- propose findings

Subagents may not:

- approve gates
- expand scope
- enter real project roots without gate
- write files unless a future gate grants a disjoint write set
- deploy, roll back, migrate, handle secrets, payment, permissions, or
  production data

## Handoff Boundary

Handoff is continuity, not authority. It must state:

- current task and phase
- allowed scope
- forbidden scope
- pending gates
- evidence location
- verified and unverified items
- next startup prompt

Handoff must not smuggle old product details or old approvals into a new task.
